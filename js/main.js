// Initialize the map and set its view to Brazil's approximate geographical center and zoom level
const map = L.map('map').setView([-14.2350, -51.9253], 5);

// Add a tile layer from OpenStreetMap
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

console.log("Map initialized. Loading GeoJSON data...");

let stateScores = {}; // To store placeholder scores for each state

// Function to load GeoJSON data
async function loadGeoJSON(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log("GeoJSON data loaded successfully."); // Simplified log for brevity here
        return data;
    } catch (error) {
        console.error("Error loading GeoJSON data:", error);
    }
}

// Function to define style for GeoJSON features (states)
// This function will be updated in a subsequent step to use stateScores for color-coding
function styleStates(feature) {
    return {
        fillColor: '#D3D3D3', // Default fill, will be overridden by score-based color
        weight: 1,
        opacity: 1,
        color: 'white',
        fillOpacity: 0.7
    };
}

// Load Brazil states GeoJSON and add to map
loadGeoJSON('data/brasil-estados.geojson').then(geojsonData => {
    if (geojsonData) {
        // Generate placeholder scores for each state
        if (geojsonData.features) { // Ensure features exist
            geojsonData.features.forEach(feature => {
                // IMPORTANT: Assumed 'SIGLA_UF' exists and is unique based on subtask description.
                // If 'data/brasil-estados.geojson' were available for inspection and another property
                // like 'CD_UF' or 'NM_UF' was more suitable, this line would be changed.
                const stateId = feature.properties.SIGLA_UF;
                if (stateId) {
                    stateScores[stateId] = Math.floor(Math.random() * 101); // Random score 0-100
                } else {
                    console.warn("Feature without a valid 'SIGLA_UF' property found:", feature.properties);
                }
            });
            console.log("Placeholder state scores generated:", stateScores);
        } else {
            console.warn("GeoJSON data does not contain a 'features' array. Cannot generate scores.", geojsonData);
        }

        L.geoJson(geojsonData, {
            style: styleStates
        }).addTo(map);
        console.log("GeoJSON layer added to map with basic styling. Scores ready for use.");
    }
});
