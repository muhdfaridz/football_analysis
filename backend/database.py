"""
database.py — SQLite schema, queries, and cache layer.

Responsibilities:
- Create and migrate all tables on first run
- Provide typed insert/upsert functions for each data domain
- Provide query functions that return clean DataFrames
- Track cache freshness via the api_cache table

All functions return pandas DataFrames or None. No business logic here.
Frontend never imports this directly — goes through data_processor.py.
"""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Path resolution ──────────────────────────────────────────────────────────

def get_db_path(db_path: str = "data/football.db") -> Path:
    """Resolve db path relative to project root (two levels up from backend/)."""
    here = Path(__file__).parent          # backend/
    project_root = here.parent            # football-analytics/
    full_path = project_root / db_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    return full_path


# ── Connection ───────────────────────────────────────────────────────────────

@contextmanager
def get_connection(db_path: str = "data/football.db"):
    """Context manager: yields a sqlite3 connection with WAL mode enabled."""
    path = get_db_path(db_path)
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # allows concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema ───────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- ── Competitions ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS competitions (
    id          INTEGER PRIMARY KEY,   -- football-data.org competition ID
    name        TEXT    NOT NULL,
    country     TEXT,
    code        TEXT,                  -- e.g. "PL", "CL"
    updated_at  TEXT    NOT NULL       -- ISO-8601 UTC
);

-- ── Teams ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teams (
    id              INTEGER PRIMARY KEY,   -- football-data.org team ID
    name            TEXT    NOT NULL,
    short_name      TEXT,
    tla             TEXT,                  -- three-letter abbreviation
    crest_url       TEXT,
    competition_id  INTEGER REFERENCES competitions(id),
    updated_at      TEXT    NOT NULL
);

-- ── Standings ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS standings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id  INTEGER NOT NULL REFERENCES competitions(id),
    season          TEXT    NOT NULL,      -- e.g. "2025/26"
    matchday        INTEGER,               -- current matchday snapshot
    position        INTEGER NOT NULL,
    team_id         INTEGER NOT NULL REFERENCES teams(id),
    team_name       TEXT    NOT NULL,
    played          INTEGER DEFAULT 0,
    won             INTEGER DEFAULT 0,
    drawn           INTEGER DEFAULT 0,
    lost            INTEGER DEFAULT 0,
    goals_for       INTEGER DEFAULT 0,
    goals_against   INTEGER DEFAULT 0,
    goal_difference INTEGER DEFAULT 0,
    points          INTEGER DEFAULT 0,
    form            TEXT,                  -- e.g. "W,W,D,L,W"
    updated_at      TEXT    NOT NULL,
    UNIQUE (competition_id, season, team_id)
);

