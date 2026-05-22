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
  4. Return clean DataFrame

Rate limit: 10 requests/minute — enforced via RateLimiter.
Auth: X-Auth-Token header.
"""

# TODO: Implement in Claude Code / VS Code
# Key functions to build:
#   get_standings(competition_id) -> pd.DataFrame
#   get_fixtures(competition_id, date_from, date_to) -> pd.DataFrame
#   get_results(competition_id, limit) -> pd.DataFrame
#   get_top_scorers(competition_id) -> pd.DataFrame
#   get_team(team_id) -> dict
#   get_team_matches(team_id, limit) -> pd.DataFrame
