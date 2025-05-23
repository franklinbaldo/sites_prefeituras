// Initialize the map and set its view to Brazil's approximate geographical center and zoom level
const map = L.map('map').setView([-14.2350, -51.9253], 5);

// Add a tile layer from OpenStreetMap
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Placeholder for future code (e.g., loading GeoJSON, adding data layers)
console.log("Map initialized.");
