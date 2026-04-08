[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/FBI2cyc1)
# Integration 4 — KPI Dashboard: Amman Digital Market

Design a KPI framework, compute metrics from the Amman Digital Market database, validate patterns with statistical tests, and produce an executive summary with supporting visualizations.

## Setup

1. Start PostgreSQL container:
   ```bash
   docker run -d --name postgres-m4-int \
     -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=amman_market \
     -p 5432:5432 -v pgdata_m4_int:/var/lib/postgresql/data \
     postgres:15-alpine
   ```
2. Load schema and data:
   ```bash
   psql -h localhost -U postgres -d amman_market -f schema.sql
   psql -h localhost -U postgres -d amman_market -f seed_data.sql
   ```
3. Install dependencies: `pip install -r requirements.txt`

## Deliverables

1. **`kpi_framework.md`** — Define 5 KPIs (at least 2 time-based, 1 cohort-based)
2. **`analysis.py`** — Extract data, compute KPIs, run statistical tests, create visualizations
3. **`EXECUTIVE_SUMMARY.md`** — Top findings, supporting data, recommendations
4. **`output/`** — Chart PNG files (at least 5, one per KPI)
5. **`tests/test_analysis.py`** — Your own tests (3 required)

## Submit

1. Create branch `integration-4/kpi-dashboard`
2. Complete all deliverables
3. Push and open a PR to `main`
4. Paste your PR URL into TalentLMS → Module 4 → Integration 4

---

## License

This repository is provided for educational use only. See [LICENSE](LICENSE) for terms.

You may clone and modify this repository for personal learning and practice, and reference code you wrote here in your professional portfolio. Redistribution outside this course is not permitted.
