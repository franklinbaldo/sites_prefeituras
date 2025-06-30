P1 — Data quality & modelling (dbt-duckdb)
Boot a dbt project pointing at data/psi_results.duckdb.
Follow DuckDB’s official guide → https://duckdb.org/2025/04/04/dbt-duckdb.html

Write basic tests (dbt test)

not_null on url, timestamp

unique on (url, timestamp)

Derive modelling layer

daily_site_scores (latest record per url per calendar-day)

rolling_28d_avg (metric smoothing for dashboards)

Document models. (dbt docs generate → publish in GitHub Pages)

P2 — Observability & backfill
Grafana / DuckDB-HTTP endpoint (read-only)
Visualise rolling_28d_avg to spot regressions.

Backfill task
Catch gaps when PSI was down; loop over psi_processing_state.json for URLs that missed >48 h.

Legacy data migration
One-shot script to load historical JSON/CSV archives into DuckDB so trend lines start at day 0.

P3 — Developer-experience polish
Pre-commit hook: lint collect-psi.js + upload_to_ia.py with Ruff/ESLint.

Automated IA inventory: nightly job lists the item and checks the latest .duckdb matches today’s timestamp.

README badges: build status, last IA snapshot date, dbt docs link.

Parking-lot ideas (defer)
Split heavy tables into quarterly .duckdb shards to keep CI checkout times low.

Replace the Node PSI fetcher with @lumos/psi-lite once stable → 4× faster.

Push an anonymised copy to Zenodo for DOI-ready citations.

How this file is generated
col­lect-psi.js sets HAS_PSI_ERRORS=true when it writes any log to data/psi_error_reports/*.
The GitHub Action then replaces the contents of TODO.md with this template,
adds a short preamble noting the specific run ID + log path, and commits only if errors exist.

Resolve items top-down; never stash data in the repo again. Everything lives in DuckDB and the Internet Archive
