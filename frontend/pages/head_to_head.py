"""
head_to_head.py — Historical H2H record between two teams.
Direct DB reads via database module (data_processor has no H2H function).
Match results persist across rerenders via session_state — only refetched on Compare click.
Executed directly by st.Page; no show() wrapper.
"""

import pandas as pd
import streamlit as st

from backend.database import get_connection, get_matches


_SG_TZ = "Asia/Singapore"


def _load_teams() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name FROM teams ORDER BY name"
        ).fetchall()
    return [{"id": row["id"], "name": row["name"]} for row in rows]


def _load_comp_names() -> dict[int, str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name FROM competitions").fetchall()
    return {row["id"]: row["name"] for row in rows}


def _fetch_h2h(t1_id: int, t2_id: int) -> pd.DataFrame:
    """Fetch finished matches for Team 1, then keep only those involving Team 2."""
    df = get_matches(team_id=t1_id, status="FINISHED", limit=100)
    if df.empty:
        return df
    mask = (
        ((df["home_team_id"] == t1_id) & (df["away_team_id"] == t2_id)) |
        ((df["home_team_id"] == t2_id) & (df["away_team_id"] == t1_id))
    )
    return df[mask].reset_index(drop=True)


def _outcome(row: pd.Series, t1_id: int) -> str:
    """Return 'T1' | 'Draw' | 'T2' from Team 1's perspective."""
    winner = row.get("winner")
    if winner == "DRAW":
        return "Draw"
    is_home = row["home_team_id"] == t1_id
    if (is_home and winner == "HOME_TEAM") or (not is_home and winner == "AWAY_TEAM"):
        return "T1"
    return "T2"


def _to_sg_date(utc_series: pd.Series) -> pd.Series:
    return (
        pd.to_datetime(utc_series, utc=True)
        .dt.tz_convert(_SG_TZ)
        .dt.strftime("%d %b %Y")
    )


def _render_h2h(
    df: pd.DataFrame,
    t1_id: int,
    t1_name: str,
    t2_name: str,
) -> None:
    total = len(df)

    st.markdown(
        f"### {t1_name}  vs  {t2_name} — "
        f"{total} meeting{'s' if total != 1 else ''}"
    )

    if total < 3:
        st.info(
            "Limited history in database — only current season data is cached. "
            "H2H records will grow as more matches are stored."
        )

    if total == 0:
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric(f"{t1_name} Wins", 0)
        mc2.metric("Draws", 0)
        mc3.metric(f"{t2_name} Wins", 0)
        return

    outcomes = df.apply(_outcome, axis=1, t1_id=t1_id)
    t1_wins = int((outcomes == "T1").sum())
    draws    = int((outcomes == "Draw").sum())
    t2_wins  = int((outcomes == "T2").sum())

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric(f"{t1_name} Wins", t1_wins)
    mc2.metric("Draws", draws)
    mc3.metric(f"{t2_name} Wins", t2_wins)

    st.divider()

    comp_names = _load_comp_names()

    tbl = df[["utc_date", "home_team_name", "home_score",
              "away_score", "away_team_name", "competition_id"]].copy()

    tbl["Date"] = _to_sg_date(tbl["utc_date"])
    tbl["Score"] = tbl.apply(
        lambda r: (
            f"{int(r['home_score'])} - {int(r['away_score'])}"
            if pd.notna(r["home_score"]) and pd.notna(r["away_score"])
            else "–"
        ),
        axis=1,
    )
    tbl["Competition"] = tbl["competition_id"].map(
        lambda cid: comp_names.get(int(cid), f"Comp {cid}")
    )

    display = (
        tbl[["Date", "home_team_name", "Score", "away_team_name", "Competition"]]
        .rename(columns={"home_team_name": "Home", "away_team_name": "Away"})
        .iloc[::-1]
        .reset_index(drop=True)
    )

    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Date":        st.column_config.TextColumn(width="small"),
            "Home":        st.column_config.TextColumn(width="medium"),
            "Score":       st.column_config.TextColumn(width="small"),
            "Away":        st.column_config.TextColumn(width="medium"),
            "Competition": st.column_config.TextColumn(width="medium"),
        },
    )


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("Head to Head")

teams = _load_teams()
if not teams:
    st.info("No team data yet — run a data refresh.")
    st.stop()

names  = [t["name"] for t in teams]
id_map = {t["name"]: t["id"] for t in teams}

# ── Team selectors ────────────────────────────────────────────────────────────

col1, col2 = st.columns(2)
with col1:
    t1_name = st.selectbox("Team 1", names, index=0, key="h2h_t1")
with col2:
    t2_name = st.selectbox("Team 2", names, index=min(1, len(names) - 1), key="h2h_t2")

if st.button("Compare", type="primary"):
    st.session_state.update({
        "h2h_t1_id":   id_map[t1_name],
        "h2h_t2_id":   id_map[t2_name],
        "h2h_t1_name": t1_name,
        "h2h_t2_name": t2_name,
    })

# ── Results (persist until next Compare click) ────────────────────────────────

if "h2h_t1_id" not in st.session_state:
    st.caption("Select two teams above and click Compare.")
    st.stop()

t1_id   = st.session_state["h2h_t1_id"]
t2_id   = st.session_state["h2h_t2_id"]
t1_disp = st.session_state["h2h_t1_name"]
t2_disp = st.session_state["h2h_t2_name"]

if t1_id == t2_id:
    st.warning("Please select two different teams.")
    st.stop()

st.divider()
h2h_df = _fetch_h2h(t1_id, t2_id)
_render_h2h(h2h_df, t1_id, t1_disp, t2_disp)
