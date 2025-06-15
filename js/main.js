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
        renderTable(currentData);
    } else {
        console.error("Could not fetch PSI data to populate the table.");
    }
}

initializeApp();