-- ── Matches ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS matches (
    id              INTEGER PRIMARY KEY,   -- football-data.org match ID
    competition_id  INTEGER NOT NULL REFERENCES competitions(id),
    season          TEXT    NOT NULL,
    matchday        INTEGER,
    utc_date        TEXT    NOT NULL,      -- ISO-8601 UTC kick-off
    status          TEXT    NOT NULL,      -- SCHEDULED | LIVE | IN_PLAY | PAUSED | FINISHED | SUSPENDED | POSTPONED | CANCELLED
    home_team_id    INTEGER REFERENCES teams(id),
    home_team_name  TEXT,
    away_team_id    INTEGER REFERENCES teams(id),
    away_team_name  TEXT,
    home_score      INTEGER,               -- NULL if not yet played
    away_score      INTEGER,
    winner          TEXT,                  -- HOME_TEAM | AWAY_TEAM | DRAW | NULL
    updated_at      TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_matches_utc_date      ON matches(utc_date);
CREATE INDEX IF NOT EXISTS idx_matches_competition   ON matches(competition_id);
CREATE INDEX IF NOT EXISTS idx_matches_status        ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_home_team     ON matches(home_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_away_team     ON matches(away_team_id);

-- ── Top Scorers ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS top_scorers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id  INTEGER NOT NULL REFERENCES competitions(id),
    season          TEXT    NOT NULL,
    player_id       INTEGER,               -- football-data.org person ID
    player_name     TEXT    NOT NULL,
    team_id         INTEGER REFERENCES teams(id),
    team_name       TEXT,
    goals           INTEGER DEFAULT 0,
    assists         INTEGER DEFAULT 0,
    penalties       INTEGER DEFAULT 0,
    played_matches  INTEGER DEFAULT 0,
    updated_at      TEXT    NOT NULL,
    UNIQUE (competition_id, season, player_id)
);

-- ── Players ──────────────────────────────────────────────────────────────────
-- Populated from football-data.org /persons endpoint (Phase 1 top scorers only)
-- Expanded in Phase 2 with API-Football player stats
CREATE TABLE IF NOT EXISTS players (
    id              INTEGER PRIMARY KEY,   -- football-data.org person ID
    name            TEXT    NOT NULL,
    first_name      TEXT,
    last_name       TEXT,
    date_of_birth   TEXT,
    nationality     TEXT,
    position        TEXT,                  -- GOALKEEPER | DEFENDER | MIDFIELDER | FORWARD
    shirt_number    INTEGER,
    team_id         INTEGER REFERENCES teams(id),
    updated_at      TEXT    NOT NULL
);

-- ── FPL Players ──────────────────────────────────────────────────────────────
-- From FPL official API — keyed on FPL's own player ID
CREATE TABLE IF NOT EXISTS fpl_players (
    id                      INTEGER PRIMARY KEY,   -- FPL player ID
    web_name                TEXT    NOT NULL,       -- display name
    first_name              TEXT,
    second_name             TEXT,
    team_fpl_id             INTEGER,               -- FPL's internal team ID
    team_name               TEXT,
    position_type           INTEGER,               -- 1=GK 2=DEF 3=MID 4=FWD
    position_label          TEXT,                  -- GK | DEF | MID | FWD
    now_cost                REAL,                  -- price in £M (raw/10)
    total_points            INTEGER DEFAULT 0,
    event_points            INTEGER DEFAULT 0,     -- last GW points
    form                    REAL,                  -- FPL form rating
    selected_by_percent     REAL,                  -- ownership %
    minutes                 INTEGER DEFAULT 0,
    goals_scored            INTEGER DEFAULT 0,
    assists                 INTEGER DEFAULT 0,
    clean_sheets            INTEGER DEFAULT 0,
    goals_conceded          INTEGER DEFAULT 0,
    yellow_cards            INTEGER DEFAULT 0,
    red_cards               INTEGER DEFAULT 0,
    bonus                   INTEGER DEFAULT 0,
    bps                     INTEGER DEFAULT 0,     -- bonus point system score
    ict_index               REAL,
    influence               REAL,
    creativity              REAL,
    threat                  REAL,
    cost_change_start        REAL,                 -- price change since GW1
    cost_change_event        REAL,                 -- price change this GW
    transfers_in_event       INTEGER DEFAULT 0,
    transfers_out_event      INTEGER DEFAULT 0,
    status                  TEXT,                  -- a=available, i=injured, d=doubt, s=suspended, u=unavailable
    chance_of_playing_next  INTEGER,               -- %
    news                    TEXT,                  -- injury/availability note
    updated_at              TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fpl_players_team      ON fpl_players(team_fpl_id);
CREATE INDEX IF NOT EXISTS idx_fpl_players_position  ON fpl_players(position_type);

-- ── FPL Gameweeks ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fpl_gameweeks (
    id                  INTEGER PRIMARY KEY,   -- GW number
    name                TEXT,
    deadline_time       TEXT,                  -- ISO-8601 UTC
    is_current          INTEGER DEFAULT 0,     -- boolean
    is_next             INTEGER DEFAULT 0,
    is_finished         INTEGER DEFAULT 0,
    average_entry_score INTEGER DEFAULT 0,
    highest_score       INTEGER DEFAULT 0,
    updated_at          TEXT    NOT NULL
);

-- ── API Cache Tracker ────────────────────────────────────────────────────────
-- Tracks when each cache key was last refreshed from live API.
-- cache_key pattern: "{source}:{endpoint}:{param}"
-- e.g. "fdo:standings:2021", "fdo:fixtures:2021", "fpl:bootstrap"
CREATE TABLE IF NOT EXISTS api_cache (
    cache_key       TEXT    PRIMARY KEY,
    source          TEXT    NOT NULL,   -- fdo | api_football | fpl
    fetched_at      TEXT    NOT NULL,   -- ISO-8601 UTC of last successful fetch
    ttl_hours       REAL    DEFAULT 6,
    status          TEXT    DEFAULT 'ok'  -- ok | error
);
"""


def init_db(db_path: str = "data/football.db") -> None:
    """Create all tables if they don't exist. Safe to call on every startup."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
    logger.info(f"Database initialised at {get_db_path(db_path)}")


# ── Cache helpers ────────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_cache_fresh(cache_key: str, ttl_hours: float = 6.0,
                   db_path: str = "data/football.db") -> bool:
    """Return True if cache_key was fetched within ttl_hours."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT fetched_at FROM api_cache WHERE cache_key = ? AND status = 'ok'",
            (cache_key,)
        ).fetchone()
    if not row:
        return False
    fetched_at = datetime.fromisoformat(row["fetched_at"])
    age_hours = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
    return age_hours < ttl_hours


def mark_cache_refreshed(cache_key: str, source: str, ttl_hours: float = 6.0,
                         db_path: str = "data/football.db") -> None:
    """Upsert a cache_key as freshly fetched."""
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO api_cache (cache_key, source, fetched_at, ttl_hours, status)
            VALUES (?, ?, ?, ?, 'ok')
            ON CONFLICT(cache_key) DO UPDATE SET
                fetched_at = excluded.fetched_at,
                ttl_hours  = excluded.ttl_hours,
                status     = 'ok'
        """, (cache_key, source, _now_utc(), ttl_hours))


