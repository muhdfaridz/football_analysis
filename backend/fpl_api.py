"""
fpl_api.py — FPL official API connector.

Endpoints covered:
  - /bootstrap-static/       → all players + gameweeks + teams
  - /fixtures/               → all fixtures with difficulty ratings
  - /element-summary/{id}/   → per-player GW history

No auth required — FPL API is fully public.
Cache pattern: same as football_data_api.py — check DB freshness first,
fetch from API only when stale, upsert, mark cache refreshed.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
import yaml

from . import database

logger = logging.getLogger(__name__)


# ── Config ────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    here = Path(__file__).parent
    project_root = here.parent
    with open(project_root / "config" / "settings.yaml") as f:
        return yaml.safe_load(f)


_config = _load_config()
_BASE_URL = "https://fantasy.premierleague.com/api"
_CACHE_TTL: float = float(_config.get("cache_ttl_hours", 6))
_DB_PATH: str = _config.get("db_path", "data/football.db")

database.init_db(_DB_PATH)


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _get(path: str) -> dict | list:
    """Simple GET to FPL API. Raises requests.HTTPError on non-2xx."""
    url = f"{_BASE_URL}/{path.lstrip('/')}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


# ── Public API ────────────────────────────────────────────────────────────────

def get_bootstrap() -> dict:
    """
    Fetch /bootstrap-static/, upsert players and gameweeks to DB, return raw dict.

    Builds a team_id → team_name lookup from bootstrap teams and injects team_name
    into each player dict before upserting (upsert_fpl_players expects this field).

    Returns the raw response dict on a fresh fetch, {} if cache was already fresh.
    """
    cache_key = "fpl:bootstrap"

    if not database.is_cache_fresh(cache_key, _CACHE_TTL, _DB_PATH):
        try:
            data = _get("/bootstrap-static/")

            teams = data.get("teams", [])
            team_lookup: dict[int, str] = {t["id"]: t["name"] for t in teams}

            players = data.get("elements", [])
            for p in players:
                p["team_name"] = team_lookup.get(p.get("team"), "")

            gameweeks = data.get("events", [])

            database.upsert_fpl_players(players, _DB_PATH)
            database.upsert_fpl_gameweeks(gameweeks, _DB_PATH)
            database.mark_cache_refreshed(cache_key, "fpl", _CACHE_TTL, _DB_PATH)
            logger.info(
                "FPL bootstrap refreshed — %d players, %d gameweeks",
                len(players), len(gameweeks),
            )
            return data

        except Exception as exc:
            logger.error("Failed to fetch FPL bootstrap: %s", exc)
            database.mark_cache_error(cache_key, "fpl", _DB_PATH)
            return {}

    return {}


def get_fixtures() -> pd.DataFrame:
    """
    Fetch /fixtures/ and return a DataFrame of all season fixtures with FDR.

    One row per fixture. Columns:
      fixture_id, gameweek, kickoff_time,
      home_team_fpl_id, away_team_fpl_id,
      home_difficulty, away_difficulty, finished
    """
    cache_key = "fpl:fixtures"

    try:
        fixtures_raw = _get("/fixtures/")
        # Mark cache refreshed on every successful fetch (fixtures aren't persisted to DB)
        database.mark_cache_refreshed(cache_key, "fpl", _CACHE_TTL, _DB_PATH)
        logger.info("FPL fixtures fetched — %d fixtures", len(fixtures_raw))
    except Exception as exc:
        logger.error("Failed to fetch FPL fixtures: %s", exc)
        database.mark_cache_error(cache_key, "fpl", _DB_PATH)
        return pd.DataFrame(columns=[
            "fixture_id", "gameweek", "kickoff_time",
            "home_team_fpl_id", "away_team_fpl_id",
            "home_difficulty", "away_difficulty", "finished",
        ])

    rows = [
        {
            "fixture_id":       f["id"],
            "gameweek":         f.get("event"),
            "kickoff_time":     f.get("kickoff_time"),
            "home_team_fpl_id": f.get("team_h"),
            "away_team_fpl_id": f.get("team_a"),
            "home_difficulty":  f.get("team_h_difficulty"),
            "away_difficulty":  f.get("team_a_difficulty"),
            "finished":         bool(f.get("finished", False)),
        }
        for f in fixtures_raw
    ]
    return pd.DataFrame(rows)


def get_current_gameweek() -> Optional[int]:
    """
    Return the current FPL gameweek number.

    Checks DB first (fast path). Falls back to fetching bootstrap if DB is empty.
    Returns None if the season hasn't started.
    """
    gw = database.get_fpl_current_gameweek(_DB_PATH)
    if gw is not None:
        return gw

    logger.info("No current gameweek in DB — fetching bootstrap")
    get_bootstrap()
    return database.get_fpl_current_gameweek(_DB_PATH)


def get_player_history(player_id: int) -> pd.DataFrame:
    """
    Fetch /element-summary/{player_id}/ and return per-GW history as DataFrame.

    Key columns (FPL field names preserved):
      round, opponent_team, total_points, was_home, kickoff_time,
      minutes, goals_scored, assists, clean_sheets, goals_conceded,
      yellow_cards, red_cards, bonus, bps, influence, creativity,
      threat, ict_index, value, selected, transfers_in, transfers_out
    """
    try:
        data = _get(f"/element-summary/{player_id}/")
        history = data.get("history", [])
        if not history:
            return pd.DataFrame()
        return pd.DataFrame(history)

    except Exception as exc:
        logger.error("Failed to fetch player history for id=%s: %s", player_id, exc)
        return pd.DataFrame()
