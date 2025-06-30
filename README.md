# Auditoria de Sites de Prefeituras Brasileiras com PageSpeed Insights

## Overview/Purpose

This project aims to automatically audit Brazilian city (prefeitura) websites using the Google PageSpeed Insights (PSI) API. The project has transitioned from an initial approach using a local Lighthouse CLI to massively leveraging the PSI API for more comprehensive data collection. Metrics for performance, accessibility, SEO, and best practices are gathered sequentially with a one-second pause between requests, and partial results are written to disk after each successful call.

This project was elaborated as part of a Master's dissertation research focusing on evaluating the transparency and accessibility of municipal websites.

## Master's Dissertation

This repository and its findings are a result of academic research developed during a Master's program. The related publications are:

```
@article{silveira2023using,
  title={USING AUTOMATED ACCESSIBILITY METERING TOOLS IN TRANSPARENCY RANKINGS IN BRAZIL.},
  author={Silveira Baldo, Franklin and Veludo Watanabe, Carolina Yukari and Ton Tiussi, Denise},
  journal={Direito da Cidade},
  volume={15},
  number={3},
  year={2023}
}

@article{baldo2019acessibilidade,
  title={Acessibilidade web para indicadores de transpar{\^e}ncia},
  author={Baldo, Franklin Silveira},
  year={2019}
}
```

## How it Works

The project uses a combination of a data file, a GitHub Action, and a Node.js script to collect and present data from the PageSpeed Insights API.

### Data Source

The primary list of websites to be audited is sourced from the `sites_das_prefeituras_brasileiras.csv` file located in the root of this repository. This CSV file should contain information such as the city name, state (UF), IBGE code, and the official URL of the city's website.

### GitHub Action Workflow

A GitHub Action, defined in `.github/workflows/psi.yml`, automates the data collection and archival process. This workflow:
- Runs on a schedule (currently configured for daily at 3 AM UTC).
- Can also be triggered manually via the GitHub Actions tab.

The main steps performed by the workflow are:
1.  **Checkout Repository:** Checks out the latest version of the repository.
2.  **Set up Node.js & Python:** Configures the environment with Node.js (currently v18) and Python (3.x).
3.  **Install Dependencies:** Installs Node.js packages (including `duckdb`) via `npm ci` and Python packages (`internetarchive`) via `pip`.
4.  **Run PSI Data Collection Script (`collect-psi.js`):** Executes the script to gather PSI metrics. Data is saved into a DuckDB database file at `data/psi_results.duckdb`.
5.  **Upload to Internet Archive:** The `data/psi_results.duckdb` file is uploaded to a specified Internet Archive item using the `upload_to_ia.py` script. This requires `IA_ACCESS_KEY` and `IA_SECRET_KEY` to be configured as GitHub secrets. The default Internet Archive item identifier is `psi_brazilian_city_audits` (this can be changed in the workflow file).
6.  **Error Handling and Reporting:**
    *   If `collect-psi.js` encounters errors (e.g., unable to fetch PSI data for a specific URL), these are logged to `psi_errors.log`.
    *   The workflow checks this log. If errors are present, it archives `psi_errors.log` to `data/psi_error_reports/psi_errors_<run_id>.log` and creates/updates `TODO.md` at the root of the repository with details and a link to the workflow run.
7.  **Commit State and Reports:** The workflow commits any changes to `data/psi_processing_state.json` (which tracks the processing status of URLs). If errors occurred, `TODO.md` and the archived error log in `data/psi_error_reports/` are also committed. These files are pushed to the main branch.

### Data Collection Script (`collect-psi.js`)

This Node.js script is the core of the data collection. It performs:
- Reads URLs from `sites_das_prefeituras_brasileiras.csv`.
- For each URL, fetches PSI metrics (performance, accessibility, best-practices, seo) for the mobile strategy.
- Implements retries with backoff for transient errors and respects PSI API rate limits.
- **Stores all collected data directly into a DuckDB database (`data/psi_results.duckdb`).** The table `psi_metrics` within this database holds the results.
- Maintains a `data/psi_processing_state.json` file to keep track of URLs that have been processed or attempted, ensuring that URLs are processed efficiently over time. This state file is committed to the repository.

Key metrics collected:
- Performance score
- Accessibility score
- SEO score
- Best Practices score
- Timestamp, URL, and IBGE code.

### Results Storage and Archival

