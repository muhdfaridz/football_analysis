"""
players.py — Top scorers and FPL player search / comparison tool.
Frontend only — data_processor for scorers; database.get_fpl_players used directly
for the search tab (data_processor has no flexible FPL player query wrapper).
Executed directly by st.Page; no show() wrapper.
"""

import yaml
import streamlit as st
import pandas as pd

from backend import data_processor
from backend.database import get_fpl_players


_MEDAL_BG = {1: "#FFF3C4", 2: "#F0F0F0", 3: "#FFE0C4"}

_STATUS_ICON = {"a": "✅", "d": "⚠️", "i": "🚑", "s": "🚫", "u": "❌"}

_SORT_COLS = {
    "Total Points": ("total_points", False),
    "Form":         ("form",         False),
    "Goals":        ("goals_scored", False),
    "Assists":      ("assists",      False),
}

_SEARCH_DISPLAY_COLS = [
    ("web_name",       "Player"),
    ("team_name",      "Team"),
    ("position_label", "Pos"),
    ("now_cost",       "Price (£m)"),
    ("total_points",   "Pts"),
    ("form",           "Form"),
    ("minutes",        "Mins"),
    ("goals_scored",   "G"),
    ("assists",        "A"),
    ("clean_sheets",   "CS"),
    ("bonus",          "Bonus"),
    ("ict_index",      "ICT"),
    ("status",         "Status"),
]


def _load_competitions() -> list[dict]:
    with open("config/settings.yaml") as fh:
        return yaml.safe_load(fh).get("active_competitions", [])


# ── Top Scorers ───────────────────────────────────────────────────────────────

def _medal_style(row: pd.Series) -> list[str]:
    bg = _MEDAL_BG.get(int(row["Rank"]), "")
    return [f"background-color:{bg}" if bg else "" for _ in row]


def _render_top_scorers(competitions: list[dict]) -> None:
    comp_names = [c["name"] for c in competitions]
    comp_map = {c["name"]: c["id"] for c in competitions}

    selected = st.selectbox("Competition", comp_names, key="scorers_comp")
    comp_id = comp_map[selected]

    df = data_processor.get_top_scorers_display(comp_id)
    if df.empty:
        st.info("No scorer data yet — try refreshing.")
        return

    cols = ["player_name", "team_name", "goals", "assists", "penalties",
            "played_matches", "goals_per_game"]
    avail = [c for c in cols if c in df.columns]
    display = df[avail].copy()
    display.insert(0, "Rank", range(1, len(display) + 1))
    display.columns = ["Rank", "Player", "Team", "Goals", "Assists",
                       "Pens", "Games", "G/Game"]

    styled = display.style.apply(_medal_style, axis=1)
    st.dataframe(styled, hide_index=True, use_container_width=True)


# ── Player Search ─────────────────────────────────────────────────────────────

def _sort_df(df: pd.DataFrame, sort_by: str) -> pd.DataFrame:
    if sort_by == "Value (pts/£m)":
        df = df.copy()
        df["_value"] = (
            df["total_points"] / df["now_cost"].replace(0, float("nan"))
        ).round(1)
        return df.sort_values("_value", ascending=False).drop(
            columns=["_value"]
        ).reset_index(drop=True)
    col, asc = _SORT_COLS.get(sort_by, ("total_points", False))
    return df.sort_values(col, ascending=asc).reset_index(drop=True)


