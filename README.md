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
        |
        v
[DuckDB] --> [Parquet] --> [Internet Archive]
        |
        v
[MkDocs + DuckDB-wasm] --> Visualizacao Web
```

### Componentes

| Componente | Tecnologia | Descricao |
|------------|------------|-----------|
| Coletor | Python + httpx | Requisicoes async com rate limiting |
| Storage | DuckDB | Banco de dados local otimizado para analytics |
| CLI | Typer + Rich | Interface de linha de comando |
| Docs | MkDocs Material | Documentacao e visualizacao |
| CI/CD | GitHub Actions | Coleta diaria automatizada |

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

# Configurar API key
export PSI_KEY="sua_chave_aqui"
```

### Uso

```bash
# Auditar um site
uv run sites-prefeituras audit https://www.prefeitura.sp.gov.br

# Auditoria em lote
uv run sites-prefeituras batch sites_das_prefeituras_brasileiras.csv \
  --max-concurrent 10 \
  --requests-per-second 1.0

# Ver estatisticas
uv run sites-prefeituras stats

# Limpar arquivos legados (se existirem)
uv run sites-prefeituras cleanup --remove-js --confirm
```

## GitHub Actions

O projeto possui 3 workflows automatizados:

### Coleta PSI (`collect-psi.yml`)

Executa diariamente as 03:00 UTC:
- Coleta metricas de todos os sites
- Salva em DuckDB com cache entre execucoes
- Exporta para Parquet e JSON
- Upload para Internet Archive

**Execucao manual:** Actions > "Coleta PSI" > Run workflow

### CI (`ci.yml`)

Executa em PRs e pushes:
- Lint com ruff
- Type checking com mypy
- Testes com pytest + coverage
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

### Obtendo a PSI API Key

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto ou selecione existente
3. Ative a "PageSpeed Insights API"
4. Crie uma credencial (API Key)
5. Configure no GitHub como secret `PSI_KEY`

## Estrutura do Projeto

```
sites_prefeituras/
├── src/sites_prefeituras/    # Codigo principal
│   ├── cli.py                # Interface de linha de comando
│   ├── collector.py          # Coletor async PSI
│   ├── models.py             # Modelos Pydantic
│   └── storage.py            # Camada DuckDB
├── tests/                    # Testes pytest
├── docs/                     # Documentacao MkDocs
├── data/                     # Dados coletados
│   ├── sites_prefeituras.duckdb
│   └── output/               # Exports Parquet/JSON
├── .github/workflows/        # GitHub Actions
│   ├── ci.yml                # Testes e lint
│   ├── collect-psi.yml       # Coleta diaria
│   └── docs.yml              # Deploy docs
└── sites_das_prefeituras_brasileiras.csv  # Lista de sites
```

## Desenvolvimento

```bash
# Instalar dependencias de dev
uv sync

# Rodar testes
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

## Dados

### Fonte

Lista de 5.570 municipios brasileiros em `sites_das_prefeituras_brasileiras.csv`.

### Metricas Coletadas

Para cada site (mobile e desktop):
- **Performance**: FCP, LCP, CLS, TBT, Speed Index
- **Accessibility**: Score de acessibilidade
- **SEO**: Score de otimizacao para buscadores
- **Best Practices**: Score de boas praticas

### Acesso aos Dados

Os dados sao arquivados no [Internet Archive](https://archive.org/details/psi_brazilian_city_audits) em formato Parquet.

## Contribuicoes

Contribuicoes sao bem-vindas! Por favor:

1. Fork o repositorio
2. Crie uma branch (`git checkout -b feature/minha-feature`)
3. Commit suas alteracoes (`git commit -m 'Add feature'`)
4. Push para a branch (`git push origin feature/minha-feature`)
5. Abra um Pull Request

## Licenca

Este projeto esta sob a licenca MIT.
