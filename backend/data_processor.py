"""
data_processor.py — data cleaning, transformation, and aggregation.

This is the only module the frontend imports from.
All functions accept raw API dicts or DB DataFrames and return
clean, display-ready DataFrames.

No API calls here. No DB writes here. Transform only.
"""

# TODO: Implement in Claude Code / VS Code
# Key functions to build:
#
# Standings:
#   format_standings(df) -> pd.DataFrame
#     - Add rank delta, form badges (W/D/L), points-from-top-4 column
#
# Fixtures:
#   format_fixtures(df, tz="Asia/Singapore") -> pd.DataFrame
#     - Convert utc_date to SG time
#     - Add display columns: kick_off_sg, date_label, time_label
#
# Form:
#   parse_form_string(form_str) -> list[str]
#     - "W,D,L,W,W" -> ["W", "D", "L", "W", "W"]
#
# FPL:
#   add_points_per_million(df) -> pd.DataFrame
#     - Compute total_points / now_cost → value column
#   get_top_value_picks(df, position, n=10) -> pd.DataFrame
#   get_differential_picks(df, max_ownership=10.0, n=10) -> pd.DataFrame
#   get_form_table(df, n=20) -> pd.DataFrame
