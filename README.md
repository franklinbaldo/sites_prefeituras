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

The schema for the `psi_metrics` table in DuckDB (`data/psi_results.duckdb`) is:
- `timestamp` (TIMESTAMPTZ): Timestamp of the audit.
- `url` (VARCHAR): Audited URL.
- `ibge_code` (VARCHAR): IBGE code for the city.
- `strategy` (VARCHAR): The PSI strategy used ('mobile' or 'desktop').
- `performance` (FLOAT): Performance score (0-1).
- `accessibility` (FLOAT): Accessibility score (0-1).
- `seo` (FLOAT): SEO score (0-1).
- `bestPractices` (FLOAT): Best Practices score (0-1).
(Primary Key: `url`, `timestamp`, `strategy`)

## Accessing and Analyzing the Data

The primary collected data is stored in DuckDB database files, which are archived to the Internet Archive. The `index.html` page in this repository also presents a view of the latest results for each site (from `data/psi-latest-viewable-results.json`, updated by the GitHub Action).

For in-depth analysis and access to historical data, you can use the archived DuckDB files or the local `data/psi_results.duckdb` file if you run the collection script locally.

### 1. Downloading Data from the Internet Archive

-   **Access the Item:** Go to the Internet Archive item where the data is stored. The default item identifier used by the workflow is `psi_brazilian_city_audits`. The direct link would be `https://archive.org/details/psi_brazilian_city_audits` (this may need to be created by the project owner if it's the first time).
-   **Find Files:** Within the item, you will find multiple files named like `psi_results_<timestamp>.duckdb`. Each file is a snapshot of the database at the time of collection.
-   **Download:** Download the specific database file(s) you are interested in.

### 2. Using a DuckDB Client

Once you have a `.duckdb` file (either downloaded from the Internet Archive or the local `data/psi_results.duckdb`):

-   **DuckDB CLI:**
    -   Install the DuckDB CLI (see [DuckDB documentation](https://duckdb.org/docs/api/cli.html)).
    -   Open the database file: `duckdb path/to/your/psi_results_xxxx.duckdb`
    -   You can then run SQL queries directly. For example: `.tables` to list tables, `SUMMARIZE psi_metrics;` for a quick overview, or any SQL query.
-   **Python with DuckDB Library:**
    ```python
    import duckdb
    # Connect to an in-memory database
    # con = duckdb.connect(database=':memory:', read_only=False)
    # Connect to a file
    con = duckdb.connect(database='path/to/your/psi_results_xxxx.duckdb', read_only=True)
    results = con.execute("SELECT * FROM psi_metrics WHERE performance < 0.5 AND strategy = 'mobile' ORDER BY timestamp DESC LIMIT 10;").fetchdf()
    print(results)
    con.close()
    ```
-   **GUI Tools:** Tools like DBeaver, DataGrip, or others that support JDBC can connect to DuckDB. You'll typically need the DuckDB JDBC driver. Refer to the specific tool's documentation and DuckDB's JDBC driver page.

### 3. Example SQL Queries

Here are some example queries you can run against the `psi_metrics` table:

-   **Get the latest scores for all URLs for a specific strategy:**
    ```sql
    SELECT *
    FROM psi_metrics
    WHERE strategy = 'mobile' -- or 'desktop'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY url ORDER BY timestamp DESC) = 1;
    ```
-   **Average scores per strategy:**
    ```sql
    SELECT
        strategy,
        ROUND(AVG(performance), 3) as avg_performance,
        ROUND(AVG(accessibility), 3) as avg_accessibility,
        ROUND(AVG(seo), 3) as avg_seo,
        ROUND(AVG(bestPractices), 3) as avg_best_practices,
        COUNT(*) as record_count
    FROM psi_metrics
    GROUP BY strategy;
    ```
-   **List 10 worst performing sites (mobile) based on latest audit:**
    ```sql
    WITH LatestMobileScores AS (
        SELECT *
        FROM psi_metrics
        WHERE strategy = 'mobile'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY url ORDER BY timestamp DESC) = 1
    )
    SELECT url, performance, timestamp
    FROM LatestMobileScores
    WHERE performance IS NOT NULL
    ORDER BY performance ASC
    LIMIT 10;
    ```
-   **Track performance of a specific URL over time:**
    ```sql
    SELECT timestamp, strategy, performance, accessibility
    FROM psi_metrics
    WHERE url = 'http://example.com/prefeitura_specific_url'
    ORDER BY timestamp DESC;
    ```

### 4. Using the Local Analysis Script (`analyze_psi_data.js`)

This repository includes a command-line tool to quickly query the data.

-   **Prerequisites:** Node.js and npm installed. Run `npm install` in the repository root if you haven't already (to install `duckdb` Node.js package).
-   **Usage:**
    ```bash
    node analyze_psi_data.js [options]
    ```
-   **Common Operations:**
    -   Show summary: `node analyze_psi_data.js --summary`
    -   Get average scores for mobile: `node analyze_psi_data.js --avg-scores mobile`
    -   List 10 worst accessibility scores for desktop: `node analyze_psi_data.js --list-worst accessibility 10 desktop`
    -   Find a specific URL: `node analyze_psi_data.js --find-url "example.gov.br"`
    -   Run a custom query: `node analyze_psi_data.js --query "SELECT strategy, COUNT(*) FROM psi_metrics GROUP BY strategy;"`
-   For all options, run: `node analyze_psi_data.js --help`
-   You can specify a different database file: `node analyze_psi_data.js --db path/to/another_results.duckdb --summary`

**The GitHub Pages site currently hosted at [https://franklinbaldo.github.io/sites_prefeituras/](https://franklinbaldo.github.io/sites_prefeituras/) is now updated by the GitHub Action workflow to display the latest results from `data/psi-latest-viewable-results.json`.**

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
-   **Desktop vs. Mobile:** The script now collects data for both mobile and desktop strategies.
-   **Internet Archive Item Management:** The IA item identifier is currently hardcoded (though changeable in the workflow). More sophisticated management or parameterization might be useful. Users must ensure they have the necessary IA credentials (`IA_ACCESS_KEY`, `IA_SECRET_KEY`) configured as GitHub secrets.
-   **Configuration:** The `collect-psi.js` script uses `psi-collector-config.json` for several operational parameters. See this file for details on configurable options like API categories, concurrency, retry settings, and file paths. Environment variables can override some of these settings (e.g., `PSI_KEY`, `PSI_CONCURRENCY`).

## Contributing

Contributions are welcome! Here are a few ways you can help:

-   **Updating the Website List:** If you find inaccuracies in `sites_das_prefeituras_brasileiras.csv` or want to add new official municipal websites, please feel free to submit a pull request with your changes.
-   **Improving Scripts & Workflow:** Enhancements to the `collect-psi.js` script, the GitHub Actions workflow, or the `index.html` presentation are welcome.
-   **Bug Fixes & Feature Requests:** If you encounter any issues or have ideas for new features, please open an issue on GitHub.

When contributing, please ensure your changes are well-tested and follow the general coding style of the project.
