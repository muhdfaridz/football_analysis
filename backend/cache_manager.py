"""
cache_manager.py — Domain-specific TTL and cache key helpers.

Thin layer over database.is_cache_fresh / mark_cache_refreshed.

Cache key convention: "{source}:{endpoint}:{param}"
  fdo:standings:2021
  fdo:fixtures:2021
  fdo:scorers:2021
  fdo:team:66
  fpl:bootstrap
"""

from . import database

# ── TTL constants (hours) ─────────────────────────────────────────────────────

TTL_STANDINGS: float = 6.0
TTL_FIXTURES:  float = 6.0
TTL_SCORERS:   float = 6.0
TTL_TEAM:      float = 24.0
TTL_FPL:       float = 6.0


# ── Cache key builders ────────────────────────────────────────────────────────

def standings_key(competition_id: int) -> str:
    return f"fdo:standings:{competition_id}"


def fixtures_key(competition_id: int) -> str:
    return f"fdo:fixtures:{competition_id}"


def scorers_key(competition_id: int) -> str:
    return f"fdo:scorers:{competition_id}"


def team_key(team_id: int) -> str:
    return f"fdo:team:{team_id}"


def fpl_bootstrap_key() -> str:
    return "fpl:bootstrap"


# ── Refresh check ─────────────────────────────────────────────────────────────

def needs_refresh(
    cache_key: str,
    ttl_hours: float,
    db_path: str = "data/football.db",
) -> bool:
    """Return True if cache_key is stale or has never been fetched."""
    return not database.is_cache_fresh(cache_key, ttl_hours, db_path)
