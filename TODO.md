# Priority TODO – "Mapa de Acessibilidade" Roadmap (v2025‑05‑30)

*After a full review of the current codebase, these are the **next actions** grouped by urgency and leverage. Finishing the **Critical Path** will turn the prototype into a usable public demo; the later phases harden it for production and research use.*

---

## 0 · Critical Path – **Finish the Minimum Viable Map** (⚡ Do these first)

| ⚙︎ | Task                                                                                                                | Owner | Notes                                                                                                                                                  |   |                                                                              |
| -- | ------------------------------------------------------------------------------------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | - | ---------------------------------------------------------------------------- |
| ☐  | **Populate GeoJSON files** (`data/brasil‑estados.geojson`, `data/brasil‑municipios.geojson`) with real IBGE shapes  |       | Download from IBGE or [https://github.com/tbrugz/ibge‑geojson](https://github.com/tbrugz/ibge‑geojson). Keep only the props we need → smaller payload. |   |                                                                              |
| ☐  | **Expose `codigo_ibge` field** in `collect-psi.js` results                                                          |       | Already present in CSV; include as `ibge_code` in JSON to enable precise GeoJSON join                                                                  |   | Without this, `map‑controller.js` cannot match PSI rows ↔︎ GeoJSON features. |
| ☐  | Refactor `map‑controller.addMarkersToMap()` to use exact `ibge_code` lookup instead of fuzzy `extractNameFromUrl()` |       | Simpler + deterministic.                                                                                                                               |   |                                                                              |
| ☐  | Verify that markers render end‑to‑end with one known city in **TEST** mode                                          |       | Use `test_sites.csv` after adding IBGE codes.                                                                                                          |   |                                                                              |

> **Outcome:** A functional leaflet map that shows PSI scores for at least a handful of municipalities.

---

\## 1 · High‑Impact Quality Improvements (🏃 Sprint after Critical Path)

* ☐ **Historical Runs** – change `collect‑psi.js` to append to `data/history/YYYY‑MM‑DD.json` instead of overwriting.

  * Update `data‑processor.js` to select the latest file or show a time‑slider later.
  * Add a cron note in README.
* ☐ **Retry + Backoff** in `originalFetchPSI()` (wrap `p‑limit` job with exponential backoff on 429/5xx).
  Write errors once to `psi_errors.log` *and* `console.warn`.
* ☐ **Desktop strategy support** – parametrize strategy (`mobile`/`desktop`) and store both in result rows (`performance_mobile`, `performance_desktop`, …).
  UI toggle later.
* ☐ **GeoJSON lazy‑load** – fetch only the **state** layer until user zooms < 7, then load municipalities; reduces first paint.

---

\## 2 · UI & UX Polishing (🎨)

* ☐ Clean mobile layout: responsive map height, hamburger nav.
* ☐ Replace bare export button with CSV & JSON download of current filter.
* ☐ Color‑code markers by accessibility score bucket (red < 50, orange < 80, green ≥ 80).
* ☐ Add a legend component.

---

\## 3 · Testing & CI (🧪)

* ☐ Unit tests for `data‑processor.js` merge logic (GeoJSON ↔︎ PSI).
* ☐ E2E smoke test on GitHub Actions: run in `--test` mode and fail the build if collected JSON is empty.

---

\## 4 · Stretch Goals (🌱 nice‑to‑have)

* ☐ **Time‑series charts** with Recharts (line chart per metric per state).
* ☐ Progressive Web App: offline cache of last result + map tiles.
* ☐ Internationalization stub (pt‑BR ⇆ en‑US strings).

---

\## Suggested Sequence

1. **Geo data + IBGE plumbing** (Critical Path) – *1 day*.
2. Marker refactor & smoke test – *½ day*.
3. Retry + backoff – *½ day*.
4. Historical data directory – *1 day*.
5. Desktop strategy & UI toggle – *1 day*.
6. Visual polish & legends – *2 days*.
7. CI tests + deploy tweaks – *1 day*.

*This schedule assumes one developer (you) working focused blocks.  Feel free to adjust.*

---

\### Changelog Anchor
Create a `CHANGELOG.md` and log completion of each checklist item ✨.
