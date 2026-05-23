"""
teams.py — Team profile: season stats, form guide, recent results, upcoming fixtures.
Frontend only — data_processor for all transforms; one direct DB read for team_id lookup
since data_processor has no get_team_id() function.
Executed directly by st.Page; no show() wrapper.
"""

import yaml
import streamlit as st
import pandas as pd

from backend import data_processor
from backend.database import get_connection


_BADGE_COLOR = {"W": "#2ecc71", "D": "#f39c12", "L": "#e74c3c"}
_RESULT_BG   = {"W": "background-color:#d4edda", "D": "background-color:#fff3cd", "L": "background-color:#f8d7da"}


def _load_competitions() -> list[dict]:
    with open("config/settings.yaml") as fh:
        return yaml.safe_load(fh).get("active_competitions", [])


def _get_team_id(team_name: str) -> int | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM teams WHERE name = ?", (team_name,)
        ).fetchone()
    return row["id"] if row else None


def _form_badge_html(result: str) -> str:
    color = _BADGE_COLOR.get(result, "#95a5a6")
    return (
        f'<div style="background:{color};color:white;text-align:center;'
        f'border-radius:5px;padding:7px 2px;font-weight:700;font-size:1em">'
        f'{result}</div>'
    )


def _color_result_cell(val: str) -> str:
    return _RESULT_BG.get(val, "")


def _render_form_guide(form_data: list[dict]) -> None:
    st.markdown("#### Form Guide (last 10)")
    if not form_data:
        st.caption("No form data yet.")
        return

    cols = st.columns(len(form_data))
    for col, match in zip(cols, form_data):
        with col:
            st.markdown(_form_badge_html(match["result"]), unsafe_allow_html=True)
            st.caption(match["date"][5:])


def _render_results_table(form_data: list[dict], team_name: str) -> None:
    st.markdown("#### Recent Results")
    if not form_data:
        st.caption("No results yet.")
        return

    rows = []
    for m in form_data:
        is_home = m["home"] == team_name
        rows.append({
            "Date":     m["date"],
            "H / A":   "Home" if is_home else "Away",
            "Opponent": m["away"] if is_home else m["home"],
            "Score":    m["score"],
            "Result":   m["result"],
        })

    df = pd.DataFrame(rows)
    styled = df.style.map(_color_result_cell, subset=["Result"])
    st.dataframe(styled, hide_index=True, use_container_width=True)


def _render_upcoming(upcoming_df: pd.DataFrame) -> None:
    st.markdown("#### Upcoming Fixtures")
    if upcoming_df.empty:
        st.caption("No upcoming fixtures found.")
        return

    display = upcoming_df[["date_label", "time_label", "home_team_name", "away_team_name"]].copy()
    display.columns = ["Date", "Kick-off (SG)", "Home", "Away"]
    st.dataframe(display, hide_index=True, use_container_width=True)


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("Teams")

try:
    competitions = _load_competitions()
except Exception:
    st.error("Could not load config — is config/settings.yaml present?")
    st.stop()

comp_names = [c["name"] for c in competitions]
comp_map   = {c["name"]: c["id"] for c in competitions}

# ── Selectors ─────────────────────────────────────────────────────────────────

sel_comp, sel_team_col = st.columns(2)

with sel_comp:
    selected_comp = st.selectbox("Competition", comp_names)

comp_id = comp_map[selected_comp]
standings_df = data_processor.format_standings(comp_id)

if standings_df.empty:
    st.info("No standings data yet — try refreshing.")
    st.stop()

team_names = standings_df["team_name"].tolist()

with sel_team_col:
    selected_team = st.selectbox("Team", team_names)

# ── Resolve team_id ───────────────────────────────────────────────────────────

team_id = _get_team_id(selected_team)
if team_id is None:
    st.warning(
        f"'{selected_team}' not yet in the teams table — "
        "run a data refresh to populate it."
    )
    st.stop()

# ── Season stats from standings ───────────────────────────────────────────────

team_row = standings_df[standings_df["team_name"] == selected_team]
if team_row.empty:
    st.warning("Standing data not found for this team.")
    st.stop()

r = team_row.iloc[0]

st.markdown(f"### {selected_team}")
st.caption(f"Position: **{int(r['position'])}** · {int(r['points'])} pts")

st.markdown("#### Season Statistics")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Played",  int(r["played"]))
c2.metric("Wins",    int(r["won"]))
c3.metric("Draws",   int(r["drawn"]))
c4.metric("Losses",  int(r["lost"]))

c5, c6, c7 = st.columns(3)
c5.metric("Goals For",     int(r["goals_for"]))
c6.metric("Goals Against", int(r["goals_against"]))
c7.metric("Goal Diff",     int(r["goal_difference"]))

st.divider()

# ── Form guide + recent results (shared data call) ────────────────────────────

form_data = data_processor.get_team_form(team_id, n=10)

_render_form_guide(form_data)
st.markdown("")
_render_results_table(form_data, selected_team)

st.divider()

# ── Upcoming fixtures ─────────────────────────────────────────────────────────

upcoming_df = data_processor.format_matches(
    comp_id, status="SCHEDULED", team_id=team_id, limit=5
)
_render_upcoming(upcoming_df)
