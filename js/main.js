// js/main.js

let psiData = [];
let currentData = [];
let currentSort = { column: null, asc: true };

function scoreClass(val) {
    if (val >= 0.9) return 'score-good';
    if (val >= 0.5) return 'score-ok';
    return 'score-bad';
}

function renderTable(data) {
    const tableBody = document.getElementById('psi-results-table').getElementsByTagName('tbody')[0];
    tableBody.innerHTML = '';
    data.forEach(item => {
        const row = tableBody.insertRow();

        const urlCell = row.insertCell();
        urlCell.textContent = item.url;

        const performanceCell = row.insertCell();
        performanceCell.textContent = (item.performance * 100).toFixed(0) + '%';
        performanceCell.className = scoreClass(item.performance);

        const accessibilityCell = row.insertCell();
        accessibilityCell.textContent = (item.accessibility * 100).toFixed(0) + '%';
        accessibilityCell.className = scoreClass(item.accessibility);

        const seoCell = row.insertCell();
        seoCell.textContent = (item.seo * 100).toFixed(0) + '%';
        seoCell.className = scoreClass(item.seo);

        const bestPracticesCell = row.insertCell();
        bestPracticesCell.textContent = item.bestPractices ? (item.bestPractices * 100).toFixed(0) + '%' : 'N/A';
        if (item.bestPractices) {
            bestPracticesCell.className = scoreClass(item.bestPractices);
        }

        const timestampCell = row.insertCell();
        timestampCell.textContent = new Date(item.timestamp).toLocaleString();
    });
}

function sortBy(column) {
    if (currentSort.column === column) {
        currentSort.asc = !currentSort.asc;
    } else {
        currentSort.column = column;
        currentSort.asc = true;
    }
    const dir = currentSort.asc ? 1 : -1;
    currentData.sort((a, b) => {
        if (a[column] < b[column]) return -1 * dir;
        if (a[column] > b[column]) return 1 * dir;
        return 0;
    });
    renderTable(currentData);
}

function initializeSorting() {
    const headers = document.querySelectorAll('#psi-results-table th');
    const fields = ['url', 'performance', 'accessibility', 'seo', 'bestPractices', 'timestamp'];
    headers.forEach((th, idx) => {
        th.addEventListener('click', () => sortBy(fields[idx]));
    });
}

function initializeFiltering() {
    const input = document.getElementById('table-filter');
    if (!input) return;
    input.addEventListener('keyup', () => {
        const q = input.value.toLowerCase();
        currentData = psiData.filter(item =>
            item.url.toLowerCase().includes(q) || String(item.ibge_code || '').includes(q)
        );
        renderTable(currentData);
    });
}

async function initializeApp() {
    psiData = await appDataProcessor.getPsiData();
    if (psiData) {
        console.log("PSI Data fetched successfully in main.js:", psiData.length, "records");
        currentData = [...psiData];
        initializeSorting();
        initializeFiltering();
        initializeExport();
        renderTable(currentData);
        appChartGenerator.generateAllCharts(currentData); // Generate charts
    } else {
        console.error("Could not fetch PSI data to populate the table.");
        // Attempt to generate charts even if data is null/empty to display "No data" message
        appChartGenerator.generateAllCharts(null);
    }
}

function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

function dataToCsv(data) {
    const header = ['url','performance','accessibility','seo','bestPractices','timestamp','ibge_code'];
    const lines = data.map(item => header.map(h => item[h] !== undefined ? item[h] : '').join(','));
    return header.join(',') + '\n' + lines.join('\n');
}

function downloadCSV(data, filename) {
    const csv = dataToCsv(data);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

function initializeExport() {
    const btn = document.getElementById('export-data-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
        downloadCSV(currentData, 'psi-results.csv');
        downloadJSON(currentData, 'psi-results.json');
    });
}

initializeApp();
