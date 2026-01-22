<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acessibilidade Municipal - Comparador de Sites de Prefeituras</title>
    <link href="https://unpkg.com/tabulator-tables@5.5.4/dist/css/tabulator.min.css" rel="stylesheet">
    <script type="text/javascript" src="https://unpkg.com/tabulator-tables@5.5.4/dist/js/tabulator.min.js"></script>
    <link rel="stylesheet" href="styles.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cal+Sans:wght@400;600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
</head>
<body>
    <header class="hero">
        <div class="hero-content">
            <h1 class="hero-title">Acessibilidade Municipal</h1>
            <p class="hero-subtitle">Compare a acessibilidade digital dos sites de prefeituras brasileiras</p>
            <div class="search-container">
                <input type="text" id="citySearch" placeholder="Digite o nome da cidade ou estado..." class="search-input">
                <button class="search-btn" onclick="searchCity()">Buscar</button>
            </div>
        </div>
        <div class="scroll-indicator">
            <div class="scroll-arrow"></div>
        </div>
    </header>

    <main class="main-content">
        <section class="stats-section">
            <div class="container">
                <h2>Panorama Nacional</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number" data-stat="total" data-count="0">0</div>
                        <div class="stat-label">Sites Analisados</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" data-stat="avg-accessibility" data-count="0">0</div>
                        <div class="stat-label">Acessibilidade Media</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" data-stat="avg-performance" data-count="0">0</div>
                        <div class="stat-label">Performance Media</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="lastUpdated">-</div>
                        <div class="stat-label">Ultima Atualizacao</div>
                    </div>
                </div>
            </div>
        </section>

        <section class="ranking-section">
            <div class="container">
                <h2>Ranking de Acessibilidade</h2>
                <div class="ranking-controls">
                    <select id="stateFilter" class="filter-select">
                        <option value="">Todos os Estados</option>
                    </select>
                    <select id="populationFilter" class="filter-select">
                        <option value="">Todos os Tamanhos</option>
                        <option value="big">Grandes (>500k)</option>
                        <option value="medium">Medias (100k-500k)</option>
                        <option value="small">Pequenas (<100k)</option>
                    </select>
                </div>
                <div id="ranking-table"></div>
            </div>
        </section>

        <section class="methodology-section">
            <div class="container">
                <h2>Metodologia</h2>
                <div class="methodology-grid">
                    <div class="methodology-card">
                        <div class="methodology-icon">🎯</div>
                        <h3>PageSpeed Insights</h3>
                        <p>Analise automatizada usando a API do Google PageSpeed Insights</p>
                    </div>
                    <div class="methodology-card">
                        <div class="methodology-icon">🤖</div>
                        <h3>Coleta Diaria</h3>
                        <p>Dados atualizados automaticamente via GitHub Actions</p>
                    </div>
                    <div class="methodology-card">
                        <div class="methodology-icon">📊</div>
                        <h3>Metricas WCAG</h3>
                        <p>Scores de acessibilidade, performance, SEO e boas praticas</p>
                    </div>
                    <div class="methodology-card">
                        <div class="methodology-icon">📱</div>
                        <h3>Mobile First</h3>
                        <p>Foco em dispositivos moveis, onde a maioria acessa</p>
                    </div>
                </div>
            </div>
        </section>
    </main>

    <footer class="footer">
        <div class="container">
            <p>&copy; 2024 Acessibilidade Municipal. Dados coletados com PageSpeed Insights.</p>
            <p>
                <a href="https://github.com/franklinbaldo/sites_prefeituras">GitHub</a> |
                <a href="https://archive.org/details/psi_brazilian_city_audits">Internet Archive</a>
            </p>
        </div>
    </footer>

    <script src="js/script.js"></script>
</body>
</html>