def _comparison_metrics(p1: pd.Series, p2: pd.Series) -> None:
    int_metrics = [
        ("Total Points",  "total_points"),
        ("Goals",         "goals_scored"),
        ("Assists",       "assists"),
        ("Clean Sheets",  "clean_sheets"),
    ]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{p1['web_name']}** — {p1['team_name']}")
        if (p1.get("status") or "a") != "a":
            st.warning(p1.get("news") or "Availability concern")
        for label, field in int_metrics:
            st.metric(label, int(p1[field] or 0))
        st.metric("Price (£m)", f"£{float(p1['now_cost'] or 0):.1f}m")
        st.metric("Form",       round(float(p1["form"]      or 0), 1))
        st.metric("ICT Index",  round(float(p1["ict_index"] or 0), 1))

    with col2:
        st.markdown(f"**{p2['web_name']}** — {p2['team_name']}  *(vs Player 1)*")
        if (p2.get("status") or "a") != "a":
            st.warning(p2.get("news") or "Availability concern")
        for label, field in int_metrics:
            v1, v2 = int(p1[field] or 0), int(p2[field] or 0)
            st.metric(label, v2, delta=v2 - v1)
        v1_p = float(p1["now_cost"] or 0)
        v2_p = float(p2["now_cost"] or 0)
        st.metric("Price (£m)", f"£{v2_p:.1f}m", delta=round(v2_p - v1_p, 1))
        v1_f = float(p1["form"] or 0)
        v2_f = float(p2["form"] or 0)
        st.metric("Form", round(v2_f, 1), delta=round(v2_f - v1_f, 1))
        v1_i = float(p1["ict_index"] or 0)
        v2_i = float(p2["ict_index"] or 0)
        st.metric("ICT Index", round(v2_i, 1), delta=round(v2_i - v1_i, 1))


def _render_player_search() -> None:
    fc1, fc2, fc3, fc4 = st.columns(4)

    with fc1:
        position = st.selectbox(
            "Position", ["All", "GK", "DEF", "MID", "FWD"], key="ps_pos"
        )
    with fc2:
        min_mins = st.slider("Min Minutes", 0, 2000, 450, key="ps_mins")
    with fc3:
        max_price = st.slider(
            "Max Price (£m)", min_value=4.0, max_value=15.0,
            value=15.0, step=0.5, key="ps_price",
        )
    with fc4:
        sort_by = st.selectbox(
            "Sort By",
            ["Total Points", "Form", "Goals", "Assists", "Value (pts/£m)"],
            key="ps_sort",
        )

    pos_arg = None if position == "All" else position
    raw_df = get_fpl_players(position=pos_arg, min_minutes=min_mins)

    if raw_df.empty:
        st.info("No FPL player data yet — run a data refresh.")
        return

    df = raw_df[raw_df["now_cost"] <= max_price].copy()
    df = _sort_df(df, sort_by)

    if df.empty:
        st.info("No players match the current filters.")
        return

    avail_src = [src for src, _ in _SEARCH_DISPLAY_COLS if src in df.columns]
    rename_map = {src: lbl for src, lbl in _SEARCH_DISPLAY_COLS}

    display = df[avail_src].copy()
    if "status" in display.columns:
        display["status"] = display["status"].map(
            lambda s: _STATUS_ICON.get(s or "a", s or "?")
        )
    display = display.rename(columns=rename_map)

    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Player": st.column_config.TextColumn(width="medium"),
            "Team":   st.column_config.TextColumn(width="medium"),
        },
    )

    st.divider()

    st.markdown("#### Player Comparison")

    if len(df) < 2:
        st.caption("Need at least 2 players in results to compare — adjust filters.")
        return

    labels = [
        f"{row['web_name']} ({row['team_name']})"
        for _, row in df.iterrows()
    ]

    sel_col1, sel_col2 = st.columns(2)
    with sel_col1:
        p1_idx = st.selectbox(
            "Player 1",
            range(len(labels)),
            format_func=lambda i: labels[i],
            key="cmp_p1",
        )
    with sel_col2:
        p2_idx = st.selectbox(
            "Player 2",
            range(len(labels)),
            format_func=lambda i: labels[i],
            index=min(1, len(labels) - 1),
            key="cmp_p2",
        )

    _comparison_metrics(df.iloc[p1_idx], df.iloc[p2_idx])


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("Players")

try:
    competitions = _load_competitions()
except Exception:
    st.error("Could not load config — is config/settings.yaml present?")
    st.stop()

tab_scorers, tab_search = st.tabs(["Top Scorers", "Player Search"])

with tab_scorers:
    _render_top_scorers(competitions)

with tab_search:
    _render_player_search()
