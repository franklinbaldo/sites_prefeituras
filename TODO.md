# Project TODO List

## Core Functionality Enhancements

- **Enhance Error Handling in `collect-psi.js`**:
    - Implement retry mechanisms with exponential backoff for API requests to handle transient network issues or API rate limits more gracefully.
    - Add more detailed logging for errors encountered during data collection.

- **Implement Data Visualization in `index.html`**:
    - **Develop `js/data-processor.js`**:
        - Load, parse, and process data from `data/psi-results.json`.
        - Merge PSI data with geographic data from `data/brasil-municipios.geojson` using IBGE codes (requires ensuring `psi-results.json` or the initial CSV includes IBGE codes that match the GeoJSON properties).
    - **Develop `js/map-controller.js`**:
        - Display PSI scores and related data on the Leaflet map.
        - Use markers, possibly color-coded by performance or accessibility scores.
        - Implement popups on markers to show detailed PSI scores (Performance, Accessibility, SEO, Best Practices) for each municipality.
        - Add filtering options to the map (e.g., by state, by score range).
    - **Develop `js/chart-generator.js`**:
        - Create various interactive charts to summarize the PSI data (e.g., using a library like Chart.js or D3.js).
        - Examples:
            - Bar chart showing average scores (Performance, Accessibility, etc.) per state or region.
            - Histogram showing the distribution of scores for each metric.
            - Scatter plot of Performance vs. Accessibility.
    - **Integrate map and charts into `index.html`**:
        - Design a user-friendly layout for `index.html` to present the map and charts effectively.
        - Ensure the page is responsive and accessible.

- **Implement Historical Data Tracking**:
    - Modify `collect-psi.js` to store results with timestamps, perhaps in a way that new results are appended rather than overwriting the `psi-results.json` file (e.g., a JSON array or a new file per run in a specific directory).
    - Update data processing and visualization components to allow users to view trends over time.

- **Incorporate Desktop PSI Scans**:
    - Update `collect-psi.js` to fetch PSI scores for the 'desktop' strategy in addition to 'mobile'.
    - Store both mobile and desktop scores.
    - Update visualization components to allow users to switch between mobile and desktop views or compare them.

## Documentation and Testing

- **Improve `README.md`**:
    - Add detailed descriptions of new data visualization features as they are implemented.
    - Explain how to interpret the map and charts.
    - Document the structure of `psi-results.json` if it evolves.
- **Add Unit/Integration Tests**:
    - Write tests for data processing logic in `js/data-processor.js`.
    - Add tests for `js/map-controller.js` if possible (mocking Leaflet might be complex).
    - Consider tests for `collect-psi.js` (e.g., mocking API calls, testing CSV parsing).

## Data Management

- **Validate and Clean `sites_das_prefeituras_brasileiras.csv`**:
    - Check for broken or incorrect URLs.
    - Ensure IBGE codes are accurate and present for linking with GeoJSON data.
    - Potentially add population data or other relevant metadata for richer analysis.
