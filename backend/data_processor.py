"""
data_processor.py — Transform and enrich database query results.

Reads from database query functions (get_standings, get_matches, etc.)
and returns clean DataFrames / lists ready for frontend consumption.
No API calls. No DB writes. Transform only.
"""

import logging
from typing import Optional

import pandas as pd

from . import database

logger = logging.getLogger(__name__)

_SG_TZ = "Asia/Singapore"
_AVAILABLE_STATUSES = {"a", "d"}   # FPL: available or doubtful


# ── Standings ─────────────────────────────────────────────────────────────────

def format_standings(competition_id: int, db_path: str = "data/football.db") -> pd.DataFrame:
    """
    Enrich standings DataFrame with derived columns.

    Added:
      form_list          — ["W","D","L","W","W"] parsed from comma-separated form string
      points_from_4th    — signed gap vs 4th place (negative = behind CL spots)
      points_from_relegation — signed gap vs 18th place (positive = above the drop)
    """
    df = database.get_standings(competition_id, db_path=db_path)
    if df.empty:
        return df

    df["form_list"] = df["form"].apply(
        lambda f: [r.strip() for r in f.split(",")] if isinstance(f, str) and f else []
    )

    fourth_arr = df.loc[df["position"] == 4, "points"].values
    fourth_pts = int(fourth_arr[0]) if len(fourth_arr) else None

    eighteenth_arr = df.loc[df["position"] == 18, "points"].values
    eighteenth_pts = int(eighteenth_arr[0]) if len(eighteenth_arr) else None

    df["points_from_4th"] = df["points"].apply(
        lambda p: (p - fourth_pts) if fourth_pts is not None else None
    )
    df["points_from_relegation"] = df["points"].apply(
        lambda p: (p - eighteenth_pts) if eighteenth_pts is not None else None
    )

    return df


# ── Fixtures / Results ────────────────────────────────────────────────────────

def format_matches(
    competition_id: int,
    status: Optional[str] = None,
    team_id: Optional[int] = None,
    limit: int = 50,
    db_path: str = "data/football.db",
) -> pd.DataFrame:
    """
    Return matches with Singapore-localised time and human-friendly display columns.

    Added:
      kick_off_sg  — tz-aware Timestamp (Asia/Singapore)
      date_label   — "Today", "Tomorrow", or e.g. "Sat 24 May"
      time_label   — "20:00"
      result_label — "2 - 1" for finished matches, "-" otherwise
    """
    df = database.get_matches(
        competition_id=competition_id,
        team_id=team_id,
        status=status,
        limit=limit,
        db_path=db_path,
    )
    if df.empty:
        return df

    kick_off_sg = pd.to_datetime(df["utc_date"], utc=True).dt.tz_convert(_SG_TZ)
    df["kick_off_sg"] = kick_off_sg

    now_sg = pd.Timestamp.now(tz=_SG_TZ)
    today_sg = now_sg.date()
    tomorrow_sg = (now_sg + pd.Timedelta(days=1)).date()

    def _date_label(ts: pd.Timestamp) -> str:
        d = ts.date()
        if d == today_sg:
            return "Today"
        if d == tomorrow_sg:
            return "Tomorrow"
        return f"{ts.strftime('%a')} {ts.day} {ts.strftime('%b')}"

    df["date_label"] = kick_off_sg.apply(_date_label)
    df["time_label"] = kick_off_sg.dt.strftime("%H:%M")

    def _result_label(row) -> str:
        if pd.notna(row["home_score"]) and pd.notna(row["away_score"]):
            return f"{int(row['home_score'])} - {int(row['away_score'])}"
        return "-"

    df["result_label"] = df.apply(_result_label, axis=1)

    return df


# ── Team Form ─────────────────────────────────────────────────────────────────

def get_team_form(
    team_id: int,
    n: int = 5,
    db_path: str = "data/football.db",
) -> list[dict]:
    """
    Return the last n finished matches for a team as a list of dicts.

    Keys: date (YYYY-MM-DD), home, away, score ("2 - 1"), result (W/D/L from team's perspective).
    """
    df = database.get_matches(
        team_id=team_id,
        status="FINISHED",
        limit=200,
        db_path=db_path,
    )
    if df.empty:
        return []

    df = df.tail(n).reset_index(drop=True)

    results = []
    for _, row in df.iterrows():
        is_home = row["home_team_id"] == team_id
        winner = row.get("winner")

        if winner == "DRAW":
            result = "D"
        elif (is_home and winner == "HOME_TEAM") or (not is_home and winner == "AWAY_TEAM"):
            result = "W"
        else:
            result = "L"

        home_score = int(row["home_score"]) if pd.notna(row["home_score"]) else 0
        away_score = int(row["away_score"]) if pd.notna(row["away_score"]) else 0

        results.append({
            "date":   row["utc_date"][:10],
            "home":   row["home_team_name"],
            "away":   row["away_team_name"],
            "score":  f"{home_score} - {away_score}",
            "result": result,
        })

    return results


# ── FPL ───────────────────────────────────────────────────────────────────────

def get_value_picks(
    position: Optional[str] = None,
    min_minutes: int = 450,
    db_path: str = "data/football.db",
) -> pd.DataFrame:
    """
    Players sorted by points_per_million (total_points / now_cost).
    Excludes injured, suspended, and unavailable players (FPL status not in {a, d}).
    """
    df = database.get_fpl_players(position=position, min_minutes=min_minutes, db_path=db_path)
    if df.empty:
        return df

    df = df[df["status"].isin(_AVAILABLE_STATUSES)].copy()
    df["points_per_million"] = (df["total_points"] / df["now_cost"]).round(1)
    return df.sort_values("points_per_million", ascending=False).reset_index(drop=True)


def get_form_table(
    n: int = 20,
    db_path: str = "data/football.db",
) -> pd.DataFrame:
    """Top n FPL players by form rating with at least 450 minutes played."""
    df = database.get_fpl_players(min_minutes=450, db_path=db_path)
    if df.empty:
        return df
    return df.sort_values("form", ascending=False).head(n).reset_index(drop=True)


def get_differentials(
    position: Optional[str] = None,
    max_ownership: float = 10.0,
    n: int = 15,
    db_path: str = "data/football.db",
) -> pd.DataFrame:
    """
    Low-ownership, high-form picks.

    Filters: ownership <= max_ownership%, min 450 min played, available only.
    Sorted by FPL form descending.
    """
    df = database.get_fpl_players(position=position, min_minutes=450, db_path=db_path)
    if df.empty:
        return df

    df = df[
        (df["selected_by_percent"] <= max_ownership) &
        (df["status"].isin(_AVAILABLE_STATUSES))
    ].copy()
    return df.sort_values("form", ascending=False).head(n).reset_index(drop=True)


def get_top_scorers_display(
    competition_id: int,
    db_path: str = "data/football.db",
) -> pd.DataFrame:
    """Top scorers with goals_per_game column added."""
    df = database.get_top_scorers(competition_id, db_path=db_path)
    if df.empty:
        return df

    df["goals_per_game"] = (
        df["goals"] / df["played_matches"].replace(0, pd.NA)
    ).round(2)
    return df
