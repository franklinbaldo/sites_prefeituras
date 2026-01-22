# Auditoria de Sites de Prefeituras Brasileiras

[![CI](https://github.com/franklinbaldo/sites_prefeituras/actions/workflows/ci.yml/badge.svg)](https://github.com/franklinbaldo/sites_prefeituras/actions/workflows/ci.yml)
[![Coleta PSI](https://github.com/franklinbaldo/sites_prefeituras/actions/workflows/collect-psi.yml/badge.svg)](https://github.com/franklinbaldo/sites_prefeituras/actions/workflows/collect-psi.yml)

Sistema automatizado de auditoria de sites de prefeituras brasileiras usando Google PageSpeed Insights (PSI). Coleta metricas de desempenho, acessibilidade, SEO e melhores praticas para os 5.570 municipios do Brasil.

## Arquitetura

```
CSV (5570 municipios)
        |
        v
[CLI Python] --async--> [PageSpeed Insights API]
        |                     (3.5 req/s)
        v
[DuckDB] --> [JSON estatico] --> [Internet Archive]
        |
        v
[MkDocs + Tabulator.js] --> Dashboard Web
```

### Componentes

| Componente | Tecnologia | Descricao |
|------------|------------|-----------|
| Coletor | Python + httpx + tenacity | Requisicoes async com rate limiting e retry |
| Storage | DuckDB | Banco de dados local otimizado para analytics |
| CLI | Typer + Rich | Interface de linha de comando completa |
| Dashboard | JSON estatico + Tabulator.js | Visualizacao web leve e rapida |
| Docs | MkDocs Material | Documentacao |
| CI/CD | GitHub Actions | Coleta diaria automatizada |
| Testes | pytest-bdd | Testes BDD em portugues |

## Inicio Rapido

### Pre-requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes)
- Chave da API [PageSpeed Insights](https://developers.google.com/speed/docs/insights/v5/get-started)

### Instalacao

```bash
# Clonar repositorio
git clone https://github.com/franklinbaldo/sites_prefeituras.git
cd sites_prefeituras

# Instalar dependencias
uv sync

# Configurar API key (aceita ambos os nomes)
export PSI_KEY="sua_chave_aqui"
# ou
export PAGESPEED_API_KEY="sua_chave_aqui"
```

## Uso da CLI

### Comandos Principais

```bash
# Auditar um site individual
uv run sites-prefeituras audit https://www.prefeitura.sp.gov.br

# Auditoria em lote (otimizada)
uv run sites-prefeituras batch sites_das_prefeituras_brasileiras.csv \
  --max-concurrent 10 \
  --requests-per-second 3.5 \
  --skip-recent 24  # Pula sites auditados nas ultimas 24h

# Ver estatisticas do banco
uv run sites-prefeituras stats
```

### Metricas e Relatorios

```bash
# Metricas agregadas
uv run sites-prefeituras metrics

# Metricas por estado
uv run sites-prefeituras metrics --by-state

# Top 10 piores sites (performance)
uv run sites-prefeituras metrics --worst 10

# Top 10 melhores sites (acessibilidade)
uv run sites-prefeituras metrics --best 10

# Exportar metricas para JSON
uv run sites-prefeituras metrics --export metricas.json
```

### Sistema de Quarentena

Sites com falhas persistentes (3+ dias) sao automaticamente quarentenados:

```bash
# Listar sites em quarentena
uv run sites-prefeituras quarantine

# Atualizar lista de quarentena
uv run sites-prefeituras quarantine --update

# Exportar quarentena para JSON/CSV
uv run sites-prefeituras quarantine --export-json quarantine.json
uv run sites-prefeituras quarantine --export-csv quarantine.csv

# Alterar status de um site
uv run sites-prefeituras quarantine --url "https://site.gov.br" --set-status investigating
```

### Exportar Dashboard

```bash
# Gerar JSONs estaticos para o dashboard
uv run sites-prefeituras export-dashboard --output-dir docs/data
```

Gera os seguintes arquivos:
- `summary.json` - Metricas agregadas
- `ranking.json` - Ranking completo de sites
- `top50.json` - Melhores 50 sites
- `worst50.json` - Piores 50 sites
- `by-state.json` - Metricas por estado
- `quarantine.json` - Sites em quarentena

## GitHub Actions

O projeto possui 3 workflows automatizados:

### Coleta PSI (`collect-psi.yml`)

Executa diariamente as 03:00 UTC:
- Coleta incremental (pula sites auditados nas ultimas 24h)
- Rate limit otimizado: 3.5 req/s
- Atualiza lista de quarentena
- Gera JSONs estaticos para dashboard
- Upload para Internet Archive
- Commit automatico dos resultados

**Execucao manual:** Actions > "Coleta PSI" > Run workflow

Parametros configureaveis:
- `max_concurrent`: Requisicoes simultaneas (default: 10)
- `requests_per_second`: Taxa de requisicoes (default: 3.5, max: 4.0)
- `skip_recent_hours`: Pular sites recentes (default: 24, 0=todos)

### CI (`ci.yml`)

Executa em PRs e pushes:
- Lint com ruff
- Type checking com mypy
- Testes BDD com pytest-bdd + coverage
- Build da documentacao

### Docs (`docs.yml`)

Deploy automatico da documentacao para GitHub Pages.

## Configuracao de Secrets

Configure os seguintes secrets no GitHub (Settings > Secrets > Actions):

| Secret | Obrigatorio | Descricao |
|--------|-------------|-----------|
| `PSI_KEY` | Sim | Google PageSpeed Insights API Key |
| `IA_ACCESS_KEY` | Nao | Internet Archive access key |
| `IA_SECRET_KEY` | Nao | Internet Archive secret key |

### Limites da API PSI

- 25.000 requisicoes/dia
- 400 requisicoes/100 segundos (4 req/s)
- Usamos 3.5 req/s para margem de seguranca

### Obtendo a PSI API Key

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto ou selecione existente
3. Ative a "PageSpeed Insights API"
4. Crie uma credencial (API Key)
5. Configure no GitHub como secret `PSI_KEY`

## Estrutura do Projeto

```
sites_prefeituras/
├── src/sites_prefeituras/       # Codigo principal
│   ├── cli.py                   # Interface de linha de comando
│   ├── collector.py             # Coletor async PSI
│   ├── models.py                # Modelos Pydantic
│   └── storage.py               # Camada DuckDB + exports
├── tests/                       # Testes
│   ├── features/                # Features BDD (Gherkin PT-BR)
│   │   ├── parallel_chunks.feature
│   │   ├── aggregated_metrics.feature
│   │   ├── api_mock.feature
│   │   └── quarantine.feature
│   ├── step_defs/               # Implementacao dos steps
│   └── conftest.py              # Fixtures compartilhadas
├── docs/                        # Documentacao MkDocs + Dashboard
│   ├── data/                    # JSONs do dashboard
│   ├── js/script.js             # Dashboard JavaScript
│   └── styles.css               # Estilos do dashboard
├── data/                        # Dados coletados
│   ├── sites_prefeituras.duckdb # Banco de dados
│   ├── output/                  # Exports Parquet/JSON
│   └── quarantine/              # Listas de quarentena
├── .github/workflows/           # GitHub Actions
│   ├── ci.yml                   # Testes e lint
│   ├── collect-psi.yml          # Coleta diaria
│   └── docs.yml                 # Deploy docs
└── sites_das_prefeituras_brasileiras.csv  # Lista de sites
```

## Desenvolvimento

### Setup

```bash
# Instalar dependencias
uv sync

# Rodar testes BDD
uv run pytest

# Rodar testes com coverage
uv run pytest --cov=sites_prefeituras

# Lint
uv run ruff check src/

# Type check
uv run mypy src/

# Documentacao local
uv run mkdocs serve
```

### Testes BDD

Os testes usam pytest-bdd com features escritas em portugues:

```gherkin
# tests/features/quarantine.feature
Funcionalidade: Sistema de quarentena

  Cenario: Identificar sites com falhas persistentes
    Dado um banco de dados com sites que falharam por 3 dias consecutivos
    Quando o sistema atualiza a quarentena
    Entao os sites com falhas persistentes devem ser quarentenados
```

## Dados

### Fonte

Lista de 5.570 municipios brasileiros em `sites_das_prefeituras_brasileiras.csv`.

### Metricas Coletadas

Para cada site (mobile e desktop):
- **Performance**: FCP, LCP, CLS, TBT, Speed Index
- **Accessibility**: Score de acessibilidade (0-100)
- **SEO**: Score de otimizacao para buscadores
- **Best Practices**: Score de boas praticas

### Acesso aos Dados

Os dados sao arquivados no [Internet Archive](https://archive.org/details/psi_brazilian_city_audits):
- JSONs do dashboard atualizados diariamente
- Listas de quarentena versionadas por data
- Historico completo de auditorias

## Contribuicoes

Contribuicoes sao bem-vindas! Por favor:

1. Fork o repositorio
2. Crie uma branch (`git checkout -b feature/minha-feature`)
3. Escreva testes BDD para a funcionalidade
4. Commit suas alteracoes (`git commit -m 'Add feature'`)
5. Push para a branch (`git push origin feature/minha-feature`)
6. Abra um Pull Request

## Licenca

Este projeto esta sob a licenca MIT.
