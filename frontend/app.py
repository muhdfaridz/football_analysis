"""
app.py — Streamlit entry point and navigation shell.

Run with: streamlit run frontend/app.py

Uses st.navigation / st.Page so Streamlit's automatic filename-based
multipage routing is overridden and all navigation goes through this file.
Pages are executed directly from their file paths; no show() indirection.
"""

import atexit

import streamlit as st

from backend.database import get_cache_status, init_db
from backend.scheduler import shutdown_scheduler, start_scheduler

# ── Page config (must be first Streamlit call) ────────────────────────────────

st.set_page_config(
    page_title="Football Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── One-time startup (guarded by session_state) ───────────────────────────────

if "scheduler" not in st.session_state:
    init_db()
    _sched = start_scheduler()
    st.session_state["scheduler"] = _sched
    atexit.register(shutdown_scheduler, _sched)

# ── Sidebar brand header ──────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚽ Football Analytics")
    st.markdown("---")

# ── Navigation ────────────────────────────────────────────────────────────────

pg = st.navigation([
    st.Page("pages/home.py",         title="Home",         icon="🏠"),
    st.Page("pages/standings.py",    title="Standings",    icon="📊"),
    st.Page("pages/fixtures.py",     title="Fixtures",     icon="📅"),
    st.Page("pages/teams.py",        title="Teams",        icon="🏟️"),
    st.Page("pages/players.py",      title="Players",      icon="👤"),
    st.Page("pages/fantasy.py",      title="Fantasy",      icon="⚽"),
    st.Page("pages/head_to_head.py", title="Head to Head", icon="⚔️"),
])

# ── Sidebar cache status footer ───────────────────────────────────────────────

with st.sidebar:
    st.markdown("---")
    st.markdown("**Last Refresh**")

    try:
        cache_df = get_cache_status()
        if cache_df.empty:
            st.caption("No cache data yet.")
        else:
            seen = set()
            for _, row in cache_df.iterrows():
                key = row["cache_key"]
                if key in seen:
                    continue
                seen.add(key)

                icon = "✅" if row["status"] == "ok" else "⚠️"
                fetched = row["fetched_at"] or "—"
                if fetched and len(fetched) >= 16:
                    fetched = fetched[5:16]

                st.caption(f"{icon} `{key}` {fetched}")
    except Exception:
        st.caption("Cache status unavailable.")

# ── Execute selected page ─────────────────────────────────────────────────────

pg.run()
