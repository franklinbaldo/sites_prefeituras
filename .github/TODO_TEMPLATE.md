# Project TODO List

This file tracks tasks for improving the Brazilian City Hall Website Audit project.
Priorities: P0 (Critical), P1 (High), P2 (Medium), P3 (Low).

## How this file is used

The GitHub Action workflow (`psi.yml`) may prepend error reports to this file if issues are found during data collection. The tasks below are general project improvements.

---

## P0 - Critical Tasks

*   **DOC-1 (was FEW-6):** Ensure `index.html` and its components are fully WCAG 2.1 AA compliant for accessibility.
*   **DOC-2 (was DOC-1):** Update `README.md` to accurately reflect the current data flow (especially the role of `psi-latest-viewable-results.json` and `index.html`), and how `TODO.md` is generated.

## P1 - High Priority Tasks

**Data Quality, Modelling & Migration (DQM)**
*   **DQM-1 (Template P1):** Boot a dbt project pointing at `data/psi_results.duckdb`.
    *   Follow DuckDB’s official guide: [https://duckdb.org/docs/guides/dbt/getting_started.html](https://duckdb.org/docs/guides/dbt/getting_started.html) (Note: Link updated to a likely more stable one, original was futuristic).
*   **DQM-2 (Template P1):** Write basic dbt tests: `not_null` on url, timestamp; `unique` on (url, timestamp, strategy).
*   **DQM-3 (Template P1):** Derive dbt modelling layer:
    *   `daily_site_scores` (latest record per url per calendar-day for each strategy).
    *   `rolling_28d_avg` (metric smoothing for dashboards).
*   **DQM-4 (Template P2):** Legacy data migration: Create a one-shot script to load historical data from `data/psi-results.csv` and `data/psi-results.json` into the DuckDB `psi_metrics` table to enable long-term trend analysis.
*   **DM-1 (was DM-1, related to DQM-2):** Implement data validation checks (e.g., using `dbt tests` or custom scripts) on the DuckDB data to ensure integrity (e.g., scores within 0-1 range, valid URLs, expected categories).

**Code Quality & Maintainability (QCM)**
*   **QCM-1:** Refactor `collect-psi.js` into smaller, more focused modules (e.g., `csvReader.js`, `psiFetcher.js`, `duckdbWriter.js`, `stateManager.js`).
*   **QCM-2:** Implement ESLint for all JavaScript files (`collect-psi.js`, `analyze_psi_data.js`, `js/*.js`) with a standard style guide and fix all linting errors.
*   **QCM-3:** Implement a Python linter (e.g., Ruff or Flake8+Black) for `generate_viewable_json.py` and `upload_to_ia.py` and fix all linting errors.
*   **QCM-4 (was QCM-6):** Review and update all Node.js dependencies in `package.json` to their latest stable versions. Address any breaking changes.

**Collector Features & Error Handling (FEC/EHR)**
*   **FEC-1 (was FEC-4):** Add functionality to `collect-psi.js` to fetch and store specific Lighthouse audit details (e.g., failing accessibility checks, specific metric values like LCP, CLS, TBT) beyond just the top-level scores. This would involve schema changes to DuckDB.
*   **EHR-1:** In `collect-psi.js`, implement more specific error categorization for PSI API failures (e.g., distinguish between 404s, API errors, Lighthouse errors, timeouts) and log them structuredly.
*   **FEC-2 (was FEC-2):** Add an option to `collect-psi.js` to re-run PSI for URLs that failed in the previous run, perhaps based on a structured error log or a "needs_retry" state in `psi_processing_state.json`.

**Web Interface (FEW)**
*   **FEW-1:** Improve overall UI/UX of `index.html`: better visual hierarchy, more intuitive controls, and clearer presentation of data.
*   **FEW-2:** Add advanced filtering to the web table (e.g., filter by score ranges for different categories, by state/region if that data is available).
*   **FEW-3 (was FEW-4):** Add a feature to `index.html` to display historical trend charts for a selected URL (requires DQM-4 and DQM-3).
*   **FEW-4 (was FEW-5):** Add a comparison feature to `index.html` to select 2+ sites and view their scores side-by-side.
*   **FEW-5 (was FEW-7):** Improve mobile responsiveness of `index.html` and ensure charts are legible on small screens.

**Testing & CI/CD (TST/CICD)**
*   **TST-1:** Increase test coverage for `collect-psi.js`, especially for error handling paths, retry logic, and state management.
*   **TST-2:** Add unit tests for `generate_viewable_json.py`, mocking DuckDB interactions.
*   **CICD-1 (Template P3 & QCM-4/5):** Implement pre-commit hooks for linting (ESLint, Ruff/Flake8) and formatting (Prettier, Black). Also add these as checks in the CI pipeline.
*   **CICD-2 (was CICD-3):** Integrate a dependency vulnerability scanner (e.g., `npm audit`, Snyk, Dependabot security updates) into the CI workflow.
*   **SEC-1 (was SEC-2):** Verify that API keys or sensitive configurations are not accidentally logged in debug outputs.

## P2 - Medium Priority Tasks

**Data Quality, Modelling & Observability (DQM/OBS)**
*   **DQM-5 (Template P1):** Document dbt models and generate documentation (e.g., `dbt docs generate`), publish to GitHub Pages.
*   **OBS-1 (Template P2):** Explore setting up Grafana with a DuckDB HTTP endpoint (read-only) to visualize key metrics like `rolling_28d_avg` and spot regressions.
*   **OBS-2 (Template P2):** Backfill task: Enhance `collect-psi.js` or create a separate script to identify and re-process URLs from `psi_processing_state.json` that have missed data collection for a significant period (e.g., >48 hours).

**Code Quality & Maintainability (QCM)**
*   **QCM-5 (was QCM-2):** Refactor `analyze_psi_data.js` if it grows complex, separating argument parsing, DuckDB querying, and output formatting.
*   **QCM-6 (was QCM-3):** Refactor `generate_viewable_json.py` to improve clarity, add more transformation options (e.g., include/exclude specific Lighthouse audits if FEC-1 is done).
*   **QCM-7 (was QCM-7):** Review and update Python dependencies in the GitHub Actions workflow.
*   **QCM-8:** Add comprehensive JSDoc comments to `collect-psi.js`, `analyze_psi_data.js` and frontend `js/*.js` files.
*   **QCM-9:** Add Python type hints and docstrings to `generate_viewable_json.py` and `upload_to_ia.py`.
*   **QCM-10:** Evaluate and remove any unused code or files (e.g., `babel.config.cjs`, `script.js`, `style.css`).
*   **QCM-11:** Standardize logging across all scripts (Node.js and Python) for format and levels.

**Collector Features & Error Handling (FEC/EHR)**
*   **FEC-3 (was FEC-1):** Make PSI API categories (`performance`, `accessibility`, etc.) more dynamically configurable in `psi-collector-config.json` for `collect-psi.js`.
*   **FEC-4 (was FEC-3):** Implement more sophisticated PSI API quota management in `collect-psi.js`.
*   **FEC-5 (was FEC-5):** Allow `collect-psi.js` to accept a list of specific IBGE codes or URLs via command line for targeted runs.
*   **EHR-2 (was EHR-2):** Ensure the enhanced `TODO.md` generation in the workflow distinctly captures different error types from EHR-1.
*   **EHR-3:** Implement a mechanism in `collect-psi.js` to detect and potentially blacklist consistently failing URLs after N retries over M runs.

**Web Interface (FEW)**
*   **FEW-6 (was FEW-3):** Implement multi-column sorting in the web table on `index.html`.
*   **FEW-7 (was FEW-8):** Add a "Last Data Updated" timestamp to `index.html` (from `psi-latest-viewable-results.json` generation time).
*   **FEW-8 (was FEW-9):** Allow users to select PSI strategy (mobile/desktop) to view in `index.html` table/charts.
*   **FEW-9:** Add pagination to the results table in `index.html` for better performance with many sites.

**Analysis Features (FEA)**
*   **FEA-1:** Enhance `analyze_psi_data.js` with more predefined queries (e.g., sites with most improved/declined scores, regional averages).
*   **FEA-2:** Develop a script for basic anomaly detection in PSI scores (e.g., identify sites with sudden significant drops).
*   **FEA-3:** Add capability to `analyze_psi_data.js` to output results in CSV or JSON to a file.

**Testing & CI/CD (TST/CICD)**
*   **TST-3:** Add unit tests for `analyze_psi_data.js`.
*   **TST-4:** Add basic E2E tests for `index.html` (e.g., using Playwright/Puppeteer) to verify table loading, filtering, chart generation.
*   **TST-5:** Ensure tests in `collect-psi.test.js` cover both mobile and desktop strategy collection logic and different error conditions.
*   **CICD-2 (was CICD-2):** Automate deployment of `index.html` and related assets to GitHub Pages on merge to main.
*   **CICD-3 (was CICD-4):** Add a GitHub Action step to validate the format of `sites_das_prefeituras_brasileiras.csv`.
*   **OBS-3 (Template P3):** Automated IA inventory: Nightly job to list IA item contents and check if the latest `.duckdb` file matches today’s timestamp.

**Documentation (DOC)**
*   **DOC-3 (was DOC-2):** Expand `README.md` with a "Project Architecture" section.
*   **DOC-4 (was DOC-3):** Create/Expand `CONTRIBUTING.md` with guidelines for code style, testing, PRs.
*   **DOC-5 (was DOC-4):** Document the schema of `psi-latest-viewable-results.json` and the main DuckDB table in `README.md`.
*   **DOC-6 (was DOC-5):** Add detailed inline comments to complex sections of all scripts.
*   **DOC-7 (Template P3):** Add README badges: build status, last IA snapshot date, dbt docs link (once DQM-5 is done).

**Security (SEC)**
*   **SEC-2 (was SEC-1):** Add basic security headers (CSP, X-Content-Type-Options, etc.) for the GitHub Pages site.

## P3 - Low Priority Tasks / Future Ideas

*   **DM-2 (was DM-2):** Develop a strategy for managing local `psi_results.duckdb` file size in the GitHub Action runner if it grows too large (e.g., more frequent IA uploads if possible, or investigate partial uploads/diffs if IA supports).
*   **Parking-Lot (Template):** Split heavy tables into quarterly .duckdb shards to keep CI checkout times low (relevant if local DuckDB file committed, less so if only for IA upload).
*   **Parking-Lot (Template):** Replace the Node PSI fetcher with `@lumos/psi-lite` once stable for potential speed improvements.
*   **Parking-Lot (Template):** Push an anonymised copy of the data to Zenodo for DOI-ready citations.
*   **FEA-4:** Explore sentiment analysis on website text if Lighthouse provides it, or integrate another tool.
*   **FEC-6:** Add option to run specific Lighthouse accessibility audits (e.g., color contrast only) if PSI API/underlying tools allow.
*   **QCM-12:** Investigate using TypeScript for `collect-psi.js` or `analyze_psi_data.js` for improved type safety.

---
Resolve items top-down based on priority. Remember the project's goal of maintaining data in DuckDB and the Internet Archive, not in the repo directly for large datasets.
The original note about how TODO.md is generated by the GitHub action has been preserved below for reference, but a summary is now at the top of this file.

---
Original note from template:
How this file is generated
col­lect-psi.js sets HAS_PSI_ERRORS=true when it writes any log to data/psi_error_reports/*.
The GitHub Action then replaces the contents of TODO.md with this template,
adds a short preamble noting the specific run ID + log path, and commits only if errors exist.

Resolve items top-down; never stash data in the repo again. Everything lives in DuckDB and the Internet Archive
