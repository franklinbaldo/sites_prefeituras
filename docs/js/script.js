// Global variable to store fetched municipality data
let allMunicipalityData = [];
let currentFilters = {
  state: "",
  population: "",
};

// Base URL for JSON data files
const DATA_BASE_URL = "./data";

// Function to fetch PSI data from static JSON
async function fetchPsiData() {
  try {
    const response = await fetch(`${DATA_BASE_URL}/ranking.json`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    console.log(`Loaded ${data.total} sites from ranking.json`);
    return data.sites || [];
  } catch (error) {
    console.error("Error fetching PSI data:", error);
    return [];
  }
}

// Function to fetch summary metrics
async function fetchSummary() {
  try {
    const response = await fetch(`${DATA_BASE_URL}/summary.json`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching summary:", error);
    return null;
  }
}

// Animation for counting numbers
function animateCounter(element, target, duration = 2000) {
  const start = 0;
  const increment = target / (duration / 16);
  let current = start;

  const timer = setInterval(() => {
    current += increment;
    if (current >= target) {
      current = target;
      clearInterval(timer);
    }

    if (target % 1 !== 0) {
      element.textContent = current.toFixed(1);
    } else {
      element.textContent = Math.floor(current);
    }
  }, 16);
}

// Initialize stats animation when section is visible
function initStatsAnimation(summary) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const statNumbers = entry.target.querySelectorAll(".stat-number");
        statNumbers.forEach((stat) => {
          const target = parseFloat(stat.dataset.count);
          animateCounter(stat, target);
        });
        observer.unobserve(entry.target);
      }
    });
  });

  const statsSection = document.querySelector(".stats-section");
  if (statsSection) {
    // Update stats from summary data
    if (summary) {
      const totalSitesEl = document.querySelector('[data-stat="total"]');
      const avgAccessEl = document.querySelector('[data-stat="avg-accessibility"]');
      const avgPerfEl = document.querySelector('[data-stat="avg-performance"]');

      if (totalSitesEl) totalSitesEl.dataset.count = summary.total_audits || 0;
      if (avgAccessEl) avgAccessEl.dataset.count = ((summary.avg_mobile_accessibility || 0) * 100).toFixed(1);
      if (avgPerfEl) avgPerfEl.dataset.count = ((summary.avg_mobile_performance || 0) * 100).toFixed(1);
    }
    observer.observe(statsSection);
  }
}

// Get score class for styling (scores are 0-100)
function getScoreClass(score) {
  if (score >= 80) return "score-excellent";
  if (score >= 60) return "score-good";
  return "score-poor";
}

// Get badge class for styling (scores are 0-100)
function getBadgeClass(score) {
  if (score >= 80) return "badge-excellent";
  if (score >= 60) return "badge-good";
  return "badge-poor";
}

// Get badge text (scores are 0-100)
function getBadgeText(score) {
  if (score >= 80) return "Excelente";
  if (score >= 60) return "Bom";
  return "Precisa Melhorar";
}

// Render ranking list
function renderRanking(data) {
  const table = new Tabulator("#ranking-table", {
    data: data,
    layout: "fitColumns",
    pagination: "local",
    paginationSize: 50,
    columns: [
      { title: "Rank", field: "rank", width: 80 },
      { title: "Cidade", field: "name", formatter: "link", formatterParams: { urlField: "url" } },
      { title: "Estado", field: "state" },
      { title: "Score", field: "score", hozAlign: "center", formatter: "progress", formatterParams: {
          min: 0,
          max: 100,
          color: ["red", "orange", "green"],
          legend: function(value){
              return value.toFixed(1);
          }
      }},
    ],
  });
}

