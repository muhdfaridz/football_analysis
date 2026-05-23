"""
fixtures.py — Fixtures and results calendar, filterable by competition and team.
Frontend only — import from backend.data_processor, never from raw API modules.
Executed directly by st.Page; no show() wrapper.
"""

import yaml
import streamlit as st
import pandas as pd

from backend import data_processor


def _load_competitions() -> list[dict]:
    with open("config/settings.yaml") as fh:
        return yaml.safe_load(fh).get("active_competitions", [])


def _score_badge(result_label: str) -> str:
    try:
        home_g, away_g = (int(x.strip()) for x in result_label.split(" - "))
        color = "#2ecc71" if home_g > away_g else ("#e74c3c" if home_g < away_g else "#f39c12")
    except Exception:
        color = "#95a5a6"
    return (
        f'<span style="background:{color};color:white;'
        f'padding:2px 10px;border-radius:4px;font-size:0.9em;'
        f'font-weight:600">{result_label}</span>'
    )


def _collect_teams(*dfs: pd.DataFrame) -> list[str]:
    """Return sorted unique team names from one or more matches DataFrames."""
    names: set[str] = set()
    for df in dfs:
        if not df.empty:
            names.update(df["home_team_name"].dropna())
            names.update(df["away_team_name"].dropna())
    return sorted(names)


def _apply_team_filter(df: pd.DataFrame, team: str) -> pd.DataFrame:
    if team == "All Teams" or df.empty:
        return df
    mask = (df["home_team_name"] == team) | (df["away_team_name"] == team)
    return df[mask].reset_index(drop=True)


def _fixture_row(home: str, centre_html: str, away: str) -> None:
    c1, c2, c3 = st.columns([3, 1, 3])
    with c1:
        st.markdown(
            f"<div style='text-align:right;font-weight:500;padding:3px 0'>{home}</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div style='text-align:center;padding:3px 0'>{centre_html}</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"<div style='font-weight:500;padding:3px 0'>{away}</div>",
            unsafe_allow_html=True,
        )


def _render_upcoming(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No upcoming fixtures — try refreshing.")
        return
    for date_label, group in df.groupby("date_label", sort=False):
        st.subheader(str(date_label))
        for _, row in group.iterrows():
            _fixture_row(
                home=row["home_team_name"],
                centre_html=f"<code>{row['time_label']}</code>",
                away=row["away_team_name"],
            )
        st.markdown("")


def _render_results(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No results yet — try refreshing.")
        return
    df = df.iloc[::-1].reset_index(drop=True)
    for date_label, group in df.groupby("date_label", sort=False):
        st.subheader(str(date_label))
        for _, row in group.iterrows():
            _fixture_row(
                home=row["home_team_name"],
                centre_html=_score_badge(row["result_label"]),
                away=row["away_team_name"],
            )
        st.markdown("")


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("Fixtures & Results")

try:
    competitions = _load_competitions()
except Exception:
    st.error("Could not load config — is config/settings.yaml present?")
    st.stop()

comp_names = [c["name"] for c in competitions]
comp_map = {c["name"]: c["id"] for c in competitions}

# ── Controls row ──────────────────────────────────────────────────────────────

ctrl_comp, ctrl_team = st.columns(2)

with ctrl_comp:
    selected_comp = st.selectbox("Competition", comp_names)

comp_id = comp_map[selected_comp]

upcoming_df = data_processor.format_matches(comp_id, status="SCHEDULED", limit=50)
results_df = data_processor.format_matches(comp_id, status="FINISHED", limit=50)

team_options = ["All Teams"] + _collect_teams(upcoming_df, results_df)

with ctrl_team:
    selected_team = st.selectbox("Team", team_options)

# ── Apply team filter ─────────────────────────────────────────────────────────

upcoming_filtered = _apply_team_filter(upcoming_df, selected_team)
results_filtered = _apply_team_filter(results_df, selected_team)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_up, tab_res = st.tabs(["Upcoming", "Results"])

with tab_up:
    _render_upcoming(upcoming_filtered)

with tab_res:
    _render_results(results_filtered)
