"""
cache_manager.py — TTL-based cache invalidation helpers.

Wraps database.is_cache_fresh / mark_cache_refreshed with
domain-specific TTLs and cache key conventions.

Cache key convention: "{source}:{endpoint}:{param}"
Examples:
  fdo:standings:2021
  fdo:fixtures:2021
  fdo:scorers:2021
  fdo:team:66
  fpl:bootstrap
  fpl:fixtures
"""

# TODO: Implement in Claude Code / VS Code
# Key functions to build:
#
#   Cache key builders:
#     standings_key(competition_id) -> str
#     fixtures_key(competition_id) -> str
#     scorers_key(competition_id) -> str
#     team_key(team_id) -> str
#     fpl_bootstrap_key() -> str
#
#   TTL constants (hours):
#     TTL_STANDINGS = 6
#     TTL_FIXTURES  = 6
#     TTL_SCORERS   = 6
#     TTL_TEAM      = 24
#     TTL_FPL       = 6
#
#   Wrapper:
#     needs_refresh(cache_key, ttl_hours) -> bool
#       (thin wrapper over database.is_cache_fresh)
