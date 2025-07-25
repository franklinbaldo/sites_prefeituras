// js/data-processor.js

const appDataProcessor = {
  fetchPsiResults: async function () {
    try {
      // Updated to fetch the new JSON file generated by the GitHub Action
      const response = await fetch("data/psi-latest-viewable-results.json");
      if (!response.ok) {
        if (response.status === 404) {
          console.error(
            "Error fetching PSI results: data/psi-latest-viewable-results.json not found. The GitHub Action might not have run successfully yet or the file was not generated.",
          );
          // Display a message to the user in the UI
          const tableBody = document
            .getElementById("psi-results-table")
            .getElementsByTagName("tbody")[0];
          if (tableBody) {
            tableBody.innerHTML =
              '<tr><td colspan="6">Os dados ainda não estão disponíveis. Por favor, verifique mais tarde. A rotina de coleta de dados pode não ter sido executada ainda.</td></tr>';
          }
        } else {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return null;
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error fetching PSI results:", error);
      const tableBody = document
        .getElementById("psi-results-table")
        .getElementsByTagName("tbody")[0];
      if (tableBody) {
        tableBody.innerHTML =
          '<tr><td colspan="6">Erro ao carregar os dados. Por favor, tente recarregar a página.</td></tr>';
      }
      return null; // Or rethrow, or return an empty array
    }
  },

  getPsiData: async function () {
    return await this.fetchPsiResults();
  },
};
