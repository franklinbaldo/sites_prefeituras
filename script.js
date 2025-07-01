// Global variable to store fetched municipality data
let allMunicipalityData = [];
let currentFilters = {
    state: "",
    population: ""
};

// Function to fetch PSI data
async function fetchPsiData() {
    try {
        const response = await fetch('data/psi-results.json'); // Assuming this is the correct path
        if (!response.ok) {
            if (response.status === 404) {
                console.warn('data/psi-results.json not found. Using sample data or displaying empty.');
                // Fallback to sample data or handle as needed
                return transformPsiData([]); // Return empty transformed data
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const rawData = await response.json();
        return transformPsiData(rawData);
    } catch (error) {
        console.error('Error fetching or parsing PSI data:', error);
        // Fallback to sample data or handle as needed
        return transformPsiData([]); // Return empty transformed data on error
    }
}

// Function to transform PSI data to the format expected by the new site
// Expected format: { name: string, state: string, population: string, score: number, rank: number, ibge_code?: string, url?: string }
function transformPsiData(rawData) {
    if (!Array.isArray(rawData)) {
        console.error("Raw data is not an array:", rawData);
        return [];
    }
    // Sort data by accessibility_score in descending order to assign rank
    // Items with null/undefined scores or errors should be ranked lower or handled
    const sortedData = rawData
        .filter(item => item && typeof item.accessibility_score === 'number') // Ensure score is a number
        .sort((a, b) => b.accessibility_score - a.accessibility_score);

    return sortedData.map((item, index) => {
        // Basic population category example (can be refined)
        let populationCategory = 'medium'; // Default
        // This part is tricky as psi-results.json doesn't have population numbers.
        // We might need another data source or make assumptions.
        // For now, let's leave it as 'medium' or try to infer from name if possible (unreliable).
        // Or, if the old data had a way to get population, that logic would be needed.
        // Since 'population' is used for filtering, it's important.
        // For now, we will omit population or set a default.
        // Let's assume a 'nome_municipio' and 'uf' exist or can be derived.
        // The psi-results.json has 'url' and 'ibge_code'
        // We need to map 'url' to 'name' and possibly extract 'state' from 'ibge_code' or 'url' if possible
        // This transformation is highly dependent on the actual content of psi-results.json

        let name = item.url; // Default to URL if no better name is found
        let state = 'N/A';   // Default state

        // Attempt to extract a more friendly name from the URL
        try {
            const urlObj = new URL(item.url);
            name = urlObj.hostname.replace(/^www\./, ''); // Remove www.
        } catch (e) {
            // keep item.url as name
        }

        // If 'ibge_code' is available and we have a mapping, we could get city name and state
        // For now, this is a placeholder.
        // Example: if item.ibge_code starts with '35', it's SP. This is a simplification.
        if (item.ibge_code) {
            const ibgeStr = String(item.ibge_code);
            // This is a very simplified mapping. A real app would need a proper IBGE code to state mapping.
            if (ibgeStr.startsWith('35')) state = 'SP';
            else if (ibgeStr.startsWith('33')) state = 'RJ';
            else if (ibgeStr.startsWith('31')) state = 'MG';
            else if (ibgeStr.startsWith('41')) state = 'PR';
            else if (ibgeStr.startsWith('43')) state = 'RS';
            // ... and so on for other states
        }


        return {
            name: name, // Placeholder, ideally from IBGE code or URL parsing
            state: state, // Placeholder, ideally from IBGE code
            population: populationCategory, // Needs a proper source or logic
            score: parseFloat((item.accessibility_score * 100).toFixed(1)), // Assuming score is 0-1, convert to 0-100
            rank: index + 1,
            ibge_code: item.ibge_code, // Keep original IBGE code
            url: item.url // Keep original URL
        };
    });
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
function initStatsAnimation() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const statNumbers = entry.target.querySelectorAll('.stat-number');
                statNumbers.forEach(stat => {
                    const target = parseFloat(stat.dataset.count);
                    animateCounter(stat, target);
                });
                observer.unobserve(entry.target);
            }
        });
    });

    observer.observe(document.querySelector('.stats-section'));
}

// Get score class for styling (scores are 0-100)
function getScoreClass(score) {
    if (score >= 80) return 'score-excellent';
    if (score >= 60) return 'score-good';
    return 'score-poor';
}

// Get badge class for styling (scores are 0-100)
function getBadgeClass(score) {
    if (score >= 80) return 'badge-excellent';
    if (score >= 60) return 'badge-good';
    return 'badge-poor';
}

// Get badge text (scores are 0-100)
function getBadgeText(score) {
    if (score >= 80) return 'Excelente';
    if (score >= 60) return 'Bom';
    return 'Precisa Melhorar';
}

