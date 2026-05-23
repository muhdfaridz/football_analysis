"""
football_data_api.py — football-data.org connector.

Endpoints covered (Phase 1):
  - /competitions/{id}/standings  → standings
  - /competitions/{id}/matches    → fixtures and results
  - /competitions/{id}/scorers    → top scorers
  - /teams/{id}                   → team profile
  - /teams/{id}/matches           → team fixtures/results

All functions:
  1. Check cache freshness via database.is_cache_fresh()
  2. Return cached data if fresh
  3. Fetch from API if stale, upsert to DB, mark cache refreshed
  4. Return clean DataFrame or dict — no raw API responses leave this module

Rate limit: 10 requests/minute — enforced via _RateLimiter (sliding window).
Auth: X-Auth-Token header.
"""

import logging
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
import yaml
from dotenv import load_dotenv

from . import database

logger = logging.getLogger(__name__)


# ── Config & auth ─────────────────────────────────────────────────────────────

def _load_config() -> dict:
    here = Path(__file__).parent
    project_root = here.parent
    load_dotenv(project_root / ".env")
    with open(project_root / "config" / "settings.yaml") as f:
        return yaml.safe_load(f)


_config = _load_config()
_API_KEY: str = os.getenv("FOOTBALL_DATA_ORG_KEY", "")
_BASE_URL: str = _config.get("football_data_base_url", "https://api.football-data.org/v4")
_REQUESTS_PER_MIN: int = int(_config.get("football_data_requests_per_min", 10))
_CACHE_TTL: float = float(_config.get("cache_ttl_hours", 6))
_DB_PATH: str = _config.get("db_path", "data/football.db")

if not _API_KEY:
    logger.warning("FOOTBALL_DATA_ORG_KEY not set — API calls will be rejected (401)")

database.init_db(_DB_PATH)


# ── Rate limiter ──────────────────────────────────────────────────────────────

class _RateLimiter:
    """Sliding-window rate limiter. Thread-safe."""

    def __init__(self, max_calls: int, period: float = 60.0) -> None:
        self._max_calls = max_calls
        self._period = period
        self._lock = threading.Lock()
        self._calls: deque = deque()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            while self._calls and self._calls[0] < now - self._period:
                self._calls.popleft()
            if len(self._calls) >= self._max_calls:
                sleep_for = self._calls[0] + self._period - now
                if sleep_for > 0:
                    logger.debug("Rate limit reached — sleeping %.1fs", sleep_for)
                    time.sleep(sleep_for)
            self._calls.append(time.monotonic())