def mark_cache_error(cache_key: str, source: str,
                     db_path: str = "data/football.db") -> None:
    """Record a failed fetch attempt without nuking the stale cached data."""
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO api_cache (cache_key, source, fetched_at, ttl_hours, status)
            VALUES (?, ?, ?, 6, 'error')
            ON CONFLICT(cache_key) DO UPDATE SET status = 'error'
        """, (cache_key, source, _now_utc()))


# ── Upsert: Competitions ─────────────────────────────────────────────────────

def upsert_competition(competition: dict, db_path: str = "data/football.db") -> None:
    """
    Insert or update a competition row.
    Expected keys: id, name, country (optional), code (optional)
    """
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO competitions (id, name, country, code, updated_at)
            VALUES (:id, :name, :country, :code, :updated_at)
            ON CONFLICT(id) DO UPDATE SET
                name       = excluded.name,
                country    = excluded.country,
                code       = excluded.code,
                updated_at = excluded.updated_at
        """, {
            "id":         competition["id"],
            "name":       competition["name"],
            "country":    competition.get("area", {}).get("name") if isinstance(competition.get("area"), dict) else competition.get("country"),
            "code":       competition.get("code"),
            "updated_at": _now_utc(),
        })


# ── Upsert: Teams ────────────────────────────────────────────────────────────

