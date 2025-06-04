# Auditoria de Sites de Prefeituras Brasileiras com PageSpeed Insights

## Overview/Purpose

This project aims to automatically audit Brazilian city (prefeitura) websites using the Google PageSpeed Insights (PSI) API. The project has transitioned from an initial approach using a local Lighthouse CLI to massively leveraging the PSI API for more comprehensive data collection, including metrics for performance, accessibility, SEO, and best practices, with controlled parallelism (configurable). The results are processed and can be used to assess the current state of these public portals.

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

A GitHub Action, defined in `.github/workflows/psi.yml`, automates the data collection process. This workflow:
- Runs on a schedule (currently configured for daily at 3 AM UTC).
- Can also be triggered manually via the GitHub Actions tab.

The main steps performed by the workflow are:
1.  **Checkout Repository:** Checks out the latest version of the repository.
2.  **Set up Node.js:** Configures the environment with Node.js (currently v18).
3.  **Install Dependencies:** Installs the necessary Node.js packages defined in `package.json` using `npm ci`.
4.  **Run PSI Data Collection Script:** Executes the `collect-psi.js` script.
5.  **Error Handling and Reporting:**
    *   If the `collect-psi.js` script encounters errors during its run (e.g., unable to fetch PSI data for a specific URL, network issues, 404 errors from target sites), these errors are logged into a file named `psi_errors.log`.
    *   If `psi_errors.log` is generated and contains errors, the workflow will:
        *   Create a `TODO.md` file at the root of the repository. This file includes the contents of `psi_errors.log`, a timestamp of when the errors were logged, and a direct link to the specific GitHub Actions workflow run that detected them.
        *   Commit this `TODO.md` file to a dedicated branch named `psi-error-reports`.
    *   This error reporting mechanism allows for tracking and manual review of URLs or issues that consistently fail. It helps in identifying outdated URLs or other problems that need investigation, without halting the entire data collection process.
6.  **Commit Results:** Successfully collected PSI data points are compiled into `data/psi-results.json` and a historical `data/psi-results.csv`. Both files are automatically committed back to the main branch, ensuring that results are version-controlled and reflect the latest successful audits, even if some URLs encountered errors.

### Data Collection Script (`collect-psi.js`)

This Node.js script is the core of the data collection process. It performs the following actions:
- Reads the list of municipalities and their URLs from `sites_das_prefeituras_brasileiras.csv`.
- For each URL, it makes a request to the Google PageSpeed Insights API to fetch various web performance and quality metrics.
 - It manages the API requests with controlled parallelism. The concurrency defaults to 4 simultaneous requests but can be adjusted via the `PSI_CONCURRENCY` environment variable or a `--concurrency=<n>` CLI flag. The production GitHub Actions workflow sets `PSI_CONCURRENCY=100` to process many audits in parallel.
- The script collects the following key metrics for the mobile strategy:
    - Performance score
    - Accessibility score
    - SEO score
    - Best Practices score
 - The results, along with the URL, IBGE code and a timestamp, are compiled into a JSON array (`data/psi-results.json`) and also appended to `data/psi-results.csv` for historical tracking.

### Results Storage

The audit findings are stored in `data/psi-results.json` and mirrored in `data/psi-results.csv`. Each entry represents the audit result for a specific municipality and includes:
- `url`: The audited URL.
- `performance`: The PSI Performance score (0-1).
- `accessibility`: The PSI Accessibility score (0-1).
- `seo`: The PSI SEO score (0-1).
- `bestPractices`: The PSI Best Practices score (0-1).
- `timestamp`: The date and time when the audit was performed.

## Viewing the Results

The collected data is stored in `data/psi-results.json`. The `index.html` file at the root of this repository loads this data and presents it in a table, allowing for exploration of the findings.

**The live site can be accessed at: [https://franklinbaldo.github.io/sites_prefeituras/](https://franklinbaldo.github.io/sites_prefeituras/)**

To enable GitHub Pages for this repository if it's not already active, or if you've forked this repository:

1.  Go to your repository's **Settings** tab on GitHub.
2.  In the left sidebar, navigate to the **Pages** section.
3.  Under the "Build and deployment" heading:
    *   For **Source**, select **Deploy from a branch**.
    *   Under **Branch**, select your main branch (e.g., `main`, `master`) and choose the `/(root)` folder.
4.  Click **Save**.

It might take a few minutes for the site to build and become live.

## Current Limitations & Future Work

-   **Error Handling & Reporting:** The script logs errors encountered during URL processing to `psi_errors.log`. The GitHub workflow then processes this log to create a `TODO.md` on the `psi-error-reports` branch for review (as described above). While individual errors are reported, more sophisticated in-script retry mechanisms with backoff for transient network issues could still be beneficial.
-   **Data Visualization:** The current presentation of results in a table via `index.html` can be further enhanced with sorting, filtering, charts, or graphs.
-   **Historical Data:** The current setup overwrites results with each run. Implementing a system to track scores over time could be a valuable addition.
-   **Desktop vs. Mobile:** The script currently focuses on mobile strategy. Audits for desktop could also be incorporated.

## Contributing

Contributions are welcome! Here are a few ways you can help:

-   **Updating the Website List:** If you find inaccuracies in `sites_das_prefeituras_brasileiras.csv` or want to add new official municipal websites, please feel free to submit a pull request with your changes.
-   **Improving Scripts & Workflow:** Enhancements to the `collect-psi.js` script, the GitHub Actions workflow, or the `index.html` presentation are welcome.
-   **Bug Fixes & Feature Requests:** If you encounter any issues or have ideas for new features, please open an issue on GitHub.

When contributing, please ensure your changes are well-tested and follow the general coding style of the project.
