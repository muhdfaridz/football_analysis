"""
fpl_api.py — FPL Official API connector.

Base URL: https://fantasy.premierleague.com/api/
No auth required — public endpoints.

Key endpoints:
  /bootstrap-static/   → all players, teams, gameweeks, element types
  /fixtures/           → full season fixtures with FDR
  /event/{gw}/live/    → live gameweek points

All functions check cache before hitting API.
FPL data refreshed daily at 08:00 SG time.
"""

# TODO: Implement in Claude Code / VS Code
# Key functions to build:
#   get_bootstrap() -> dict           (players, teams, gameweeks)
#   get_fixtures() -> pd.DataFrame    (with fixture difficulty ratings)
#   get_live_gw(gameweek) -> dict     (live points — match days only)
#   get_player_history(player_id) -> pd.DataFrame