// Apply all filters and search term
function applyAllFiltersAndSearch() {
  const searchInput = document.getElementById("citySearch");
  const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : "";

  let filteredData = allMunicipalityData;

  // Apply state filter
  if (currentFilters.state) {
    filteredData = filteredData.filter(
      (city) => city.state === currentFilters.state,
    );
  }

  // Apply population filter
  if (currentFilters.population) {
    filteredData = filteredData.filter(
      (city) => city.population === currentFilters.population,
    );
  }

  // Apply search term
  if (searchTerm) {
    filteredData = filteredData.filter(
      (city) =>
        city.name.toLowerCase().includes(searchTerm) ||
        city.state.toLowerCase().includes(searchTerm) ||
        (city.url && city.url.toLowerCase().includes(searchTerm)),
    );
  }

  renderRanking(filteredData);

  // If search was initiated, scroll to results
  if (searchInput && (
    document.activeElement === searchInput ||
    document.activeElement === document.querySelector(".search-btn")
  )) {
    const rankingSection = document.querySelector(".ranking-section");
    if (rankingSection) {
      rankingSection.scrollIntoView({ behavior: "smooth" });
    }
  }
}

// Filter functionality
function setupFilters() {
  const stateFilter = document.getElementById("stateFilter");
  const populationFilter = document.getElementById("populationFilter");

  if (stateFilter) {
    stateFilter.addEventListener("change", (event) => {
      currentFilters.state = event.target.value;
      applyAllFiltersAndSearch();
    });
  }

  if (populationFilter) {
    populationFilter.addEventListener("change", (event) => {
      currentFilters.population = event.target.value;
      applyAllFiltersAndSearch();
    });
  }
}

// Populate state filter with available states
function populateStateFilter(data) {
  const stateFilter = document.getElementById("stateFilter");
  if (!stateFilter) return;

  const states = [...new Set(data.map(item => item.state).filter(s => s && s !== "N/A"))].sort();

  states.forEach(state => {
    const option = document.createElement("option");
    option.value = state;
    option.textContent = state;
    stateFilter.appendChild(option);
  });
}

// Search functionality (called by button click or Enter key)
function searchCity() {
  applyAllFiltersAndSearch();

  const rankingSection = document.querySelector(".ranking-section");
  if (rankingSection) {
    rankingSection.scrollIntoView({ behavior: "smooth" });
  }
}

// Main initialization function
async function initializeApp() {
  // Fetch data in parallel
  const [psiData, summary] = await Promise.all([
    fetchPsiData(),
    fetchSummary(),
  ]);

  allMunicipalityData = psiData;

  // Populate state filter dynamically
  populateStateFilter(allMunicipalityData);

  renderRanking(allMunicipalityData);
  initStatsAnimation(summary);
  setupFilters();

  // Setup search functionality
  const searchInput = document.getElementById("citySearch");
  if (searchInput) {
    searchInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        searchCity();
      }
    });
  }

  const searchButton = document.querySelector(".search-btn");
  if (searchButton) {
    searchButton.addEventListener("click", searchCity);
  }

  // Smooth scrolling for scroll indicator
  const scrollIndicator = document.querySelector(".scroll-indicator");
  if (scrollIndicator) {
    scrollIndicator.addEventListener("click", function () {
      const statsSection = document.querySelector(".stats-section");
      if (statsSection) {
        statsSection.scrollIntoView({ behavior: "smooth" });
      }
    });
  }

  // Interactivity for methodology cards
  const methodologyCards = document.querySelectorAll(".methodology-card");
  if (methodologyCards) {
    methodologyCards.forEach((card) => {
      card.addEventListener("mouseenter", function () {
        this.style.transform = "translateY(-10px) scale(1.02)";
      });

      card.addEventListener("mouseleave", function () {
        this.style.transform = "translateY(0) scale(1)";
      });
    });
  }

  // Update last updated info
  if (summary && summary.generated_at) {
    const lastUpdatedEl = document.getElementById("lastUpdated");
    if (lastUpdatedEl) {
      const date = new Date(summary.generated_at);
      lastUpdatedEl.textContent = date.toLocaleString("pt-BR");
    }
  }

  console.log("Dashboard initialized with", allMunicipalityData.length, "sites");
}

// Run initialization when DOM is ready
document.addEventListener("DOMContentLoaded", initializeApp);