_limiter = _RateLimiter(_REQUESTS_PER_MIN, period=60.0)


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _get(path: str, params: Optional[dict] = None) -> dict:
    """Rate-limited, authenticated GET. Raises requests.HTTPError on non-2xx."""
    _limiter.wait()
    url = f"{_BASE_URL}/{path.lstrip('/')}"
    resp = requests.get(
        url,
        headers={"X-Auth-Token": _API_KEY},
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _season_year(season_obj: dict) -> str:
    """Return 4-digit start year string from a football-data.org season object."""
    return season_obj.get("startDate", "")[:4]


# ── Public API ────────────────────────────────────────────────────────────────

def get_standings(competition_id: int) -> pd.DataFrame:
    """
    Return current standings for a competition.

    Columns: position, team_name, played, won, drawn, lost,
             goals_for, goals_against, goal_difference, points, form
    """
    cache_key = f"fdo:standings:{competition_id}"

    if not database.is_cache_fresh(cache_key, _CACHE_TTL, _DB_PATH):
        try:
            data = _get(f"/competitions/{competition_id}/standings")

            # Upsert competition metadata
            comp = data.get("competition", {})
            comp.setdefault("id", competition_id)
            database.upsert_competition(comp, _DB_PATH)

            season = _season_year(data.get("season", {}))
            matchday = data.get("season", {}).get("currentMatchday")

            # Use the TOTAL table only (skip HOME / AWAY sub-tables)
            table: list = []
            for group in data.get("standings", []):
                if group.get("type") == "TOTAL":
                    table = group.get("table", [])
                    break

            for row in table:
                database.upsert_team(row["team"], competition_id, _DB_PATH)

            database.upsert_standings(table, competition_id, season, matchday, _DB_PATH)
            database.mark_cache_refreshed(cache_key, "fdo", _CACHE_TTL, _DB_PATH)
            logger.info("Standings refreshed — competition %s (%d teams)", competition_id, len(table))

        except Exception as exc:
            logger.error("Failed to fetch standings for %s: %s", competition_id, exc)
            database.mark_cache_error(cache_key, "fdo", _DB_PATH)

    return database.get_standings(competition_id, db_path=_DB_PATH)


def get_fixtures(
    competition_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> pd.DataFrame:
    """
    Return scheduled/upcoming fixtures for a competition.

    date_from / date_to: ISO-8601 date strings, e.g. "2025-08-01"
    Columns: id, competition_id, season, matchday, utc_date, status,
             home_team_name, away_team_name, home_score, away_score
    """
    date_suffix = f":{date_from}:{date_to}" if (date_from or date_to) else ""
    cache_key = f"fdo:fixtures:{competition_id}{date_suffix}"

    if not database.is_cache_fresh(cache_key, _CACHE_TTL, _DB_PATH):
        try:
            params: dict = {}
            if date_from:
                params["dateFrom"] = date_from
            if date_to:
                params["dateTo"] = date_to

            data = _get(f"/competitions/{competition_id}/matches", params)
            matches = data.get("matches", [])
            database.upsert_matches(matches, _DB_PATH)
            database.mark_cache_refreshed(cache_key, "fdo", _CACHE_TTL, _DB_PATH)
            logger.info("Fixtures refreshed — competition %s (%d matches)", competition_id, len(matches))

        except Exception as exc:
            logger.error("Failed to fetch fixtures for %s: %s", competition_id, exc)
            database.mark_cache_error(cache_key, "fdo", _DB_PATH)

    return database.get_matches(
        competition_id=competition_id,
        status="SCHEDULED,TIMED",
        date_from=date_from,
        date_to=date_to,
        db_path=_DB_PATH,
    )


def get_results(competition_id: int, limit: int = 20) -> pd.DataFrame:
    """
    Return the most recent finished results for a competition.

    Returned DataFrame is sorted by utc_date descending (most recent first).
    Columns: id, competition_id, season, matchday, utc_date, status,
             home_team_name, away_team_name, home_score, away_score, winner
    """
    cache_key = f"fdo:results:{competition_id}"

    if not database.is_cache_fresh(cache_key, _CACHE_TTL, _DB_PATH):
        try:
            data = _get(
                f"/competitions/{competition_id}/matches",
                {"status": "FINISHED"},
            )
            matches = data.get("matches", [])
            database.upsert_matches(matches, _DB_PATH)
            database.mark_cache_refreshed(cache_key, "fdo", _CACHE_TTL, _DB_PATH)
            logger.info("Results refreshed — competition %s (%d matches)", competition_id, len(matches))

        except Exception as exc:
            logger.error("Failed to fetch results for %s: %s", competition_id, exc)
            database.mark_cache_error(cache_key, "fdo", _DB_PATH)

    # get_matches sorts ASC; fetch all FINISHED then take the tail for "most recent"
    df = database.get_matches(
        competition_id=competition_id,
        status="FINISHED",
        limit=9999,
        db_path=_DB_PATH,
    )
    return (
        df.sort_values("utc_date", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )


def get_top_scorers(competition_id: int) -> pd.DataFrame:
    """
    Return top scorers for a competition.

    Columns: player_name, team_name, goals, assists, penalties, played_matches
    """
    cache_key = f"fdo:scorers:{competition_id}"

    if not database.is_cache_fresh(cache_key, _CACHE_TTL, _DB_PATH):
        try:
            data = _get(f"/competitions/{competition_id}/scorers")
            season = _season_year(data.get("season", {}))
            scorers = data.get("scorers", [])
            database.upsert_top_scorers(scorers, competition_id, season, _DB_PATH)
            database.mark_cache_refreshed(cache_key, "fdo", _CACHE_TTL, _DB_PATH)
            logger.info("Top scorers refreshed — competition %s (%d players)", competition_id, len(scorers))

        except Exception as exc:
            logger.error("Failed to fetch top scorers for %s: %s", competition_id, exc)
            database.mark_cache_error(cache_key, "fdo", _DB_PATH)

    return database.get_top_scorers(competition_id, db_path=_DB_PATH)


def get_team(team_id: int) -> dict:
    """
    Return team profile as a dict.

    Keys: id, name, short_name, tla, crest_url
    Returns {} if team not found.
    """
    cache_key = f"fdo:team:{team_id}"

    if not database.is_cache_fresh(cache_key, _CACHE_TTL, _DB_PATH):
        try:
            data = _get(f"/teams/{team_id}")
            database.upsert_team(data, db_path=_DB_PATH)
            database.mark_cache_refreshed(cache_key, "fdo", _CACHE_TTL, _DB_PATH)
            logger.info("Team refreshed — %s (%s)", data.get("name"), team_id)

        except Exception as exc:
            logger.error("Failed to fetch team %s: %s", team_id, exc)
            database.mark_cache_error(cache_key, "fdo", _DB_PATH)

    with database.get_connection(_DB_PATH) as conn:
        row = conn.execute(
            "SELECT id, name, short_name, tla, crest_url FROM teams WHERE id = ?",
            (team_id,),
        ).fetchone()

    return dict(row) if row else {}


def get_team_matches(team_id: int, limit: int = 10) -> pd.DataFrame:
    """
    Return recent and upcoming matches for a team (mixed statuses).

    Sorted by utc_date ascending.
    Columns: id, competition_id, season, matchday, utc_date, status,
             home_team_name, away_team_name, home_score, away_score, winner
    """
    cache_key = f"fdo:team_matches:{team_id}"

    if not database.is_cache_fresh(cache_key, _CACHE_TTL, _DB_PATH):
        try:
            data = _get(f"/teams/{team_id}/matches")
            matches = data.get("matches", [])
            database.upsert_matches(matches, _DB_PATH)
            database.mark_cache_refreshed(cache_key, "fdo", _CACHE_TTL, _DB_PATH)
            logger.info("Team matches refreshed — team %s (%d matches)", team_id, len(matches))

        except Exception as exc:
            logger.error("Failed to fetch team matches for %s: %s", team_id, exc)
            database.mark_cache_error(cache_key, "fdo", _DB_PATH)

    return database.get_matches(team_id=team_id, limit=limit, db_path=_DB_PATH)
