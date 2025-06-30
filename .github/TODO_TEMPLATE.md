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

## Granular Task Backlog

This section contains a more detailed list of potential tasks and improvements identified during a repository review. These can be considered alongside or as sub-tasks for the P1-P3 items above.

### I. Core Data Collection (`collect-psi.js`)
1.  **Refine `loadAndPrioritizeUrls` Error Handling**: Make error reporting more granular if CSV parsing fails (e.g., specific row/column).
2.  **Advanced URL Prioritization**: Implement more sophisticated prioritization (e.g., based on error history, frequency of checks for problematic sites).
3.  **Configurable PSI API Version**: Allow specifying the PSI API version (e.g., v5) in `psi-collector-config.json`.
4.  **Dynamic Category Selection**: Allow PSI categories to be toggled on/off more easily, perhaps via command-line flags to `collect-psi.js` overriding the config for one-off runs.
5.  **Lighthouse Audit-Level Detail**: Investigate fetching and storing specific audit details (e.g., "unused-javascript", "image-alt") instead of just category scores. This would significantly increase data size and complexity.
6.  **Store Full Lighthouse JSON**: Option to store the full Lighthouse JSON report (perhaps selectively for failed audits or specific URLs) for deeper analysis.
7.  **Customizable Request Headers**: Allow specifying custom HTTP headers for PSI requests if needed for certain sites (e.g., specific User-Agent). (PSI API might not support this directly, needs check).
8.  **Batching API Requests**: Explore if PSI API supports batch requests for multiple URLs to improve efficiency (unlikely for `runPagespeed`, but worth a check).
9.  **More Robust `process.exit` Handling**: Ensure `process.exit` calls in `collect-psi.js` are handled gracefully, perhaps allowing a cleanup function to always run.
10. **Internationalization (i18n) for Logs**: If logs are intended for a wider audience, consider i18n for log messages (low priority).
11. **Plugin System for PSI Metrics**: Design a way to add new metric extractors or data processors as plugins (advanced).
12. **Alternative Data Sources**: Add capability to read URLs from sources other than CSV (e.g., a text file, a database table).
13. **Processing State Resilience**: Make `data/psi_processing_state.json` more resilient to corruption (e.g., atomic writes, backups).

### II. Error Handling & Logging
14. **Structured Logging**: Implement structured logging (e.g., JSON format for logs) for easier machine parsing and analysis of `psi_errors.log` and activity logs.
15. **Dedicated Activity Log**: Fully implement and utilize an activity log file (from `SCRIPT_CONFIG.activity_log_file`) for non-error informational and warning messages from `collect-psi.js`.
16. **Error Dashboard Integration**: Send error metrics to a monitoring/dashboarding service (e.g., Sentry, Grafana Loki).
17. **Error Alerting**: Implement alerts (e.g., email, Slack) via GitHub Actions if a certain threshold of errors is reached.
18. **Error Analysis in `analyze_psi_data.js`**: Add a feature to `analyze_psi_data.js` to parse and summarize archived `data/psi_error_reports/*.log` files.

### III. Database (`DuckDB`) & Data Management
19. **DuckDB Schema Migrations**: Implement a basic schema migration mechanism if further changes to `psi_metrics` table are expected.
20. **Data Pruning Strategy for Local DB**: Option in `collect-psi.js` or a separate script to prune old data from the local `data/psi_results.duckdb` (e.g., keep last N runs or data older than X days).
21. **Export to Other Formats from `analyze_psi_data.js`**: Add functionality to `analyze_psi_data.js` to export query results to CSV or other formats.
22. **DuckDB Version Pinning**: Pin the DuckDB version in `package.json` and workflow more strictly if schema stability becomes critical between minor versions.
23. **Data Validation Layer**: Add a validation step after fetching PSI data before inserting into DuckDB to ensure data integrity for scores (e.g., range 0-1).

