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
                        <div class="stat-number" data-count="5570">0</div>
                        <div class="stat-label">Municípios</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" data-count="2847">0</div>
                        <div class="stat-label">Sites Analisados</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" data-count="34">0</div>
                        <div class="stat-label">% Conformes WCAG</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" data-count="7.2">0</div>
                        <div class="stat-label">Nota Média</div>
                    </div>
                </div>
            </div>
        </section>

        <section class="ranking-section">
            <div class="container">
                <h2>Ranking das Melhores Prefeituras</h2>
                <div class="ranking-controls">
                    <select id="stateFilter" class="filter-select">
                        <option value="">Todos os Estados</option>
                        <option value="SP">São Paulo</option>
                        <option value="RJ">Rio de Janeiro</option>
                        <option value="MG">Minas Gerais</option>
                        <option value="RS">Rio Grande do Sul</option>
                        <option value="PR">Paraná</option>
                    </select>
                    <select id="populationFilter" class="filter-select">
                        <option value="">Todos os Tamanhos</option>
                        <option value="big">Grandes (>500k)</option>
                        <option value="medium">Médias (100k-500k)</option>
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
                        <h3>WCAG 2.1</h3>
                        <p>Análise baseada nas diretrizes internacionais de acessibilidade web</p>
                    </div>
                    <div class="methodology-card">
                        <div class="methodology-icon">🤖</div>
                        <h3>Testes Automatizados</h3>
                        <p>Ferramentas como axe-core e Lighthouse para análise técnica</p>
                    </div>
                    <div class="methodology-card">
                        <div class="methodology-icon">👥</div>
                        <h3>Avaliação Manual</h3>
                        <p>Testes com usuários reais e especialistas em acessibilidade</p>
                    </div>
                    <div class="methodology-card">
                        <div class="methodology-icon">📱</div>
                        <h3>Responsividade</h3>
                        <p>Compatibilidade com diferentes dispositivos e tecnologias assistivas</p>
                    </div>
                </div>
            </div>
        </section>
    </main>

    <footer class="footer">
        <div class="container">
            <p>&copy; 2024 Acessibilidade Municipal. Contribuindo para um Brasil digital mais inclusivo.</p>
        </div>
    </footer>

    <script src="script.js"></script>
</body>
</html>