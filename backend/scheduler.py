"""
scheduler.py — APScheduler jobs for data refresh.

Scheduler type: BackgroundScheduler (runs in background thread).
Timezone: Asia/Singapore (UTC+8).

Refresh schedule:
  06:00 SG — standings, fixtures, top scorers (football-data.org)
  08:00 SG — FPL bootstrap data
  Every 6h — today's fixtures check
  Every 60s on match days — live scores (API-Football Pro only)

Start the scheduler by calling start_scheduler().
Call shutdown_scheduler() on app exit.
"""

# TODO: Implement in Claude Code / VS Code
# Key functions to build:
#   start_scheduler() -> BackgroundScheduler
#   shutdown_scheduler(scheduler) -> None
#
# Job functions (called by scheduler):
#   job_refresh_standings()     — calls football_data_api for all active competitions
#   job_refresh_fixtures()      — calls football_data_api for upcoming fixtures
#   job_refresh_scorers()       — calls football_data_api top scorers
#   job_refresh_fpl()           — calls fpl_api bootstrap
#   job_refresh_live_scores()   — calls api_football (match days only)
