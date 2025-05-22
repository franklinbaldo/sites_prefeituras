document.addEventListener('DOMContentLoaded', () => {
  const tableBody = document.querySelector('table tbody');
  const headers = document.querySelectorAll('table th');
  let auditData = [];
  let sortDirection = {}; // To store sort direction for each column

  async function fetchDataAndRender() {
    try {
      const response = await fetch('accessibility-results.json');
      if (!response.ok) {
        // If the file is not found, it's okay, means no data yet.
        if (response.status === 404) {
          console.log('accessibility-results.json not found. Displaying empty table.');
          tableBody.innerHTML = `<tr><td colspan="6">Nenhum dado de acessibilidade encontrado ainda.</td></tr>`;
          return;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      auditData = await response.json();
      if (!Array.isArray(auditData) || auditData.length === 0) {
        console.log('No data in accessibility-results.json. Displaying empty table.');
        tableBody.innerHTML = `<tr><td colspan="6">Nenhum dado de acessibilidade encontrado.</td></tr>`;
        return;
      }
      // Default sort by accessibility score, descending, errors/nulls last
      auditData.sort((a, b) => {
        const scoreA = a.accessibility_score === null || a.error_message ? -1 : a.accessibility_score;
        const scoreB = b.accessibility_score === null || b.error_message ? -1 : b.accessibility_score;
        return scoreB - scoreA;
      });
      renderTable(auditData);
    } catch (error) {
      console.error('Error fetching or parsing data:', error);
      tableBody.innerHTML = `<tr><td colspan="6">Erro ao carregar os dados. Verifique o console.</td></tr>`;
    }
  }

  function renderTable(data) {
    tableBody.innerHTML = ''; // Clear existing rows
    if (data.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="6">Nenhum dado de acessibilidade para exibir.</td></tr>`;
      return;
    }
    data.forEach(item => {
      const row = tableBody.insertRow();
      row.insertCell().textContent = item.nome_municipio || 'N/A';
      row.insertCell().textContent = item.uf || 'N/A';
      row.insertCell().textContent = item.codigo_ibge || 'N/A';
      
      const urlCell = row.insertCell();
      if (item.url) {
        const link = document.createElement('a');
        link.href = item.url;
        // Display only the domain for brevity if it's a long URL
        try {
            const urlObject = new URL(item.url);
            link.textContent = urlObject.hostname;
        } catch (e) {
            link.textContent = item.url; // fallback to full URL if parsing fails
        }
        link.target = '_blank';
        urlCell.appendChild(link);
      } else {
        urlCell.textContent = 'N/A';
      }
      
      let scoreDisplay = 'N/A';
      if (item.error_message) {
          scoreDisplay = 'Falhou';
      } else if (item.accessibility_score !== null && item.accessibility_score !== undefined) {
          scoreDisplay = item.accessibility_score;
      }
      row.insertCell().textContent = scoreDisplay;
      row.insertCell().textContent = item.audit_timestamp ? new Date(item.audit_timestamp).toLocaleString('pt-BR') : 'N/A';
    });
  }

  headers.forEach((header, index) => {
    // Store the original text and add sort indicator space
    const originalHeaderText = header.textContent;
    header.textContent = originalHeaderText + ' '; 

    header.addEventListener('click', () => {
      const columnKeys = ['nome_municipio', 'uf', 'codigo_ibge', 'url', 'accessibility_score', 'audit_timestamp'];
      const columnProperty = columnKeys[index];
      
      // Reset sort indicators on other headers
      headers.forEach((h, i) => {
        if (i !== index) {
          h.textContent = h.textContent.replace(/[▲▼]$/, ''); // Clear indicator
          h.textContent = h.textContent.trim() + ' '; // ensure space for next indicator
        }
      });

      const currentDirection = sortDirection[columnProperty];
      let direction;
      if (currentDirection === 'asc') {
        direction = 'desc';
        header.textContent = originalHeaderText + '▼';
      } else if (currentDirection === 'desc') {
        direction = 'none'; // to revert to default sort or unsorted
        header.textContent = originalHeaderText + ' '; // No indicator or default
      } else { // 'none' or undefined
        direction = 'asc';
        header.textContent = originalHeaderText + '▲';
      }
      
      // If direction is 'none', revert to default sort (by score descending)
      if (direction === 'none') {
        delete sortDirection[columnProperty]; // remove specific sort
        // Default sort by accessibility score, descending, errors/nulls last
        auditData.sort((a, b) => {
            const scoreA = a.accessibility_score === null || a.error_message ? -1 : a.accessibility_score;
            const scoreB = b.accessibility_score === null || b.error_message ? -1 : b.accessibility_score;
            return scoreB - scoreA;
        });
      } else {
        sortDirection = { [columnProperty]: direction };

        auditData.sort((a, b) => {
          let valA = a[columnProperty];
          let valB = b[columnProperty];

          if (columnProperty === 'accessibility_score') {
            valA = valA === null || a.error_message ? -Infinity : valA; 
            valB = valB === null || b.error_message ? -Infinity : valB;
          } else if (columnProperty === 'audit_timestamp') {
            valA = valA ? new Date(valA).getTime() : 0;
            valB = valB ? new Date(valB).getTime() : 0;
          } else {
            valA = String(valA === null || valA === undefined ? '' : valA).toLowerCase();
            valB = String(valB === null || valB === undefined ? '' : valB).toLowerCase();
          }

          if (valA < valB) return direction === 'asc' ? -1 : 1;
          if (valA > valB) return direction === 'asc' ? 1 : -1;
          return 0;
        });
      }
      renderTable(auditData);
    });
  });

  fetchDataAndRender();
});