def upsert_team(team: dict, competition_id: Optional[int] = None,
                db_path: str = "data/football.db") -> None:
    """
    Insert or update a team row.
    Expected keys: id, name, shortName (optional), tla (optional), crest (optional)
    """
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO teams (id, name, short_name, tla, crest_url, competition_id, updated_at)
            VALUES (:id, :name, :short_name, :tla, :crest_url, :competition_id, :updated_at)
            ON CONFLICT(id) DO UPDATE SET
                name           = excluded.name,
                short_name     = excluded.short_name,
                tla            = excluded.tla,
                crest_url      = excluded.crest_url,
                competition_id = excluded.competition_id,
                updated_at     = excluded.updated_at
        """, {
            "id":             team["id"],
            "name":           team["name"],
            "short_name":     team.get("shortName"),
            "tla":            team.get("tla"),
            "crest_url":      team.get("crest"),
            "competition_id": competition_id,
            "updated_at":     _now_utc(),
        })


# ── Upsert: Standings ────────────────────────────────────────────────────────

def upsert_standings(rows: list[dict], competition_id: int, season: str,
                     matchday: Optional[int] = None,
                     db_path: str = "data/football.db") -> None:
    """
    Bulk upsert standings for a competition/season snapshot.
    Each row dict expected keys (from football-data.org standings table entry):
      position, team{id, name}, playedGames, won, draw, lost,
      goalsFor, goalsAgainst, goalDifference, points, form
    """
    now = _now_utc()
    with get_connection(db_path) as conn:
        for row in rows:
            conn.execute("""
                INSERT INTO standings (
                    competition_id, season, matchday, position,
                    team_id, team_name, played, won, drawn, lost,
                    goals_for, goals_against, goal_difference, points,
                    form, updated_at
                )
                VALUES (
                    :competition_id, :season, :matchday, :position,
                    :team_id, :team_name, :played, :won, :drawn, :lost,
                    :goals_for, :goals_against, :goal_difference, :points,
                    :form, :updated_at
                )
                ON CONFLICT(competition_id, season, team_id) DO UPDATE SET
                    matchday        = excluded.matchday,
                    position        = excluded.position,
                    played          = excluded.played,
                    won             = excluded.won,
                    drawn           = excluded.drawn,
                    lost            = excluded.lost,
                    goals_for       = excluded.goals_for,
                    goals_against   = excluded.goals_against,
                    goal_difference = excluded.goal_difference,
                    points          = excluded.points,
                    form            = excluded.form,
                    updated_at      = excluded.updated_at
            """, {
                "competition_id":  competition_id,
                "season":          season,
                "matchday":        matchday,
                "position":        row["position"],
                "team_id":         row["team"]["id"],
                "team_name":       row["team"]["name"],
                "played":          row.get("playedGames", 0),
                "won":             row.get("won", 0),
                "drawn":           row.get("draw", 0),
                "lost":            row.get("lost", 0),
                "goals_for":       row.get("goalsFor", 0),
                "goals_against":   row.get("goalsAgainst", 0),
                "goal_difference": row.get("goalDifference", 0),
                "points":          row.get("points", 0),
                "form":            row.get("form"),
                "updated_at":      now,
            })


# ── Upsert: Matches ──────────────────────────────────────────────────────────

def upsert_matches(matches: list[dict], db_path: str = "data/football.db") -> None:
    """
    Bulk upsert matches from football-data.org /matches response.
    Handles both scheduled and finished matches.
    """
    now = _now_utc()
    with get_connection(db_path) as conn:
        for m in matches:
            score = m.get("score", {})
            full_time = score.get("fullTime", {})
            winner = score.get("winner")  # HOME_TEAM | AWAY_TEAM | DRAW | None

            conn.execute("""
                INSERT INTO matches (
                    id, competition_id, season, matchday, utc_date, status,
                    home_team_id, home_team_name, away_team_id, away_team_name,
                    home_score, away_score, winner, updated_at
                )
                VALUES (
                    :id, :competition_id, :season, :matchday, :utc_date, :status,
                    :home_team_id, :home_team_name, :away_team_id, :away_team_name,
                    :home_score, :away_score, :winner, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status        = excluded.status,
                    matchday      = excluded.matchday,
                    home_score    = excluded.home_score,
                    away_score    = excluded.away_score,
                    winner        = excluded.winner,
                    updated_at    = excluded.updated_at
            """, {
                "id":             m["id"],
                "competition_id": m["competition"]["id"],
                "season":         m.get("season", {}).get("startDate", "")[:4],
                "matchday":       m.get("matchday"),
                "utc_date":       m["utcDate"],
                "status":         m["status"],
                "home_team_id":   m["homeTeam"]["id"] if m.get("homeTeam") else None,
                "home_team_name": m["homeTeam"].get("name") if m.get("homeTeam") else None,
                "away_team_id":   m["awayTeam"]["id"] if m.get("awayTeam") else None,
                "away_team_name": m["awayTeam"].get("name") if m.get("awayTeam") else None,
                "home_score":     full_time.get("home"),
                "away_score":     full_time.get("away"),
                "winner":         winner,
                "updated_at":     now,
            })


# ── Upsert: Top Scorers ──────────────────────────────────────────────────────

def upsert_top_scorers(scorers: list[dict], competition_id: int, season: str,
                       db_path: str = "data/football.db") -> None:
    """
    Upsert top scorers list from football-data.org /scorers response.
    Each scorer dict expected keys: player{id, name}, team{id, name},
    goals, assists, penalties, playedMatches
    """
    now = _now_utc()
    with get_connection(db_path) as conn:
        for s in scorers:
            player = s.get("player", {})
            team = s.get("team", {})
            conn.execute("""
                INSERT INTO top_scorers (
                    competition_id, season, player_id, player_name,
                    team_id, team_name, goals, assists, penalties,
                    played_matches, updated_at
                )
                VALUES (
                    :competition_id, :season, :player_id, :player_name,
                    :team_id, :team_name, :goals, :assists, :penalties,
                    :played_matches, :updated_at
                )
                ON CONFLICT(competition_id, season, player_id) DO UPDATE SET
                    player_name    = excluded.player_name,
                    team_id        = excluded.team_id,
                    team_name      = excluded.team_name,
                    goals          = excluded.goals,
                    assists        = excluded.assists,
                    penalties      = excluded.penalties,
                    played_matches = excluded.played_matches,
                    updated_at     = excluded.updated_at
            """, {
                "competition_id": competition_id,
                "season":         season,
                "player_id":      player.get("id"),
                "player_name":    player.get("name", "Unknown"),
                "team_id":        team.get("id"),
                "team_name":      team.get("name"),
                "goals":          s.get("goals", 0),
                "assists":        s.get("assists", 0),
                "penalties":      s.get("penalties", 0),
                "played_matches": s.get("playedMatches", 0),
                "updated_at":     now,
            })


# ── Upsert: FPL Players ──────────────────────────────────────────────────────

_FPL_POSITION_LABELS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

def upsert_fpl_players(players: list[dict], db_path: str = "data/football.db") -> None:
    """
    Bulk upsert FPL player data from bootstrap-static elements list.
    Raw FPL cost is in units of 100k (e.g. 65 → £6.5m). Stored as £M float.
    """
    now = _now_utc()
    with get_connection(db_path) as conn:
        for p in players:
            pos = p.get("element_type", 0)
            conn.execute("""
                INSERT INTO fpl_players (
                    id, web_name, first_name, second_name,
                    team_fpl_id, team_name, position_type, position_label,
                    now_cost, total_points, event_points, form,
                    selected_by_percent, minutes, goals_scored, assists,
                    clean_sheets, goals_conceded, yellow_cards, red_cards,
                    bonus, bps, ict_index, influence, creativity, threat,
                    cost_change_start, cost_change_event,
                    transfers_in_event, transfers_out_event,
                    status, chance_of_playing_next, news, updated_at
                )
                VALUES (
                    :id, :web_name, :first_name, :second_name,
                    :team_fpl_id, :team_name, :position_type, :position_label,
                    :now_cost, :total_points, :event_points, :form,
                    :selected_by_percent, :minutes, :goals_scored, :assists,
                    :clean_sheets, :goals_conceded, :yellow_cards, :red_cards,
                    :bonus, :bps, :ict_index, :influence, :creativity, :threat,
                    :cost_change_start, :cost_change_event,
                    :transfers_in_event, :transfers_out_event,
                    :status, :chance_of_playing_next, :news, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    web_name               = excluded.web_name,
                    team_fpl_id            = excluded.team_fpl_id,
                    team_name              = excluded.team_name,
                    position_type          = excluded.position_type,
                    position_label         = excluded.position_label,
                    now_cost               = excluded.now_cost,
                    total_points           = excluded.total_points,
                    event_points           = excluded.event_points,
                    form                   = excluded.form,
                    selected_by_percent    = excluded.selected_by_percent,
                    minutes                = excluded.minutes,
                    goals_scored           = excluded.goals_scored,
                    assists                = excluded.assists,
                    clean_sheets           = excluded.clean_sheets,
                    goals_conceded         = excluded.goals_conceded,
                    yellow_cards           = excluded.yellow_cards,
                    red_cards              = excluded.red_cards,
                    bonus                  = excluded.bonus,
                    bps                    = excluded.bps,
                    ict_index              = excluded.ict_index,
                    influence              = excluded.influence,
                    creativity             = excluded.creativity,
                    threat                 = excluded.threat,
                    cost_change_start      = excluded.cost_change_start,
                    cost_change_event      = excluded.cost_change_event,
                    transfers_in_event     = excluded.transfers_in_event,
                    transfers_out_event    = excluded.transfers_out_event,
                    status                 = excluded.status,
                    chance_of_playing_next = excluded.chance_of_playing_next,
                    news                   = excluded.news,
                    updated_at             = excluded.updated_at
            """, {
                "id":                     p["id"],
                "web_name":               p.get("web_name", ""),
                "first_name":             p.get("first_name"),
                "second_name":            p.get("second_name"),
                "team_fpl_id":            p.get("team"),
                "team_name":              p.get("team_name"),   # injected by fpl_api.py
                "position_type":          pos,
                "position_label":         _FPL_POSITION_LABELS.get(pos, ""),
                "now_cost":               p.get("now_cost", 0) / 10,
                "total_points":           p.get("total_points", 0),
                "event_points":           p.get("event_points", 0),
                "form":                   float(p.get("form", 0) or 0),
                "selected_by_percent":    float(p.get("selected_by_percent", 0) or 0),
                "minutes":                p.get("minutes", 0),
                "goals_scored":           p.get("goals_scored", 0),
                "assists":                p.get("assists", 0),
                "clean_sheets":           p.get("clean_sheets", 0),
                "goals_conceded":         p.get("goals_conceded", 0),
                "yellow_cards":           p.get("yellow_cards", 0),
                "red_cards":              p.get("red_cards", 0),
                "bonus":                  p.get("bonus", 0),
                "bps":                    p.get("bps", 0),
                "ict_index":              float(p.get("ict_index", 0) or 0),
                "influence":              float(p.get("influence", 0) or 0),
                "creativity":             float(p.get("creativity", 0) or 0),
                "threat":                 float(p.get("threat", 0) or 0),
                "cost_change_start":      p.get("cost_change_start", 0) / 10,
                "cost_change_event":      p.get("cost_change_event", 0) / 10,
                "transfers_in_event":     p.get("transfers_in_event", 0),
                "transfers_out_event":    p.get("transfers_out_event", 0),
                "status":                 p.get("status"),
                "chance_of_playing_next": p.get("chance_of_playing_next_round"),
                "news":                   p.get("news"),
                "updated_at":             now,
            })


def upsert_fpl_gameweeks(gameweeks: list[dict], db_path: str = "data/football.db") -> None:
    """Upsert FPL gameweek data from bootstrap-static events list."""
    now = _now_utc()
    with get_connection(db_path) as conn:
        for gw in gameweeks:
            conn.execute("""
                INSERT INTO fpl_gameweeks (
                    id, name, deadline_time, is_current, is_next,
                    is_finished, average_entry_score, highest_score, updated_at
                )
                VALUES (
                    :id, :name, :deadline_time, :is_current, :is_next,
                    :is_finished, :average_entry_score, :highest_score, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    is_current          = excluded.is_current,
                    is_next             = excluded.is_next,
                    is_finished         = excluded.is_finished,
                    average_entry_score = excluded.average_entry_score,
                    highest_score       = excluded.highest_score,
                    updated_at          = excluded.updated_at
            """, {
                "id":                  gw["id"],
                "name":                gw.get("name"),
                "deadline_time":       gw.get("deadline_time"),
                "is_current":          int(gw.get("is_current", False)),
                "is_next":             int(gw.get("is_next", False)),
                "is_finished":         int(gw.get("finished", False)),
                "average_entry_score": gw.get("average_entry_score", 0),
                "highest_score":       gw.get("highest_score", 0),
                "updated_at":          now,
            })


# ── Query functions → DataFrames ─────────────────────────────────────────────

def get_standings(competition_id: int, season: Optional[str] = None,
                  db_path: str = "data/football.db") -> pd.DataFrame:
    """Return current standings table for a competition as DataFrame."""
    with get_connection(db_path) as conn:
        query = """
            SELECT position, team_name, played, won, drawn, lost,
                   goals_for, goals_against, goal_difference, points, form
            FROM standings
            WHERE competition_id = ?
        """
        params: list = [competition_id]
        if season:
            query += " AND season = ?"
            params.append(season)
        query += " ORDER BY position ASC"
        return pd.read_sql_query(query, conn, params=params)


def get_matches(competition_id: Optional[int] = None,
                team_id: Optional[int] = None,
                status: Optional[str] = None,
                date_from: Optional[str] = None,
                date_to: Optional[str] = None,
                limit: int = 50,
                db_path: str = "data/football.db") -> pd.DataFrame:
    """Flexible match query. Returns matches sorted by utc_date ASC."""
    conditions = []
    params: list = []

    if competition_id:
        conditions.append("competition_id = ?")
        params.append(competition_id)
    if team_id:
        conditions.append("(home_team_id = ? OR away_team_id = ?)")
        params.extend([team_id, team_id])
    if status:
        # Accepts comma-separated: "FINISHED,LIVE"
        placeholders = ",".join("?" * len(status.split(",")))
        conditions.append(f"status IN ({placeholders})")
        params.extend(status.split(","))
    if date_from:
        conditions.append("utc_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("utc_date <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"""
        SELECT id, competition_id, season, matchday, utc_date, status,
               home_team_id, home_team_name, away_team_id, away_team_name,
               home_score, away_score, winner
        FROM matches
        {where}
        ORDER BY utc_date ASC
        LIMIT ?
    """
    params.append(limit)

    with get_connection(db_path) as conn:
        return pd.read_sql_query(query, conn, params=params)


def get_top_scorers(competition_id: int, season: Optional[str] = None,
                    limit: int = 20,
                    db_path: str = "data/football.db") -> pd.DataFrame:
    """Return top scorers for a competition."""
    with get_connection(db_path) as conn:
        query = """
            SELECT player_name, team_name, goals, assists, penalties, played_matches
            FROM top_scorers
            WHERE competition_id = ?
        """
        params: list = [competition_id]
        if season:
            query += " AND season = ?"
            params.append(season)
        query += " ORDER BY goals DESC LIMIT ?"
        params.append(limit)
        return pd.read_sql_query(query, conn, params=params)


def get_fpl_players(position: Optional[str] = None,
                    min_minutes: int = 0,
                    db_path: str = "data/football.db") -> pd.DataFrame:
    """Return FPL player table with optional position filter."""
    conditions = ["minutes >= ?"]
    params: list = [min_minutes]

    if position:
        conditions.append("position_label = ?")
        params.append(position.upper())

    where = "WHERE " + " AND ".join(conditions)
    query = f"""
        SELECT id, web_name, team_name, position_label, now_cost,
               total_points, form, selected_by_percent, minutes,
               goals_scored, assists, clean_sheets, bonus,
               ict_index, status, chance_of_playing_next, news
        FROM fpl_players
        {where}
        ORDER BY total_points DESC
    """
    with get_connection(db_path) as conn:
        return pd.read_sql_query(query, conn, params=params)


def get_fpl_current_gameweek(db_path: str = "data/football.db") -> Optional[int]:
    """Return the current FPL gameweek number, or None if not yet populated."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM fpl_gameweeks WHERE is_current = 1 LIMIT 1"
        ).fetchone()
    return row["id"] if row else None


def get_cache_status(db_path: str = "data/football.db") -> pd.DataFrame:
    """Return all cache entries — useful for a debug/admin view."""
    with get_connection(db_path) as conn:
        return pd.read_sql_query(
            "SELECT cache_key, source, fetched_at, ttl_hours, status FROM api_cache ORDER BY fetched_at DESC",
            conn
        )
