# FOOTBALL_PROJECT_CONTEXT.md
# Football Analytics Web App — Single Source of Truth
# Last updated: May 2026 (v1 — initial setup)
# Owner: Ridz (Singapore)

---

## 1. Project Overview

A football analytics web dashboard targeting casual fans and fantasy football
players across Premier League and major European leagues. Built as a personal
passion project first, with a portfolio/AI engineering transition angle second,
and eventual YouTube/content layer third.

### Goals by Priority
1. **Portfolio piece** — demonstrates data engineering + AI + web app skills
   for AI engineering career transition (AISG AIAP / NTU SCTP context)
2. **Personal passion** — deep football fan (Premier League focus),
   Manchester United supporter
3. **Side income** — long-term, via YouTube content, sponsorships,
   or premium features

### Current Phase
**Phase 1 — Web Dashboard (MVP)**
Build a clean, data-rich dashboard covering player stats, team performance,
league standings, fixtures, and fantasy-relevant metrics.
No YouTube/content layer yet — that is Phase 3.

---

## 2. Target Audience

**Primary:** Casual Premier League and European football fans
- Want quick, visual access to stats, form, standings
- Not deeply technical — no xG models or heatmaps at MVP stage
- Mobile-friendly consumption preferred

**Secondary:** Fantasy football players (FPL, fantasy leagues)
- Care about: goals, assists, clean sheets, minutes played,
  form over last 5 games, injury status, fixture difficulty
- Want head-to-head player comparisons

---

## 3. Leagues & Competitions in Scope

| League | Country | Priority |
|---|---|---|
| Premier League | England | ⭐ Primary |
| UEFA Champions League | Europe | ⭐ Primary |
| La Liga | Spain | Secondary |
| Bundesliga | Germany | Secondary |
| Serie A | Italy | Secondary |
| Ligue 1 | France | Secondary |
| FA Cup / EFL Cup | England | Future |

Start with Premier League + Champions League only.
Add other leagues in Phase 2.

---

## 4. Data Sources

### Primary — football-data.org (FREE FOREVER)
- The most reliable free football API available in 2026
- Free tier covers: Premier League, Champions League, La Liga,
  Bundesliga, Serie A, Ligue 1, Eredivisie, Primeira Liga — permanently free
- Data available: fixtures, results, standings, top scorers,
  team info, head-to-head records
- Rate limit: 10 requests/minute on free tier
- Registration: free API key at football-data.org
- Python: `requests` library, clean REST JSON API
- Auth: `X-Auth-Token` header
- Base URL: `https://api.football-data.org/v4/`

**Key endpoints:**
```
GET /competitions/{id}/standings    → league table
GET /competitions/{id}/matches      → fixtures and results
GET /competitions/{id}/scorers      → top scorers
GET /teams/{id}                     → team profile
GET /teams/{id}/matches             → team fixtures/results
GET /persons/{id}                   → player profile
GET /matches/{id}                   → match detail
```

**Competition IDs (football-data.org):**
```
Premier League:      2021
Champions League:    2001
La Liga:             2014
Bundesliga:          2002
Serie A:             2019
Ligue 1:             2015
```

### Secondary — API-Football via RapidAPI (FREEMIUM)
- Free tier: 100 requests/day, 10 leagues
- Covers: player statistics (goals, assists, cards, minutes,
  ratings), lineups, predictions, head-to-head
- Upgrade path: $19/month (Pro) for 7,500 req/day + live data
- Use for: deeper player stats not available on football-data.org
- Auth: RapidAPI key in header

### Historical/Deep Analytics — StatsBomb Open Data (FREE)
- Free event-level football data with xG, freeze frames,
  and StatsBomb 360 data. Covers FA WSL, 2023 Women's World Cup,
  selected Champions League and La Liga seasons.
- Python package: `pip install statsbombpy`
- No API key needed for open data
- Use for: xG charts, shot maps, pass networks — Phase 2 analytics features
- Limitation: historical data only, not live/current season

### Fantasy Football — FPL Official API (FREE, UNDOCUMENTED)
- Official Fantasy Premier League API — free and always available
- Base URL: `https://fantasy.premierleague.com/api/`
- Provides: FPL player prices, points, form, ICT index,
  fixture difficulty ratings, ownership %
- No auth required — public endpoints
- Perfect for fantasy dashboard features

---

## 5. Tech Stack

### Frontend / Dashboard
- **Streamlit** — primary UI framework
- **Plotly** — charts and visualisations
- **Pandas** — data processing
- **Python 3.11+**

