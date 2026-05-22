"""
app.py — Streamlit entry point and navigation shell.

Run with: streamlit run frontend/app.py

Pages:
  Home          → pages/home.py
  Standings     → pages/standings.py
  Fixtures      → pages/fixtures.py
  Teams         → pages/teams.py
  Players       → pages/players.py
  Fantasy (FPL) → pages/fantasy.py
  Head to Head  → pages/head_to_head.py

This file handles:
  - Page config (title, icon, layout)
  - Sidebar navigation
  - Scheduler startup on first load
  - DB init check

Frontend only — no business logic here.
All data comes from backend.data_processor functions.
"""

# TODO: Implement in VS Code
import streamlit as st

st.set_page_config(
    page_title="Football Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚽ Football Analytics")
st.info("Dashboard coming soon. Backend data layer is being built.")
