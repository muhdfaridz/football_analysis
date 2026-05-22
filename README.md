# Football Analytics

A football analytics web dashboard for Premier League and Champions League fans.
Built with Python, Streamlit, and SQLite.

## Setup

```bash
# 1. Clone and enter the repo
git clone <your-repo-url>
cd football-analytics

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys
cp .env.example .env
# Edit .env and add your football-data.org key

# 5. Initialise the database
python -c "from backend.database import init_db; init_db()"

# 6. Run the dashboard
streamlit run frontend/app.py
```

## API Keys

| Source | Where to get | Required |
|---|---|---|
| football-data.org | https://www.football-data.org/client/register | Yes (free) |
| API-Football (RapidAPI) | https://rapidapi.com/api-sports/api/api-football | Phase 2 |

## Project Structure

```
football-analytics/
├── backend/            ← data layer (API connectors, DB, scheduler)
│   ├── database.py     ← SQLite schema + all query/upsert functions
│   ├── football_data_api.py
│   ├── fpl_api.py
│   ├── data_processor.py
│   ├── scheduler.py
│   └── cache_manager.py
├── frontend/           ← Streamlit UI
│   ├── app.py
│   └── pages/
├── config/
│   └── settings.yaml
├── data/               ← football.db lives here (gitignored)
├── .env.example
└── requirements.txt
```

## Phase 1 Scope

- Premier League + UEFA Champions League
- Standings, Fixtures, Results, Top Scorers
- Team profiles, Player profiles
- FPL fantasy dashboard
- Head-to-head comparisons

See `FOOTBALL_PROJECT_CONTEXT.md` for full project spec.