### Backend / Data Layer
- **SQLite** — local data caching (reduce API calls, stay within rate limits)
- **APScheduler** — scheduled data refresh (every 15 min for live matches,
  hourly for standings/stats)
- **Requests / HTTPX** — API calls
- **football-data.org** — primary data source
- **API-Football** — secondary (player stats)
- **statsbombpy** — historical analytics (Phase 2)
- **FPL API** — fantasy metrics

### Deployment
- **Local** for now (Ridz's machine)
- **Streamlit Cloud** (free tier) when ready to share publicly
- Future: Railway or Render for more control

---

## 6. App Structure

```
football-analytics/
│
├── FOOTBALL_PROJECT_CONTEXT.md     ← this file
│
├── backend/                        ← data layer, Claude Code scope
│   ├── football_data_api.py        # football-data.org connector
│   ├── api_football.py             # API-Football connector (RapidAPI)
│   ├── fpl_api.py                  # FPL official API connector
│   ├── statsbomb_loader.py         # StatsBomb open data loader (Phase 2)
│   ├── database.py                 # SQLite schema, queries, caching
│   ├── scheduler.py                # APScheduler refresh jobs
│   ├── data_processor.py           # Cleaning, transforming, aggregating
│   └── cache_manager.py            # Cache invalidation logic
│
├── frontend/                       ← Streamlit UI, VS Code scope
│   ├── app.py                      # Entry point, navigation
│   └── pages/
│       ├── home.py                 # Overview — today's matches, news ticker
│       ├── standings.py            # League tables
│       ├── fixtures.py             # Fixtures and results calendar
│       ├── teams.py                # Team profile, form, stats
│       ├── players.py              # Player profile, stats, comparison tool
│       ├── fantasy.py              # FPL metrics, recommendations
│       └── head_to_head.py         # H2H team and player comparisons
│
├── data/
│   └── football.db                 # SQLite database
│
├── config/
│   └── settings.yaml               # API keys, rate limits, refresh intervals
│
├── .env                            # Secrets — never commit
├── .env.example                    # Template
└── requirements.txt
```

---

## 7. Dashboard Pages (MVP)

### Home
- Today's fixtures with kick-off times (SG timezone, UTC+8)
- Live match scores (when API-Football Pro active)
- Recent results — last 5 matches per tracked league
- League standings snapshot (top 6 per league)

### Standings
- Full league table for selected competition
- Form guide (last 5 results — W/D/L badges)
- Goals scored / conceded
- Points gap from top 4 / relegation zone

### Fixtures & Results
- Calendar view by matchweek
- Filter by team or competition
- Match result detail (goals, scorers, cards)

### Team Profile
- Season stats (wins, draws, losses, GF, GA)
- Top scorers within team
- Recent form (last 10 matches)
- Upcoming fixtures with difficulty rating

### Player Profile
- Season stats (goals, assists, minutes, cards)
- Per-90 stats (Phase 2)
- FPL metrics (price, points, form, ownership %)
- Comparison tool — compare 2 players side by side

### Fantasy (FPL) Dashboard
- Top value picks by position (points per £)
- Form table — best performing players last 4 GWs
- Fixture difficulty ratings for next 5 gameweeks
- Price change predictions (risers/fallers)
- Differential picks (low ownership, high ceiling)

### Head to Head
- Historical H2H record between two teams
- Last 5 meetings with scores and scorers

---

## 8. Data Refresh Schedule

| Data type | Refresh frequency | API source |
|---|---|---|
| Live match scores | Every 60 seconds (match days only) | API-Football |
| Today's fixtures | Every 6 hours | football-data.org |
| League standings | Daily at 06:00 SG time | football-data.org |
| Top scorers | Daily at 06:00 SG time | football-data.org |
| Team stats | Daily at 06:00 SG time | API-Football |
| Player stats | Daily at 06:00 SG time | API-Football |
| FPL data | Daily at 08:00 SG time | FPL API |
| Historical data | On-demand only | StatsBomb |

All scheduled in APScheduler. Timezone: Asia/Singapore (UTC+8).

---

## 9. Configuration (settings.yaml)

```yaml
# API
football_data_org_key: ""         # from .env
api_football_key: ""              # from .env (RapidAPI)

# Rate limits
football_data_requests_per_min: 10
api_football_requests_per_day: 100   # free tier

# Competitions active (Phase 1)
active_competitions:
  - 2021   # Premier League
  - 2001   # Champions League

# Refresh schedule (SG time)
refresh_standings_time: "06:00"
refresh_fpl_time: "08:00"
live_score_interval_seconds: 60
timezone: "Asia/Singapore"

# Cache
cache_ttl_hours: 6
db_path: "data/football.db"

# Display
default_league: 2021              # Premier League
results_per_page: 20
```

---

## 10. Build Phases

### Phase 1 — Web Dashboard MVP (current)
- [ ] Repo scaffolding + settings.yaml + .env.example
- [ ] database.py — SQLite schema for matches, teams, players, standings
- [ ] football_data_api.py — standings, fixtures, results, top scorers
- [ ] fpl_api.py — FPL player data, prices, form, fixture difficulty
- [ ] data_processor.py — clean and transform raw API responses
- [ ] scheduler.py — daily refresh jobs
- [ ] cache_manager.py — TTL-based cache invalidation
- [ ] frontend/app.py — Streamlit shell, navigation
- [ ] pages/home.py — today's fixtures, recent results, standings snapshot
- [ ] pages/standings.py — full league table with form guide
- [ ] pages/fixtures.py — fixtures and results calendar
- [ ] pages/teams.py — team profile page
- [ ] pages/players.py — player profile + comparison tool
- [ ] pages/fantasy.py — FPL dashboard
- [ ] pages/head_to_head.py — H2H comparison

### Phase 2 — Deeper Analytics
- [ ] api_football.py — player ratings, lineups, predictions
- [ ] statsbomb_loader.py — xG, shot maps, pass networks
- [ ] Per-90 player stats
- [ ] xG chart per team/player
- [ ] Shot map visualisation
- [ ] Add La Liga, Bundesliga, Serie A, Ligue 1

### Phase 3 — Content Layer (YouTube / Social)
- [ ] Match preview generator (Claude API — key stats, H2H, form)
- [ ] Post-match report generator (Claude API — goals, ratings, analysis)
- [ ] Fantasy GW preview (Claude API — who to pick, who to avoid)
- [ ] Export to script format for YouTube voiceover
- [ ] AI voiceover (ElevenLabs) — same pipeline as dropship project

### Phase 4 — Monetisation
- [ ] Streamlit Cloud public deployment
- [ ] YouTube channel content from Phase 3 pipeline
- [ ] FPL premium tier (detailed differential picks, transfer planner)
- [ ] Sponsorship / affiliate (FPL tools, football betting affiliates)

---

## 11. Claude Surface Split

| Surface | Scope |
|---|---|
| **Claude Code** | backend/ — all API connectors, database, scheduler, data processor |
| **VS Code + Claude** | frontend/ — all Streamlit pages, charts, UI components |
| **Claude.ai Project** | Architecture decisions, feature planning, content strategy |

**Rule:** Backend exposes clean functions/DataFrames. Frontend consumes only.
No business logic in frontend files.

---

## 12. API Rate Limit Strategy

football-data.org free tier: 10 req/min — manageable with caching.
API-Football free tier: 100 req/day — must be used carefully.

**Caching strategy:**
- All API responses cached in SQLite with TTL timestamps
- On data request: check cache first → if fresh, serve from DB → if stale, call API
- This means API calls happen on schedule only, not on every user page load
- Mock data layer for development (same structure as live data)

---

## 13. Decisions & Rationale

| Decision | Rationale |
|---|---|
| football-data.org as primary | Free forever, 12 competitions, clean docs, reliable since 2013 |
| API-Football as secondary | Best player-level stats on free/low-cost tier |
| FPL API for fantasy layer | Official, free, no auth — perfect for fantasy features |
| StatsBomb deferred to Phase 2 | Historical only — not needed for MVP live dashboard |
| Streamlit for frontend | Ridz's existing skill, fast to build, deployable on Streamlit Cloud |
| SQLite caching | Protects API rate limits, faster page loads, works locally |
| SG timezone display | Target audience includes Ridz and SG-based fans |
| Premier League + UCL first | Highest interest, most data available, broadest audience |
| Content layer deferred to Phase 3 | Build data foundation first, content second |

---

## 14. Future Ideas (Backlog)

- WhatsApp/Telegram bot for match alerts and FPL tips
- Mobile app (React Native or Flutter) — Phase 4+
- Betting odds integration (for analytical display only)
- Player injury tracker with push notifications
- FPL mini-league tracker
- Manchester United dedicated deep-dive section
- European leagues expansion (Eredivisie, Liga Portugal)
- Women's football (FA WSL — StatsBomb has free data)

---

*Update this file after every meaningful session.*
*It is the shared source of truth across Claude Code, VS Code, and Claude.ai Project.*
