// Global variable to store fetched municipality data
let allMunicipalityData = [];
let rankingLoaded = false;
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
    return null;
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

function setDashboardStatus(id, message = "", kind = "status") {
  const element = document.getElementById(id);
  if (!element) return;

  if (!message) {
    element.hidden = true;
    element.textContent = "";
    element.removeAttribute("role");
    element.removeAttribute("data-kind");
    return;
  }

  element.textContent = message;
  element.hidden = false;
  element.setAttribute("role", kind === "error" ? "alert" : "status");
  element.dataset.kind = kind;
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
        const statNumbers = entry.target.querySelectorAll(".stat-number[data-count]");
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
    const totalSitesEl = document.querySelector('[data-stat="total"]');
    const avgAccessEl = document.querySelector('[data-stat="avg-accessibility"]');
    const avgPerfEl = document.querySelector('[data-stat="avg-performance"]');

    if (totalSitesEl) totalSitesEl.dataset.count = summary.total_audits || 0;
    if (avgAccessEl) avgAccessEl.dataset.count = ((summary.avg_mobile_accessibility || 0) * 100).toFixed(1);
    if (avgPerfEl) avgPerfEl.dataset.count = ((summary.avg_mobile_performance || 0) * 100).toFixed(1);

    observer.observe(statsSection);
  }
}

function showSummaryUnavailable() {
  setDashboardStatus(
    "summaryStatus",
    "Não foi possível carregar o panorama nacional agora. O ranking, quando disponível, continua independente.",
    "error",
  );

  document.querySelectorAll(".stat-number[data-count]").forEach((element) => {
    element.removeAttribute("data-count");
    element.textContent = "—";
  });

  const lastUpdatedEl = document.getElementById("lastUpdated");
  if (lastUpdatedEl) {
    lastUpdatedEl.removeAttribute("datetime");
    lastUpdatedEl.textContent = "—";
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

function updateRankingEmptyState(data) {
  if (data.length === 0) {
    setDashboardStatus(
      "rankingStatus",
      "Nenhum município corresponde aos filtros e à busca atuais.",
    );
  } else {
    setDashboardStatus("rankingStatus");
  }
}

// Apply all filters and search term
function applyAllFiltersAndSearch() {
  if (!rankingLoaded) return;

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
  updateRankingEmptyState(filteredData);

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

// Search functionality
function searchCity() {
  applyAllFiltersAndSearch();

  const rankingSection = document.querySelector(".ranking-section");
  if (rankingSection) {
    rankingSection.scrollIntoView({ behavior: "smooth" });
  }
}

// Main initialization function
async function initializeApp() {
  // Fetch the ranking and summary independently so one failure does not erase the other.
  const [psiData, summary] = await Promise.all([
    fetchPsiData(),
    fetchSummary(),
  ]);

  const rankingTable = document.getElementById("ranking-table");
  if (psiData === null) {
    rankingLoaded = false;
    if (rankingTable) rankingTable.hidden = true;
    setDashboardStatus(
      "rankingStatus",
      "Não foi possível carregar o ranking agora. Tente novamente mais tarde.",
      "error",
    );
  } else {
    rankingLoaded = true;
    allMunicipalityData = psiData;
    if (rankingTable) rankingTable.hidden = false;
    populateStateFilter(allMunicipalityData);
    renderRanking(allMunicipalityData);
    updateRankingEmptyState(allMunicipalityData);
  }

  if (summary === null) {
    showSummaryUnavailable();
  } else {
    setDashboardStatus("summaryStatus");
    initStatsAnimation(summary);

    // Update last updated info while preserving the exact timestamp.
    if (summary.generated_at) {
      const lastUpdatedEl = document.getElementById("lastUpdated");
      if (lastUpdatedEl) {
        const date = new Date(summary.generated_at);
        lastUpdatedEl.setAttribute("datetime", summary.generated_at);
        lastUpdatedEl.textContent = date.toLocaleString("pt-BR");
      }
    }
  }

  setupFilters();

  // Native form submission covers both Enter and button activation exactly once.
  const searchForm = document.getElementById("citySearchForm");
  if (searchForm) {
    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      searchCity();
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

  console.log(
    "Dashboard initialized with",
    rankingLoaded ? allMunicipalityData.length : "unavailable",
    "sites",
  );
}

// Run initialization when DOM is ready
document.addEventListener("DOMContentLoaded", initializeApp);
