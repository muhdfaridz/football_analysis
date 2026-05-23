"""
standings.py — Full league table with form guide and zone highlights.
Frontend only — import from backend.data_processor, never from raw API modules.
Executed directly by st.Page; no show() wrapper.
"""

import yaml
import streamlit as st
import pandas as pd

from backend import data_processor


_RESULT_ICON = {"W": "🟢", "D": "🟡", "L": "🔴"}

_ZONE_BG = {
    "cl":   "#dbeafe",   # top 4 — Champions League
    "el":   "#fed7aa",   # 5th  — Europa League
    "uecl": "#fef9c3",   # 6th  — Conference League
    "rel":  "#fecaca",   # last 3 — relegation
}

_DISPLAY_COLS = [
    "position", "team_name", "played", "won", "drawn", "lost",
    "goals_for", "goals_against", "goal_difference", "points",
]
_RENAME = {
    "position": "Pos", "team_name": "Club",
    "played": "P", "won": "W", "drawn": "D", "lost": "L",
    "goals_for": "GF", "goals_against": "GA",
    "goal_difference": "GD", "points": "Pts",
}
_COL_CONFIG = {
    "Pos":  st.column_config.NumberColumn(width="small"),
    "Club": st.column_config.TextColumn(width="large"),
    "P":    st.column_config.NumberColumn(width="small"),
    "W":    st.column_config.NumberColumn(width="small"),
    "D":    st.column_config.NumberColumn(width="small"),
    "L":    st.column_config.NumberColumn(width="small"),
    "GF":   st.column_config.NumberColumn(width="small"),
    "GA":   st.column_config.NumberColumn(width="small"),
    "GD":   st.column_config.NumberColumn(width="small"),
    "Pts":  st.column_config.NumberColumn(width="small"),
    "Form": st.column_config.TextColumn(width="medium"),
}


def _load_competitions() -> list[dict]:
    with open("config/settings.yaml") as fh:
        return yaml.safe_load(fh).get("active_competitions", [])


def _form_str(form_list: list) -> str:
    return " ".join(_RESULT_ICON.get(r, "⬜") for r in form_list[-5:]) if form_list else "—"


def _row_style(row: pd.Series, max_pos: int) -> list[str]:
    pos = row["Pos"]
    if pos <= 4:
        color = _ZONE_BG["cl"]
    elif pos == 5:
        color = _ZONE_BG["el"]
    elif pos == 6:
        color = _ZONE_BG["uecl"]
    elif pos > max_pos - 3:
        color = _ZONE_BG["rel"]
    else:
        color = ""
    bg = f"background-color: {color}" if color else ""
    return [bg] * len(row)


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("Standings")

try:
    competitions = _load_competitions()
except Exception:
    st.error("Could not load config — is config/settings.yaml present?")
    st.stop()

comp_names = [c["name"] for c in competitions]
comp_map = {c["name"]: c["id"] for c in competitions}

selected = st.selectbox("Competition", comp_names)
comp_id = comp_map[selected]

# ── Full league table ─────────────────────────────────────────────────────────

df = data_processor.format_standings(comp_id)
if df.empty:
    st.info("No data yet — try refreshing.")
    st.stop()

avail = [c for c in _DISPLAY_COLS if c in df.columns]
display = df[avail].rename(columns=_RENAME).copy()

if "form_list" in df.columns:
    display["Form"] = df["form_list"].apply(_form_str)

max_pos = int(display["Pos"].max())

styled = display.style.apply(
    lambda row: _row_style(row, max_pos=max_pos),
    axis=1,
)

st.dataframe(
    styled,
    hide_index=True,
    use_container_width=True,
    column_config=_COL_CONFIG,
)

st.caption(
    "🔵 Champions League &nbsp;|&nbsp; 🟠 Europa League &nbsp;|&nbsp; "
    "🟡 Conference League &nbsp;|&nbsp; 🔴 Relegation zone",
    unsafe_allow_html=True,
)

st.divider()

# ── Metrics: leader + top scorer ──────────────────────────────────────────────

leader = df.iloc[0]
scorers_df = data_processor.get_top_scorers_display(comp_id)

col1, col2 = st.columns(2)

with col1:
    st.metric(
        label=f"League Leader — {leader['team_name']}",
        value=f"{int(leader['points'])} pts",
    )

with col2:
    if scorers_df.empty:
        st.metric(label="Top Scorer", value="No data yet")
    else:
        top = scorers_df.iloc[0]
        st.metric(
            label=f"Top Scorer — {top['player_name']}",
            value=f"{int(top['goals'])} goals",
        )
