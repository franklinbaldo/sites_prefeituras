# Priority TODO – "Painel de Acessibilidade" Roadmap (v2025‑05‑30)

*After a full review of the current codebase, these are the **next actions** grouped by urgency and leverage. Finishing the **Critical Path** will turn the prototype into a usable public demo; the later phases harden it for production and research use.*

---

## 0 · Critical Path – **Implement Basic Table View** (⚡ Do these first)

| ⚙︎ | Task                                                                                                                | Owner | Notes                                                                                                                                                  |   |                                                                              |
| -- | ------------------------------------------------------------------------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | - | ---------------------------------------------------------------------------- |
| ~~☐~~  | ~~**Populate GeoJSON files** (`data/brasil‑estados.geojson`, `data/brasil‑municipios.geojson`) with real IBGE shapes~~  |       | ~~Download from IBGE or [https://github.com/tbrugz/ibge‑geojson](https://github.com/tbrugz/ibge‑geojson). Keep only the props we need → smaller payload.~~ |   | _No longer applicable for table view_                                        |
| ☐  | **Expose `codigo_ibge` field** in `collect-psi.js` results                                                          |       | Already present in CSV; include as `ibge_code` in JSON. Useful for data enrichment/linking, though not critical for basic table.                      |   |                                                                              |
| ~~☐~~  | ~~Refactor `map‑controller.addMarkersToMap()` to use exact `ibge_code` lookup instead of fuzzy `extractNameFromUrl()`~~ |       | ~~Simpler + deterministic.~~                                                                                                                               |   | _No longer applicable_                                                      |
| ☐  | Verify that table renders end‑to‑end with PSI data in **TEST** mode                                                 |       | Use `test_sites.csv`.                                                                                                                                  |   |                                                                              |

> **Outcome:** A functional table view that shows PSI scores for items in `psi-results.json`.

---

\## 1 · High‑Impact Quality Improvements (🏃 Sprint after Critical Path)

* ☐ **Historical Runs** – change `collect‑psi.js` to append to `data/history/YYYY‑MM‑DD.json` instead of overwriting.

  * Update `data‑processor.js` to select the latest file or show a time‑slider later.
  * Add a cron note in README.
* ☐ **Retry + Backoff** in `originalFetchPSI()` (wrap `p‑limit` job with exponential backoff on 429/5xx).
  Write errors once to `psi_errors.log` *and* `console.warn`.
* ☐ **Desktop strategy support** – parametrize strategy (`mobile`/`desktop`) and store both in result rows (`performance_mobile`, `performance_desktop`, …).
  UI toggle later.
* ~~☐~~ **~~GeoJSON lazy‑load~~** – ~~fetch only the **state** layer until user zooms < 7, then load municipalities; reduces first paint.~~ _No longer applicable_

---

\## 2 · UI & UX Polishing (🎨)

* ☐ Clean mobile layout: responsive table, hamburger nav.
* ☐ Replace bare export button with CSV & JSON download of current table data (potentially filtered/sorted).
* ☐ Color‑code table rows or cells by accessibility score bucket (red < 50, orange < 80, green ≥ 80).
* ☐ Add a legend component if color-coding is implemented.
* ☐ Add sorting and filtering options to the table.

---

\## 3 · Testing & CI (🧪)

* ☐ Unit tests for `data‑processor.js` (if any complex logic remains or is added).
* ☐ E2E smoke test on GitHub Actions: run in `--test` mode and fail the build if collected JSON is empty or table fails to load.

---

\## 4 · Stretch Goals (🌱 nice‑to‑have)

* ☐ **Time‑series charts** with Recharts (line chart per metric, possibly aggregated by state/region if IBGE code is used).
* ☐ Progressive Web App: offline cache of last result.
* ☐ Internationalization stub (pt‑BR ⇆ en‑US strings).

---

\## Suggested Sequence

1. **IBGE plumbing** (expose `codigo_ibge` in data) – *½ day*.
2. Verify table rendering with test data – *½ day*.
3. Retry + backoff in `collect-psi.js` – *½ day*.
4. Historical data directory structure – *1 day*.
5. Desktop strategy & UI toggle for table columns – *1 day*.
6. Table UI/UX Polishing (sorting, filtering, color-coding) – *2-3 days*.
7. CI tests + deploy tweaks – *1 day*.

*This schedule assumes one developer (you) working focused blocks.  Feel free to adjust.*

---

\### Changelog Anchor
Create a `CHANGELOG.md` and log completion of each checklist item ✨.
* Pivoted from map-based visualization to a table-based view due to GeoJSON access issues and to simplify initial data presentation. (v2025-05-31)
