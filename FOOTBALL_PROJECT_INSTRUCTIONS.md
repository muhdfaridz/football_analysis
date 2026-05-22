# Claude Project Instructions — Football Analytics Web App

## What This Project Is
A football analytics web dashboard for casual fans and fantasy football players.
Covers Premier League and major European leagues.
Built by Ridz — a Singapore-based data analyst with strong Python/Streamlit skills.

## Always Do This First
Read FOOTBALL_PROJECT_CONTEXT.md before responding.
It is the single source of truth. If I paste or upload an updated version,
use that as the latest state.

## My Technical Profile
- Strong: Python, Pandas, Streamlit, SQL, REST APIs, data visualisation
- Comfortable: APScheduler, SQLite, Plotly
- Learning: AI/LLM integration, agentic systems
- Stack: Python 3.11+, Streamlit, SQLite, APScheduler, Plotly, Requests

## Claude Surface Split
- Claude Code → backend/ (API connectors, database, scheduler, data processor)
- VS Code → frontend/ (Streamlit pages, charts, UI)
- This Project → architecture decisions, feature planning, content strategy

Never suggest Streamlit UI code in a backend context.
Never suggest business logic in a frontend file.
Backend always exposes clean DataFrames or dicts. Frontend only consumes.

## Primary Data Sources
- football-data.org — free forever, primary source (standings, fixtures, results)
- API-Football via RapidAPI — secondary (player stats, 100 req/day free)
- FPL Official API — fantasy metrics, free, no auth needed
- StatsBomb Open Data — historical analytics, Phase 2 only

## Current Phase
Phase 1 — Web Dashboard MVP
Focus: get the dashboard built and functional with real data.
Do not suggest Phase 2 (deep analytics) or Phase 3 (content layer) features
unless I specifically ask. Keep scope tight.

## My Preferences
- Be direct and concise — structured responses over long prose
- Suggest the simplest solution that works before the clever one
- Always respect API rate limits — caching in SQLite is non-negotiable
- Mock data layer must mirror live data structure exactly
- Flag decisions that should update FOOTBALL_PROJECT_CONTEXT.md
- When I ask about data availability, check against the API tier we are on

## Leagues in Scope (Phase 1 Only)
- Premier League (ID: 2021)
- UEFA Champions League (ID: 2001)
Do not expand to other leagues until I say Phase 2 is starting.

## Timezone
All times display in Singapore timezone (UTC+8, Asia/Singapore).
Match kick-off times must always be converted to SG time for display.

## Deployment
Local machine only for now. Do not suggest cloud deployment setup
until I ask. Keep it simple.
