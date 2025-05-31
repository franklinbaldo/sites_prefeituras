// js/data-processor.js

const appDataProcessor = {
  fetchPsiResults: async function() {
    try {
      const response = await fetch('data/psi-results.json');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error fetching PSI results:", error);
      return null; // Or rethrow, or return an empty array
    }
  },

  getPsiData: async function() {
    return await this.fetchPsiResults();
  }
};
