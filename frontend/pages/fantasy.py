"""
fantasy.py — FPL dashboard: value picks, form table, differentials.
Frontend only — data_processor for all FPL transforms;
database.get_fpl_current_gameweek() called directly for the GW display label.
Executed directly by st.Page; no show() wrapper.
"""

import streamlit as st
import pandas as pd

from backend import data_processor
from backend.database import get_fpl_current_gameweek


# ── Cell-level style functions ────────────────────────────────────────────────

def _price_style(val) -> str:
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    if v <= 6.0:
        return "background-color:#d4edda"
    if v <= 9.0:
        return "background-color:#fff3cd"
    return "background-color:#f8d7da"


def _form_style(val) -> str:
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    if v >= 8.0:
        return "background-color:#d4edda"
    if v >= 5.0:
        return "background-color:#fff3cd"
    return ""


def _ownership_style(val) -> str:
    """Lower ownership = more differential = greener."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    if v < 5.0:
        return "background-color:#d4edda"
    if v <= 10.0:
        return "background-color:#fff3cd"
    return "background-color:#f8d7da"


# ── Shared helpers ────────────────────────────────────────────────────────────

_SRC_COLS = [
    ("web_name",           "Player"),
    ("team_name",          "Team"),
    ("position_label",     "Pos"),
    ("now_cost",           "Price (£m)"),
    ("total_points",       "Pts"),
    ("points_per_million", "Pts/£m"),
    ("form",               "Form"),
    ("selected_by_percent","Own%"),
]

_COL_CONFIG = {
    "Player":    st.column_config.TextColumn(width="medium"),
    "Team":      st.column_config.TextColumn(width="medium"),
    "Pos":       st.column_config.TextColumn(width="small"),
    "Price (£m)":st.column_config.NumberColumn(format="£%.1f", width="small"),
    "Pts":       st.column_config.NumberColumn(width="small"),
    "Pts/£m":    st.column_config.NumberColumn(format="%.1f",  width="small"),
    "Form":      st.column_config.NumberColumn(format="%.1f",  width="small"),
    "Own%":      st.column_config.NumberColumn(format="%.1f%%",width="small"),
}


def _to_display(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "points_per_million" not in df.columns:
        df["points_per_million"] = (
            df["total_points"] / df["now_cost"].replace(0, float("nan"))
        ).round(1)

    src_order = [s for s, _ in _SRC_COLS if s in df.columns]
    rename     = {s: l for s, l in _SRC_COLS}
    return df[src_order].rename(columns=rename)


# ── Tab renderers ─────────────────────────────────────────────────────────────

def _value_tab(pos_arg: str | None) -> None:
    try:
        gw = get_fpl_current_gameweek()
    except Exception:
        gw = None

    gw_label = f"Gameweek {gw}" if gw else "Current Season"
    st.subheader(f"Best Value — {gw_label}")
    st.caption("Sorted by points per £m · available players only · min 450 mins")

    df = data_processor.get_value_picks(position=pos_arg, min_minutes=450)
    if df.empty:
        st.info("No FPL data yet — run a data refresh.")
        return

    display = _to_display(df)
    styled = display.style.map(_price_style, subset=["Price (£m)"])
    st.dataframe(styled, hide_index=True, use_container_width=True,
                 column_config=_COL_CONFIG)


def _form_tab(position: str, pos_arg: str | None) -> None:
    st.subheader("Form Table — Top 20")
    st.caption("FPL form rating (rolling 30-day) · min 450 mins · all positions")

    df = data_processor.get_form_table(n=20)
    if df.empty:
        st.info("No FPL data yet — run a data refresh.")
        return

    if pos_arg:
        df = df[df["position_label"] == pos_arg].reset_index(drop=True)

    if df.empty:
        st.info(f"No {position} players with enough minutes in the form table.")
        return

    display = _to_display(df)
    styled = display.style.map(_form_style, subset=["Form"])
    st.dataframe(styled, hide_index=True, use_container_width=True,
                 column_config=_COL_CONFIG)


def _differentials_tab(pos_arg: str | None) -> None:
    max_own = st.slider(
        "Max Ownership %", min_value=5.0, max_value=15.0,
        value=10.0, step=0.5, key="diff_own",
    )

    st.subheader("Differential Picks")
    st.caption(
        f"Ownership ≤ {max_own:.0f}% · sorted by FPL form · "
        "available players only · min 450 mins"
    )

    df = data_processor.get_differentials(
        position=pos_arg, max_ownership=max_own, n=15
    )
    if df.empty:
        st.info("No differentials found — try raising the ownership threshold.")
        return

    display = _to_display(df)
    styled = display.style.map(_ownership_style, subset=["Own%"])
    st.dataframe(styled, hide_index=True, use_container_width=True,
                 column_config=_COL_CONFIG)


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("Fantasy (FPL)")

position = st.radio(
    "Position",
    ["All", "GK", "DEF", "MID", "FWD"],
    horizontal=True,
    key="fpl_pos",
)
pos_arg = None if position == "All" else position

st.divider()

tab_val, tab_form, tab_diff = st.tabs(["Value Picks", "Form Table", "Differentials"])

with tab_val:
    _value_tab(pos_arg)

with tab_form:
    _form_tab(position, pos_arg)

with tab_diff:
    _differentials_tab(pos_arg)
