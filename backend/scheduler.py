"""
scheduler.py — APScheduler background jobs for data refresh.

Scheduler type: BackgroundScheduler (daemon thread, non-blocking).
Timezone: Asia/Singapore (UTC+8), loaded from settings.yaml.

Schedule:
  06:00 SG daily    — standings, top scorers
  08:00 SG daily    — FPL bootstrap
  every 6 hours     — fixtures (all competitions)
"""

import logging
from pathlib import Path

import pytz
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from . import football_data_api, fpl_api

logger = logging.getLogger(__name__)


# ── Config ────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    here = Path(__file__).parent
    project_root = here.parent
    with open(project_root / "config" / "settings.yaml") as f:
        return yaml.safe_load(f)


_config = _load_config()

_TIMEZONE = pytz.timezone(_config.get("timezone", "Asia/Singapore"))
_ACTIVE_COMPETITIONS: list[int] = [
    comp["id"] for comp in _config.get("active_competitions", [])
]

def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse "HH:MM" → (hour, minute)."""
    h, m = time_str.split(":")
    return int(h), int(m)


_STANDINGS_H, _STANDINGS_M = _parse_time(_config.get("refresh_standings_time", "06:00"))
_SCORERS_H,   _SCORERS_M   = _parse_time(_config.get("refresh_scorers_time",   "06:00"))
_FPL_H,       _FPL_M       = _parse_time(_config.get("refresh_fpl_time",       "08:00"))
_FIXTURES_INTERVAL_H: int  = int(_config.get("fixtures_refresh_interval_hours", 6))


# ── Job functions ─────────────────────────────────────────────────────────────

def job_refresh_standings() -> None:
    """Refresh standings for all active competitions."""
    logger.info("Scheduler: refreshing standings for %d competitions", len(_ACTIVE_COMPETITIONS))
    for comp_id in _ACTIVE_COMPETITIONS:
        try:
            football_data_api.get_standings(comp_id)
            logger.info("Standings refreshed — competition %s", comp_id)
        except Exception:
            logger.exception("Failed to refresh standings for competition %s", comp_id)


def job_refresh_fixtures() -> None:
    """Refresh all fixtures/results for active competitions."""
    logger.info("Scheduler: refreshing fixtures for %d competitions", len(_ACTIVE_COMPETITIONS))
    for comp_id in _ACTIVE_COMPETITIONS:
        try:
            football_data_api.get_fixtures(comp_id)
            logger.info("Fixtures refreshed — competition %s", comp_id)
        except Exception:
            logger.exception("Failed to refresh fixtures for competition %s", comp_id)


def job_refresh_scorers() -> None:
    """Refresh top scorers for all active competitions."""
    logger.info("Scheduler: refreshing top scorers for %d competitions", len(_ACTIVE_COMPETITIONS))
    for comp_id in _ACTIVE_COMPETITIONS:
        try:
            football_data_api.get_top_scorers(comp_id)
            logger.info("Top scorers refreshed — competition %s", comp_id)
        except Exception:
            logger.exception("Failed to refresh scorers for competition %s", comp_id)


def job_refresh_fpl() -> None:
    """Refresh FPL bootstrap data (players, gameweeks, teams)."""
    logger.info("Scheduler: refreshing FPL bootstrap data")
    try:
        fpl_api.get_bootstrap()
        logger.info("FPL bootstrap refreshed")
    except Exception:
        logger.exception("Failed to refresh FPL bootstrap")


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def start_scheduler() -> BackgroundScheduler:
    """
    Create, configure, and start the background scheduler.
    Returns the running BackgroundScheduler instance.
    Call shutdown_scheduler() when the app exits.
    """
    scheduler = BackgroundScheduler(timezone=_TIMEZONE)

    scheduler.add_job(
        job_refresh_standings,
        trigger=CronTrigger(hour=_STANDINGS_H, minute=_STANDINGS_M, timezone=_TIMEZONE),
        id="refresh_standings",
        name="Refresh standings (all competitions)",
        replace_existing=True,
    )
    scheduler.add_job(
        job_refresh_scorers,
        trigger=CronTrigger(hour=_SCORERS_H, minute=_SCORERS_M, timezone=_TIMEZONE),
        id="refresh_scorers",
        name="Refresh top scorers (all competitions)",
        replace_existing=True,
    )
    scheduler.add_job(
        job_refresh_fpl,
        trigger=CronTrigger(hour=_FPL_H, minute=_FPL_M, timezone=_TIMEZONE),
        id="refresh_fpl",
        name="Refresh FPL bootstrap data",
        replace_existing=True,
    )
    scheduler.add_job(
        job_refresh_fixtures,
        trigger=IntervalTrigger(hours=_FIXTURES_INTERVAL_H, timezone=_TIMEZONE),
        id="refresh_fixtures",
        name=f"Refresh fixtures every {_FIXTURES_INTERVAL_H}h",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started — %d jobs registered, timezone: %s",
        len(scheduler.get_jobs()),
        _TIMEZONE,
    )
    return scheduler


def shutdown_scheduler(scheduler: BackgroundScheduler) -> None:
    """Gracefully stop the scheduler without waiting for running jobs."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
