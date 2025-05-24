// js/map-controller.js
const appMapController = {
  geoJsonData: null, // To store GeoJSON data
  psiResultsData: null, // To store PSI results

  // Function to load GeoJSON data for municipalities
  loadGeoJsonData: async function(path = 'data/brasil-municipios.geojson') {
    try {
      const response = await fetch(path);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      this.geoJsonData = await response.json();
      console.log("GeoJSON data loaded successfully.");
    } catch (error) {
      console.error("Error fetching GeoJSON data:", error);
      this.geoJsonData = null;
    }
  },

  // Function to set PSI data (called from main.js after data is fetched)
  setPsiData: function(psiData) {
    this.psiResultsData = psiData;
  },

  // Function to add markers to the map
  // This is a simplified version. It assumes psiResultsData contains objects with 'url' and 'ibge_code'.
  // It tries to find matching features in geoJsonData using 'ibge_code'.
  addMarkersToMap: function(mapInstance) {
    if (!this.psiResultsData) {
      console.warn("PSI data not available in map controller.");
      return;
    }
    if (!this.geoJsonData) {
      console.warn("GeoJSON data not available in map controller.");
      // As a fallback, could try to plot based on a generic Brazil location,
      // but that won't be very useful. For now, we'll just log.
      return;
    }

    console.log("Attempting to add markers. PSI results count:", this.psiResultsData.length);
    console.log("GeoJSON features count:", this.geoJsonData.features.length);

    let markersAdded = 0;
    this.psiResultsData.forEach(item => {
      // Assumption: psi-results.json items need an 'ibge_code' to match GeoJSON.
      // This 'ibge_code' is not in the current psi-results.json structure.
      // This part of the code WILL NOT WORK as intended without IBGE codes in psi-results.json
      // or an alternative way to link PSI results to GeoJSON features.
      // For the purpose of this subtask, we'll proceed with this placeholder logic.
      // The TODO.md already mentions merging PSI data with GeoJSON using IBGE codes.

      // Let's try to find a feature by name for demonstration if IBGE code is missing.
      // This is a VERY ROUGH match and likely unreliable.
      // A proper solution needs consistent identifiers (like IBGE codes).
      const municipalityName = this.extractNameFromUrl(item.url); // Helper needed
      const geoJsonFeature = this.geoJsonData.features.find(feature => {
        // GeoJSON properties might be like feature.properties.CD_MUN (IBGE code)
        // or feature.properties.NM_MUN (Name)
        // This needs to be verified against the actual GeoJSON structure.
        // For now, assuming NM_MUN for name matching.
        return feature.properties && feature.properties.NM_MUN &&
               municipalityName && feature.properties.NM_MUN.toLowerCase().includes(municipalityName.toLowerCase());
      });

      if (geoJsonFeature && geoJsonFeature.geometry) {
        // Leaflet expects coordinates in [lat, lon] order.
        // GeoJSON is typically [lon, lat]. We need to find a representative point.
        // For MultiPolygon, we might need to calculate a centroid or use the first polygon's first coordinate.
        let coords;
        if (geoJsonFeature.geometry.type === "Point") {
            coords = [geoJsonFeature.geometry.coordinates[1], geoJsonFeature.geometry.coordinates[0]];
        } else if (geoJsonFeature.geometry.type === "Polygon") {
            // Simple case: use first coordinate of the first ring (not ideal, but for placeholder)
            coords = [geoJsonFeature.geometry.coordinates[0][0][1], geoJsonFeature.geometry.coordinates[0][0][0]];
        } else if (geoJsonFeature.geometry.type === "MultiPolygon") {
             // Simple case: use first coordinate of the first ring of the first polygon
            coords = [geoJsonFeature.geometry.coordinates[0][0][0][1], geoJsonFeature.geometry.coordinates[0][0][0][0]];
        }

        if (coords) {
            L.marker(coords).addTo(mapInstance)
              .bindPopup(`URL: ${item.url}<br>Performance: ${item.performance || 'N/A'}`);
            markersAdded++;
        }
      }
    });
    console.log(`Added ${markersAdded} markers to the map based on name matching (if any).`);
    if (markersAdded === 0) {
        console.warn("No markers were added. This is likely due to missing IBGE codes in psi-results.json or inability to match by name. This needs to be addressed by ensuring IBGE codes are present and used for matching in js/data-processor.js as per TODO.md.");
    }
  },

  // Helper function to attempt to extract a municipality name from URL (very basic)
  extractNameFromUrl: function(url) {
    try {
      const hostname = new URL(url).hostname;
      // Example: www.NOMECIDADE.uf.gov.br -> NOMECIDADE
      const parts = hostname.split('.');
      if (parts.length >= 4 && parts[0] === 'www') return parts[1];
      if (parts.length >= 3 && parts[0] !== 'www') return parts[0]; // prefeitura.NOMECIDADE.uf.gov.br
    } catch (e) {
      return null;
    }
    return null;
  }
};
