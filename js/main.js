// js/main.js

// Main function to orchestrate data loading and table population
async function initializeApp() {
    // Fetch PSI data using the data processor
    const psiData = await appDataProcessor.getPsiData(); // Assuming appDataProcessor is globally available

    if (psiData) {
        console.log("PSI Data fetched successfully in main.js:", psiData.length, "records");
        const tableBody = document.getElementById('psi-results-table').getElementsByTagName('tbody')[0];

        psiData.forEach(item => {
            const row = tableBody.insertRow();

            const urlCell = row.insertCell();
            urlCell.textContent = item.url;

            const performanceCell = row.insertCell();
            performanceCell.textContent = (item.performance * 100).toFixed(0) + '%';

            const accessibilityCell = row.insertCell();
            accessibilityCell.textContent = (item.accessibility * 100).toFixed(0) + '%';

            const seoCell = row.insertCell();
            seoCell.textContent = (item.seo * 100).toFixed(0) + '%';

            const bestPracticesCell = row.insertCell();
            bestPracticesCell.textContent = item.bestPractices ? (item.bestPractices * 100).toFixed(0) + '%' : 'N/A';

            const timestampCell = row.insertCell();
            timestampCell.textContent = new Date(item.timestamp).toLocaleString();
        });

    } else {
        console.error("Could not fetch PSI data to populate the table.");
    }
}

// Run the initialization
initializeApp();
