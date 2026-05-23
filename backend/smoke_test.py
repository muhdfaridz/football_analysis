"""
smoke_test.py — quick sanity check for the backend connectors.

Run from the project root:
    python -m backend.smoke_test
    python -m backend.smoke_test fpl      # FPL section only
    python -m backend.smoke_test fdo      # football-data.org section only
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

from backend import football_data_api, fpl_api   # noqa: E402
from backend import database, data_processor      # noqa: E402
from backend import scheduler as sched_module     # noqa: E402


def smoke_fdo() -> None:
    print("\n=== football-data.org — Premier League standings ===\n")
    df = football_data_api.get_standings(2021)
    if df.empty:
        print("No data returned. Check API key, network, or cache status.")
        return
    print(df.to_string(index=False))
    print(f"\n{len(df)} teams returned.")


def smoke_fpl() -> None:
    print("\n=== FPL bootstrap ===\n")
    data = fpl_api.get_bootstrap()

    if data:
        print(f"bootstrap-static returned: {len(data.get('elements', []))} players, "
              f"{len(data.get('events', []))} gameweeks, "
              f"{len(data.get('teams', []))} teams")
    else:
        print("Cache was fresh — data already in DB.")

    gw = fpl_api.get_current_gameweek()
    if gw is None:
        print("Current gameweek: not yet determined (season may not have started)")
    else:
        print(f"\nCurrent gameweek: GW{gw}")

    print("\nTop 5 players by total points:\n")
    db_path = fpl_api._DB_PATH
    df = database.get_fpl_players(db_path=db_path)
    if df.empty:
        print("No FPL player data in DB — bootstrap may have failed.")
        return

    cols = ["web_name", "team_name", "position_label", "now_cost", "total_points",
            "form", "selected_by_percent"]
    top5 = df.head(5)[cols]
    print(top5.to_string(index=False))


def smoke_processor() -> None:
    db_path = fpl_api._DB_PATH

    print("\n=== data_processor — format_standings(2021) top 6 ===\n")
    df = data_processor.format_standings(2021, db_path=db_path)
    if df.empty:
        print("No standings data — run smoke_fdo() first.")
    else:
        cols = ["position", "team_name", "points", "form_list",
                "points_from_4th", "points_from_relegation"]
        print(df.head(6)[cols].to_string(index=False))

    print("\n=== data_processor — get_value_picks() top 5 ===\n")
    df = data_processor.get_value_picks(db_path=db_path)
    if df.empty:
        print("No FPL data — run smoke_fpl() first.")
    else:
        cols = ["web_name", "team_name", "position_label", "now_cost",
                "total_points", "points_per_million"]
        print(df.head(5)[cols].to_string(index=False))


def smoke_scheduler() -> None:
    print("\n=== scheduler — start, inspect, shutdown ===\n")
    s = sched_module.start_scheduler()

    jobs = s.get_jobs()
    print(f"{len(jobs)} jobs registered:\n")
    for job in jobs:
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M %Z") if job.next_run_time else "N/A"
        print(f"  [{job.id}]  {job.name}")
        print(f"    next run: {next_run}")

    sched_module.shutdown_scheduler(s)
    print("\nScheduler shut down cleanly.")


def main() -> None:
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    if target in ("fdo", "all"):
        smoke_fdo()
    if target in ("fpl", "all"):
        smoke_fpl()
    if target in ("processor", "all"):
        smoke_processor()
    if target in ("scheduler", "all"):
        smoke_scheduler()


if __name__ == "__main__":
    main()
