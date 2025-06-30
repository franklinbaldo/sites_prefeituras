# Completed Tasks

This file tracks tasks that have been completed.

*As of [current date], no major tasks from the `.github/TODO_TEMPLATE.md` have been fully completed and moved here. This file is ready for future updates.*

---

## Recently Completed (General Project Progress - Not from Template)

While not explicitly listed as granular tasks in the `TODO_TEMPLATE.md` before its current version, the following significant project improvements have been achieved:

*   **Data Storage Modernization:** Transitioned from CSV/JSON files to DuckDB for primary data storage of PSI results. (Related to P1 Data Quality & Modelling)
*   **Comprehensive Data Collection:** The collection script (`collect-psi.js`) now gathers data for both mobile and desktop strategies.
*   **Automated Error Reporting:** Implemented a system where PSI collection errors are logged, archived, and reported in `TODO.md` via GitHub Actions. (Related to P2 Observability)
*   **Data Archival:** PSI results (DuckDB database) are automatically uploaded to the Internet Archive.
*   **Web Visualization of Latest Data:** The `index.html` page, through `generate_viewable_json.py` and associated JavaScript, displays the latest PSI results for each site from the DuckDB database.

*(Note: Replace [current date] with the actual date upon execution if possible, otherwise, I'll leave it as a placeholder.)*
