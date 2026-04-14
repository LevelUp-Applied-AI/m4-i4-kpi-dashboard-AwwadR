# Tier 3 Dash App Architecture

## Overview
This project extends the KPI dashboard into a multi-page Dash analytical report.

## File Structure
- `app.py`: main Dash application entry point, page navigation, and shared state
- `dash_data.py`: shared data access, cleaning, filtering, KPI preparation, and figure builders
- `pages/overview.py`: Page 1, KPI overview with gauge indicators and city selector
- `pages/time_series.py`: Page 2, time-series deep dive with date range selector
- `pages/cohorts.py`: Page 3, cohort comparison with drill-down interaction
- `assets/style.css`: simple local styling for the Dash app

## Data Flow
1. The application loads and cleans the Amman Digital Market data through `dash_data.py`.
2. Page 1 allows the user to select a city.
3. The selected city is stored in `dcc.Store(id="global-filters")`.
4. Page 2 reads the selected city from the shared store and applies an additional date range filter.
5. Page 3 also reads the selected city from the shared store and updates the cohort comparison.
6. Clicking a cohort bar on Page 3 triggers a drill-down chart showing category revenue for that selected cohort.

## Cross-Filtering
Cross-filtering is implemented by storing the selected city on Page 1 and reusing it in callback functions on Pages 2 and 3.

## Local Run
Run the app locally with:

```bash
python app.py
```