// Render ranking list
function renderRanking(data) {
    const rankingList = document.getElementById('rankingList');
    if (!rankingList) return;

    if (!data || data.length === 0) {
        rankingList.innerHTML = '<p style="text-align: center; padding: 2rem;">Nenhum dado encontrado para os filtros selecionados.</p>';
        return;
    }

    rankingList.innerHTML = data.map(city => `
        <div class="ranking-item">
            <div class="ranking-position">${city.rank}°</div>
            <div class="ranking-city">
                <div class="city-name"><a href="${city.url}" target="_blank" title="Visitar site: ${city.name}">${city.name}</a></div>
                <div class="city-state">${city.state} (IBGE: ${city.ibge_code || 'N/A'})</div>
            </div>
            <div class="ranking-score ${getScoreClass(city.score)}">${city.score.toFixed(1)}</div>
            <div class="ranking-badge ${getBadgeClass(city.score)}">${getBadgeText(city.score)}</div>
        </div>
    `).join('');
}

// Apply all filters and search term
function applyAllFiltersAndSearch() {
    const searchInput = document.getElementById('citySearch');
    const searchTerm = searchInput.value.toLowerCase().trim();

    let filteredData = allMunicipalityData;

    // Apply state filter
    if (currentFilters.state) {
        filteredData = filteredData.filter(city => city.state === currentFilters.state);
    }

    // Apply population filter
    if (currentFilters.population) {
        filteredData = filteredData.filter(city => city.population === currentFilters.population);
    }

    // Apply search term
    if (searchTerm) {
        filteredData = filteredData.filter(city =>
            city.name.toLowerCase().includes(searchTerm) ||
            city.state.toLowerCase().includes(searchTerm) ||
            (city.ibge_code && String(city.ibge_code).includes(searchTerm))
        );
    }

    // Re-rank based on the filtered data for display purposes if needed, or keep original rank.
    // For now, we keep the original rank from the full dataset.
    // If re-ranking is desired:
    // filteredData.sort((a, b) => b.score - a.score).forEach((item, index) => item.rank = index + 1);

    renderRanking(filteredData);

    // If search was initiated, scroll to results
    if (document.activeElement === searchInput || document.activeElement === document.querySelector('.search-btn')) {
        const rankingSection = document.querySelector('.ranking-section');
        if (rankingSection) {
            rankingSection.scrollIntoView({ behavior: 'smooth' });
        }
    }
}


// Filter functionality
function setupFilters() {
    const stateFilter = document.getElementById('stateFilter');
    const populationFilter = document.getElementById('populationFilter');

    if (stateFilter) {
        stateFilter.addEventListener('change', (event) => {
            currentFilters.state = event.target.value;
            applyAllFiltersAndSearch();
        });
    }

    if (populationFilter) {
        populationFilter.addEventListener('change', (event) => {
            currentFilters.population = event.target.value;
            applyAllFiltersAndSearch();
        });
    }
}

// Search functionality (called by button click or Enter key)
function searchCity() {
    applyAllFiltersAndSearch(); // This now handles search term

    // Scroll to results - moved to applyAllFiltersAndSearch to trigger only on explicit search
    document.querySelector('.ranking-section').scrollIntoView({
        behavior: 'smooth'
    });
}

// Main initialization function
async function initializeApp() {
    allMunicipalityData = await fetchPsiData();

    // Populate state filter dynamically if desired, or ensure options in HTML are sufficient
    // For now, assumes HTML options are static or manually maintained.
    // Example: populateStateFilter(allMunicipalityData);

    renderRanking(allMunicipalityData); // Initial render with all (transformed) data
    initStatsAnimation(allMunicipalityData); // Initialize stats with data
    setupFilters(); // Setup filter event listeners

    const searchInput = document.getElementById('citySearch');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchCity(); // searchCity now calls applyAllFiltersAndSearch
            }
        });
    }

    const searchButton = document.querySelector('.search-btn');
    if (searchButton) {
        // Ensure the searchCity function is globally available or correctly referenced
        // If searchCity is defined within DOMContentLoaded, it might not be global.
        // We've defined it globally, so this should be fine.
        // searchButton.onclick = searchCity; // This is already in HTML, but good for dynamic buttons
    }

    // Smooth scrolling for scroll indicator
    document.querySelector('.scroll-indicator').addEventListener('click', function() {
        document.querySelector('.stats-section').scrollIntoView({
            behavior: 'smooth'
        });
    });

    // Interactivity for methodology cards
    const methodologyCards = document.querySelectorAll('.methodology-card');
    if (methodologyCards) {
        methodologyCards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-10px) scale(1.02)';
            });

            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
        });
    }
}

// Run initialization when DOM is ready
document.addEventListener('DOMContentLoaded', initializeApp);