### IV. GitHub Actions Workflow (`.github/workflows/psi.yml`)
24. **Workflow Optimization**: Review workflow for efficiency (e.g., caching strategies for `npm ci` and `pip install` if not fully optimal).
25. **Matrix Builds for Strategies**: Consider if running mobile and desktop strategies in parallel matrix jobs within the workflow is feasible/beneficial for speed.
26. **More Sophisticated IA Upload Options**: Add options to `upload_to_ia.py` (e.g., metadata customization via args, different IA item per strategy if desired).
27. **Workflow Failure Notifications**: Ensure workflow failure notifications are set up effectively (e.g., on error, on failure).
28. **Timeout Management Review**: Fine-tune `timeout-minutes` for the PSI collection step based on typical runtimes with dual strategies.
29. **Conditional Execution of Steps Review**: Review `if: success()` conditions, ensure they are optimal (e.g., should JSON generation run if IA upload fails but local DB was created?).
30. **Python Dependency Management for Scripts**: Introduce `requirements.txt` for Python scripts (`upload_to_ia.py`, `generate_viewable_json.py`) and use `pip install -r requirements.txt` in the workflow.

### V. Frontend & Visualization (`index.html`, `analyze_psi_data.js`)
31. **Strategy Selector for Charts/Table**: In `index.html`, add UI elements to select which strategy's data (mobile, desktop, or combined) is displayed in charts and the table. This would require `generate_viewable_json.py` to provide data accordingly.
32. **Historical Trend Charts**: Add charts to `index.html` showing how a selected metric for a specific URL (or average) has changed over time (requires `generate_viewable_json.py` to provide historical data or a different data source for the page).
33. **Advanced Filtering/Sorting for Table in `index.html`**: Add more advanced filtering (e.g., by score ranges) and multi-column sorting to the table.
34. **Accessibility Audit of `index.html`**: Run an accessibility audit on the `index.html` page itself and fix any issues.
35. **Performance Optimization of `index.html`**: Optimize the frontend for speed (e.g., efficient DOM manipulation, code splitting if it grows).
36. **UI/UX Improvements for `analyze_psi_data.js`**: Improve output formatting, add color-coding, or use a CLI table formatter for `analyze_psi_data.js`.
37. **Interactive Queries in `analyze_psi_data.js`**: Add a mode for `analyze_psi_data.js` to enter an interactive SQL query loop.

### VI. Testing
38. **Unit Tests for `collect-psi.js`**: Write unit tests for `loadAndPrioritizeUrls`, `originalFetchPSI` (with mocked fetch), and DuckDB interaction functions.
39. **Unit Tests for Python Scripts**: Write unit tests for `generate_viewable_json.py` and `upload_to_ia.py` (mocking IA and DB interactions).
40. **Integration Tests**: Develop integration tests that run `collect-psi.js` with a test CSV and a local mock PSI API, verifying data is written to a test DuckDB correctly.
41. **E2E Tests for Workflow**: Consider high-level E2E tests for the GitHub Action workflow (e.g., a test that runs the workflow on a small dataset and verifies outputs).
42. **Test Coverage Reporting**: Integrate test coverage reporting (e.g., using Jest's coverage features).

### VII. Documentation & General Maintenance
43. **Comprehensive `CONTRIBUTING.md`**: Create a `CONTRIBUTING.md` file with guidelines for developers.
44. **Code Style Enforcement**: Introduce and configure a linter (e.g., ESLint for JS, Flake8/Black for Python) and code formatter (Prettier).
45. **Update `AGENTS.md`**: Keep `AGENTS.md` updated as new features are added or refactoring occurs. (Self-referential task, good to keep in mind).
46. **Detailed Comments for Complex Logic**: Review and add more detailed comments for any particularly complex algorithms or non-obvious logic in all scripts.
47. **Architectural Diagram**: Create a simple architectural diagram showing data flow and component interactions, and add to README or a `/docs` folder.
48. **Security Review of Dependencies**: Regularly perform security audits of dependencies (`npm audit`, `pip-audit`) and address vulnerabilities.
49. **License Review**: Ensure all dependencies have compatible licenses if this project were to be distributed or used in specific ways. Add a `LICENSE` file for the project itself.
50. **User Documentation for `index.html`**: Add a small section on `index.html` itself (or linked from it) explaining how to interpret the charts and table.
51. **Refine `generate_viewable_json.py` for Strategy**: Decide how `generate_viewable_json.py` should handle multiple strategies (mobile/desktop) for the same URL when picking the "latest". (e.g., provide both, provide a default, provide an average). This affects frontend visualization.
52. **Add `psi-collector-config.json` to `.gitignore`?**: Decide if `psi-collector-config.json` should be in `.gitignore` with a committed `psi-collector-config.example.json` instead, if API keys or other sensitive info were ever to be part of it (currently API key is via env var name in config). For now, it's fine as is.
