// js/main.js

// Initialize the map and set its view to Brazil's approximate geographical center and zoom level
const map = L.map('map').setView([-14.2350, -51.9253], 4); // Adjusted zoom slightly

// Add a tile layer from OpenStreetMap
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 18,
}).addTo(map);

console.log("Map initialized.");

// Main function to orchestrate data loading and map population
async function initializeApp() {
    // Load GeoJSON data first (or in parallel if independent)
    await appMapController.loadGeoJsonData(); // Assuming appMapController is globally available

    // Fetch PSI data using the data processor
    const psiData = await appDataProcessor.getPsiData(); // Assuming appDataProcessor is globally available

    if (psiData) {
        console.log("PSI Data fetched successfully in main.js:", psiData.length, "records");
        // Pass PSI data to the map controller
        appMapController.setPsiData(psiData);
        // Add markers to the map
        appMapController.addMarkersToMap(map);
    } else {
        console.error("Could not fetch PSI data to populate the map.");
    }
}

// Run the initialization
initializeApp();