-   **Primary Data Store:** Audit findings are stored in a DuckDB database file located at `data/psi_results.duckdb`. This file is NOT committed to the Git repository.
-   **Archival:** After each successful run of the data collection script, the `data/psi_results.duckdb` file is uploaded to the Internet Archive. Each upload is timestamped to maintain a history of results. The default Internet Archive item for these uploads is `psi_brazilian_city_audits`.
-   **Processing State:** The `data/psi_processing_state.json` file, which helps manage the queue of URLs to audit, IS committed to the Git repository.
-   **Error Logs:** Detailed error logs for problematic URLs from a specific run are archived in `data/psi_error_reports/` and committed to the repository if errors occur. `TODO.md` is also updated.

The schema for the `psi_metrics` table in DuckDB is:
- `timestamp` (TIMESTAMPTZ)
- `url` (VARCHAR)
- `ibge_code` (VARCHAR)
- `performance` (FLOAT)
- `accessibility` (FLOAT)
- `seo` (FLOAT)
- `bestPractices` (FLOAT)
(Primary Key: `url`, `timestamp`)

## Viewing the Results

Previously, `index.html` loaded data from a JSON file. **This mechanism is currently not functional** as the data is now stored in a DuckDB database and archived to the Internet Archive.

To view and analyze the results:
1.  **Download from Internet Archive:** Access the Internet Archive item (default: [https://archive.org/details/psi_brazilian_city_audits](https://archive.org/details/psi_brazilian_city_audits) - *Note: This link is a placeholder until the item is actually created*) and download the desired `_psi_results_<timestamp>.duckdb` file.
2.  **Use a DuckDB client:** Connect to the downloaded `.duckdb` file using any DuckDB-compatible SQL client (e.g., DuckDB CLI, DBeaver, Python with the DuckDB library) to query and analyze the data.

**The GitHub Pages site currently hosted at [https://franklinbaldo.github.io/sites_prefeituras/](https://franklinbaldo.github.io/sites_prefeituras/) will no longer display updated data unless `index.html` is modified to source data from a new process (e.g., by periodically querying DuckDB and generating a static JSON, or by pointing to an external service that can serve the data from the archived DuckDB files).**

To enable GitHub Pages for this repository (for static content like the README):

1.  Go to your repository's **Settings** tab on GitHub.
2.  In the left sidebar, navigate to the **Pages** section.
3.  Under the "Build and deployment" heading:
    *   For **Source**, select **Deploy from a branch**.
    *   Under **Branch**, select your main branch (e.g., `main`, `master`) and choose the `/(root)` folder.
4.  Click **Save**.

It might take a few minutes for the site to build and become live.

## Current Limitations & Future Work

-   **Error Handling & Reporting:** The error handling mechanism (logging to `psi_errors.log`, archiving, and creating `TODO.md`) is in place. Further enhancements to in-script retries or error categorization could be made.
-   **Data Visualization:** The `index.html` page is no longer functional for viewing current data. Future work could involve:
    *   Creating a new process to periodically extract data from the archived DuckDB files (or a central DuckDB instance) and generate a static JSON/CSV for `index.html` or other visualization tools.
    *   Developing a dynamic web application that can query and display data from the DuckDB files or a data warehouse populated from them.
    *   Leveraging dbt (as per the user's initial interest) to transform and model data from DuckDB for easier analysis and reporting.
-   **Historical Data:** Historical data is now preserved through timestamped DuckDB file uploads to the Internet Archive. Analyzing trends across these historical snapshots would require downloading multiple database files and comparing them.
-   **Desktop vs. Mobile:** The script currently focuses on mobile strategy. Audits for desktop could also be incorporated into the DuckDB schema and collection script.
-   **Internet Archive Item Management:** The IA item identifier is currently hardcoded (though changeable in the workflow). More sophisticated management or parameterization might be useful. Users must ensure they have the necessary IA credentials (`IA_ACCESS_KEY`, `IA_SECRET_KEY`) configured as GitHub secrets.

## Contributing

Contributions are welcome! Here are a few ways you can help:

-   **Updating the Website List:** If you find inaccuracies in `sites_das_prefeituras_brasileiras.csv` or want to add new official municipal websites, please feel free to submit a pull request with your changes.
-   **Improving Scripts & Workflow:** Enhancements to the `collect-psi.js` script, the GitHub Actions workflow, or the `index.html` presentation are welcome.
-   **Bug Fixes & Feature Requests:** If you encounter any issues or have ideas for new features, please open an issue on GitHub.

When contributing, please ensure your changes are well-tested and follow the general coding style of the project.
