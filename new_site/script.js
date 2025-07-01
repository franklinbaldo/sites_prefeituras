// Sample data for Brazilian municipalities
const municipalityData = [
    { name: "São Paulo", state: "SP", population: "big", score: 8.7, rank: 1 },
    { name: "Curitiba", state: "PR", population: "big", score: 8.5, rank: 2 },
    { name: "Florianópolis", state: "SC", population: "medium", score: 8.3, rank: 3 },
    { name: "Porto Alegre", state: "RS", population: "big", score: 8.1, rank: 4 },
    { name: "Belo Horizonte", state: "MG", population: "big", score: 7.9, rank: 5 },
    { name: "Campinas", state: "SP", population: "big", score: 7.8, rank: 6 },
    { name: "Rio de Janeiro", state: "RJ", population: "big", score: 7.6, rank: 7 },
    { name: "Brasília", state: "DF", population: "big", score: 7.4, rank: 8 },
    { name: "Joinville", state: "SC", population: "medium", score: 7.3, rank: 9 },
    { name: "Santos", state: "SP", population: "medium", score: 7.2, rank: 10 },
    { name: "Nova Lima", state: "MG", population: "small", score: 7.1, rank: 11 },
    { name: "Vitória", state: "ES", population: "medium", score: 7.0, rank: 12 },
    { name: "Niterói", state: "RJ", population: "medium", score: 6.9, rank: 13 },
    { name: "Sorocaba", state: "SP", population: "big", score: 6.8, rank: 14 },
    { name: "Londrina", state: "PR", population: "big", score: 6.7, rank: 15 }
];

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

// Get score class for styling
function getScoreClass(score) {
    if (score >= 8) return 'score-excellent';
    if (score >= 6) return 'score-good';
    return 'score-poor';
}

// Get badge class for styling
function getBadgeClass(score) {
    if (score >= 8) return 'badge-excellent';
    if (score >= 6) return 'badge-good';
    return 'badge-poor';
}

// Get badge text
function getBadgeText(score) {
    if (score >= 8) return 'Excelente';
    if (score >= 6) return 'Bom';
    return 'Precisa Melhorar';
}

// Render ranking list
function renderRanking(data = municipalityData) {
    const rankingList = document.getElementById('rankingList');
    
    rankingList.innerHTML = data.map(city => `
        <div class="ranking-item">
            <div class="ranking-position">${city.rank}°</div>
            <div class="ranking-city">
                <div class="city-name">${city.name}</div>
                <div class="city-state">${city.state}</div>
            </div>
            <div class="ranking-score ${getScoreClass(city.score)}">${city.score}</div>
            <div class="ranking-badge ${getBadgeClass(city.score)}">${getBadgeText(city.score)}</div>
        </div>
    `).join('');
}

// Filter functionality
function setupFilters() {
    const stateFilter = document.getElementById('stateFilter');
    const populationFilter = document.getElementById('populationFilter');
    
    function applyFilters() {
        let filteredData = municipalityData;
        
        if (stateFilter.value) {
            filteredData = filteredData.filter(city => city.state === stateFilter.value);
        }
        
        if (populationFilter.value) {
            filteredData = filteredData.filter(city => city.population === populationFilter.value);
        }
        
        renderRanking(filteredData);
    }
    
    stateFilter.addEventListener('change', applyFilters);
    populationFilter.addEventListener('change', applyFilters);
}

// Search functionality
function searchCity() {
    const searchInput = document.getElementById('citySearch');
    const searchTerm = searchInput.value.toLowerCase().trim();
    
    if (!searchTerm) {
        renderRanking();
        return;
    }
    
    const filteredData = municipalityData.filter(city => 
        city.name.toLowerCase().includes(searchTerm) || 
        city.state.toLowerCase().includes(searchTerm)
    );
    
    renderRanking(filteredData);
    
    // Scroll to results
    document.querySelector('.ranking-section').scrollIntoView({ 
        behavior: 'smooth' 
    });
}

// Add search on Enter key
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('citySearch');
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchCity();
        }
    });
    
    // Initialize components
    initStatsAnimation();
    renderRanking();
    setupFilters();
    
    // Smooth scrolling for scroll indicator
    document.querySelector('.scroll-indicator').addEventListener('click', function() {
        document.querySelector('.stats-section').scrollIntoView({ 
            behavior: 'smooth' 
        });
    });
});

// Add some interactivity to methodology cards
document.addEventListener('DOMContentLoaded', function() {
    const methodologyCards = document.querySelectorAll('.methodology-card');
    
    methodologyCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
});

