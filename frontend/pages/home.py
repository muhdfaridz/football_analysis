"""
home.py — Home page: today's fixtures, recent results, standings snapshot.
Frontend only — import from backend.data_processor, never from raw API modules.
Executed directly by st.Page; no show() wrapper.
"""

import yaml
import streamlit as st
import pandas as pd

from backend import data_processor


_RESULT_ICON = {"W": "🟢", "D": "🟡", "L": "🔴"}

_STANDINGS_COLS = [
    "position", "team_name", "played", "won", "drawn",
    "lost", "goal_difference", "points",
]
_STANDINGS_RENAME = {
    "position": "#", "team_name": "Team", "played": "P",
    "won": "W", "drawn": "D", "lost": "L",
    "goal_difference": "GD", "points": "Pts",
}


def _load_competitions() -> list[dict]:
    with open("config/settings.yaml") as fh:
        cfg = yaml.safe_load(fh)
    return cfg.get("active_competitions", [])


def _score_badge(result_label: str) -> str:
    """Wrap a score string in a coloured HTML badge."""
    try:
        home_g, away_g = (int(x.strip()) for x in result_label.split("-"))
        color = "#2ecc71" if home_g > away_g else ("#e74c3c" if home_g < away_g else "#f39c12")
    except Exception:
        color = "#95a5a6"
    return (
        f'<span style="background:{color};color:white;'
        f'padding:1px 7px;border-radius:4px;font-size:0.85em;'
        f'font-weight:600">{result_label}</span>'
    )


def _form_badges(form_list: list) -> str:
    return " ".join(_RESULT_ICON.get(r, "⬜") for r in form_list[-5:]) if form_list else "—"


def _render_fixtures(df: pd.DataFrame, comp_name: str) -> None:
    st.markdown(f"**{comp_name}**")
    if df.empty:
        st.caption("No data yet — try refreshing.")
        return
    for _, row in df.iterrows():
        when = f"{row['date_label']}  {row['time_label']}"
        st.markdown(
            f"<div style='margin-bottom:4px'>"
            f"<code style='font-size:0.8em'>{when}</code>&nbsp;&nbsp;"
            f"{row['home_team_name']} <b>vs</b> {row['away_team_name']}</div>",
            unsafe_allow_html=True,
        )


def _render_results(df: pd.DataFrame, comp_name: str) -> None:
    st.markdown(f"**{comp_name}**")
    if df.empty:
        st.caption("No data yet — try refreshing.")
        return
    for _, row in df.iterrows():
        badge = _score_badge(row["result_label"])
        st.markdown(
            f"<div style='margin-bottom:4px'>"
            f"{row['home_team_name']}&nbsp;{badge}&nbsp;{row['away_team_name']}"
            f"&nbsp;&nbsp;<small style='color:grey'>{row['date_label']}</small></div>",
            unsafe_allow_html=True,
        )


def _render_standings(df: pd.DataFrame, comp_name: str) -> None:
    st.markdown(f"**{comp_name} — Top 6**")
    if df.empty:
        st.caption("No data yet — try refreshing.")
        return

    available_cols = [c for c in _STANDINGS_COLS if c in df.columns]
    top6 = df.head(6)[available_cols].copy()
    top6 = top6.rename(columns=_STANDINGS_RENAME)

    if "form_list" in df.columns:
        top6["Form"] = df.head(6)["form_list"].apply(_form_badges)

    st.dataframe(top6, hide_index=True, use_container_width=True)


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("Football Dashboard")

try:
    competitions = _load_competitions()
except Exception:
    st.error("Could not load competition config — is config/settings.yaml present?")
    st.stop()

# ── Top section: Upcoming fixtures (left) | Recent results (right) ────────────

col_fix, col_res = st.columns(2)

with col_fix:
    st.subheader("Upcoming Fixtures")
    for comp in competitions:
        df = data_processor.format_matches(comp["id"], status="SCHEDULED", limit=10)
        _render_fixtures(df, comp["name"])
        st.markdown(" ")

with col_res:
    st.subheader("Recent Results")
    for comp in competitions:
        df = data_processor.format_matches(comp["id"], status="FINISHED", limit=5)
        _render_results(df, comp["name"])
        st.markdown(" ")

st.divider()

# ── Bottom section: Standings snapshot — top 6 side by side ──────────────────

st.subheader("Standings Snapshot")
stand_cols = st.columns(len(competitions))
for col, comp in zip(stand_cols, competitions):
    with col:
        df = data_processor.format_standings(comp["id"])
        _render_standings(df, comp["name"])
