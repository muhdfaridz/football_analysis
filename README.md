# ⚽ Football Analytics

A personal football analytics web dashboard for Premier League and Champions League fans — covering live standings, fixtures, results, top scorers, team profiles, and an FPL fantasy dashboard.

Built as a portfolio project demonstrating data engineering, API integration, and web app development in Python.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38-red?logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-cached-lightgrey?logo=sqlite)
![Phase](https://img.shields.io/badge/Phase-1%20MVP-orange)

---

## What It Does

| Page | Description |
|---|---|
| **Home** | Today's fixtures (SG time), recent results, standings snapshot |
| **Standings** | Full league table with form guide (W/D/L badges) |
| **Fixtures** | Calendar view by matchweek, filterable by team |
| **Teams** | Team profile — season stats, form, upcoming fixtures |
| **Players** | Player stats, FPL metrics, side-by-side comparison tool |
| **Fantasy (FPL)** | Top value picks, form table, fixture difficulty ratings |
| **Head to Head** | Historical H2H record between any two teams |

**Leagues covered (Phase 1):** Premier League · UEFA Champions League

---

## Tech Stack

- **Frontend** — Streamlit + Plotly
- **Backend** — Python 3.11, Requests, Pandas
- **Database** — SQLite (local caching layer)
- **Scheduler** — APScheduler (daily refresh jobs)
- **Data sources** — football-data.org, FPL Official API, API-Football

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/your-username/football-analytics.git
cd football-analytics
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your API key

```bash
cp .env.example .env
```

Open `.env` and add your [football-data.org](https://www.football-data.org/client/register) key (free registration):

```
FOOTBALL_DATA_ORG_KEY=your_key_here
```

### 5. Initialise the database

```bash
python -c "from backend.database import init_db; init_db()"
```

### 6. Run the dashboard

```bash
streamlit run frontend/app.py
```

---

## API Keys

| Source | Free Tier | Required | Where to Get |
|---|---|---|---|
| football-data.org | ✅ Free forever | Phase 1 | [Register here](https://www.football-data.org/client/register) |
| FPL Official API | ✅ Free, no auth | Phase 1 | No key needed |
| API-Football (RapidAPI) | 100 req/day | Phase 2 | [RapidAPI](https://rapidapi.com/api-sports/api/api-football) |

> **Never commit your `.env` file.** It is already in `.gitignore`.

---

## Project Structure

```
football-analytics/
│
├── backend/                    ← data layer
│   ├── database.py             # SQLite schema, upserts, query functions
│   ├── football_data_api.py    # football-data.org connector
│   ├── fpl_api.py              # FPL official API connector
│   ├── data_processor.py       # cleaning, transforms, aggregation
│   ├── scheduler.py            # APScheduler refresh jobs
│   ├── cache_manager.py        # TTL-based cache invalidation
│   └── api_football.py         # API-Football connector (Phase 2)
│
├── frontend/                   ← Streamlit UI
│   ├── app.py                  # entry point, navigation
│   └── pages/
│       ├── home.py
│       ├── standings.py
│       ├── fixtures.py
│       ├── teams.py
│       ├── players.py
│       ├── fantasy.py
│       └── head_to_head.py
│
├── config/
│   └── settings.yaml           # rate limits, refresh schedule, competition IDs
│
├── data/
│   └── football.db             # SQLite database (gitignored)
│
├── .env.example                # API key template
├── .gitignore
└── requirements.txt
```

---

## Data Refresh Schedule

All times in **Singapore Time (UTC+8)**.

| Data | Frequency | Source |
|---|---|---|
| League standings | Daily 06:00 | football-data.org |
| Fixtures & results | Every 6 hours | football-data.org |
| Top scorers | Daily 06:00 | football-data.org |
| FPL player data | Daily 08:00 | FPL Official API |
| Live scores | Every 60s (match days) | API-Football (Phase 2) |

---

## Roadmap

- [x] Repo scaffold + database schema
- [ ] football_data_api.py — standings, fixtures, results, scorers
- [ ] fpl_api.py — player prices, form, fixture difficulty
- [ ] data_processor.py — transforms and display formatting
- [ ] scheduler.py — automated refresh jobs
- [ ] Frontend — all 7 dashboard pages
- [ ] **Phase 2** — deeper player stats, xG charts, additional leagues
- [ ] **Phase 3** — AI-generated match previews and FPL tips (Claude API)

---

## Architecture Notes

**Caching is non-negotiable.** football-data.org allows 10 requests/minute and API-Football's free tier allows 100/day. Every API response is cached in SQLite with a TTL. Page loads always read from the database — API calls only happen on the scheduled refresh jobs.

**Backend/frontend separation is strict.** The backend exposes clean DataFrames. Frontend pages only import from `data_processor.py` — never from raw API modules or the database directly.

---

## Acknowledgements

- [football-data.org](https://www.football-data.org) — reliable free football data since 2013
- [Fantasy Premier League API](https://fantasy.premierleague.com/api/bootstrap-static/) — official FPL data
- [StatsBomb Open Data](https://github.com/statsbomb/open-data) — free event-level data (Phase 2)
