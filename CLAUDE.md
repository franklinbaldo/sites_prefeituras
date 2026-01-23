# CLAUDE.md - Guia para Assistentes de IA

Este arquivo fornece contexto para assistentes de IA trabalhando neste projeto.

## Visao Geral do Projeto

**Sites Prefeituras** e um sistema automatizado de auditoria de sites de prefeituras brasileiras usando Google PageSpeed Insights (PSI). Coleta metricas de desempenho, acessibilidade, SEO e melhores praticas para os 5.570 municipios do Brasil.

## Stack Tecnologico

- **Linguagem**: Python 3.11+ (100% Python, sem Node.js)
- **Gerenciador de Pacotes**: uv (astral.sh/uv)
- **CLI**: Typer + Rich
- **HTTP Client**: httpx + tenacity (async com retry)
- **Banco de Dados**: DuckDB
- **Testes**: pytest-bdd (BDD em portugues)
- **Mocks**: respx
- **Documentacao**: MkDocs Material
- **CI/CD**: GitHub Actions

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
│   ├── step_defs/               # Step definitions
│   └── conftest.py              # Fixtures compartilhadas
├── docs/                        # Documentacao + Dashboard
│   ├── data/                    # JSONs estaticos do dashboard
│   ├── js/script.js             # Dashboard JavaScript
│   └── index.md                 # HTML do dashboard
├── .github/workflows/           # GitHub Actions
│   ├── ci.yml                   # Testes e lint
│   ├── collect-psi.yml          # Coleta diaria
│   └── docs.yml                 # Deploy docs
└── data/                        # Dados coletados
    ├── sites_prefeituras.duckdb # Banco de dados
    └── quarantine/              # Listas de quarentena
```

## Comandos Principais

```bash
# Instalar dependencias
uv sync

# Rodar testes
uv run pytest

# CLI
uv run sites-prefeituras --help
uv run sites-prefeituras audit <URL>
uv run sites-prefeituras batch <CSV>
uv run sites-prefeituras metrics
uv run sites-prefeituras quarantine
uv run sites-prefeituras export-dashboard
```

## Conceitos Importantes

### Sistema de Quarentena

Sites com falhas persistentes (3+ falhas no periodo de lookback) sao automaticamente quarentenados. Status possiveis:
- `quarantined`: Em quarentena, sera pulado na coleta
- `investigating`: Em investigacao manual
- `resolved`: Problema resolvido
- `wrong_url`: URL incorreta na lista original

### Coleta Incremental

A coleta usa `--skip-recent` para pular sites auditados nas ultimas N horas. Isso otimiza o tempo de execucao do workflow diario.

### Dashboard

O dashboard usa JSON estatico (nao mais DuckDB WASM). Os arquivos sao gerados pelo comando `export-dashboard`:
- `summary.json` - Metricas agregadas
- `ranking.json` - Ranking completo
- `top50.json` / `worst50.json` - Extremos
- `by-state.json` - Por estado
- `quarantine.json` - Sites em quarentena

### Testes BDD

Os testes usam pytest-bdd com features escritas em portugues:

```gherkin
# language: pt
Funcionalidade: Sistema de quarentena

  Cenario: Identificar sites com falhas persistentes
    Dado um banco com sites que falharam 3 dias seguidos
    Quando o sistema atualiza a quarentena
    Entao esses sites devem ser marcados como quarentenados
```

## Variaveis de Ambiente

| Variavel | Descricao |
|----------|-----------|
| `PSI_KEY` | Google PageSpeed Insights API Key |
| `PAGESPEED_API_KEY` | Alias para PSI_KEY |
| `IA_ACCESS_KEY` | Internet Archive access key |
| `IA_SECRET_KEY` | Internet Archive secret key |

## Limites da API PSI

- 25.000 requisicoes/dia
- 400 requisicoes/100 segundos (4 req/s)
- Usamos 3.5 req/s para margem de seguranca

## Workflows GitHub Actions

### collect-psi.yml (Diario 03:00 UTC)
1. Restaura cache do DuckDB
2. Executa coleta incremental (pula sites recentes)
3. Atualiza lista de quarentena
4. Exporta JSONs para dashboard
5. Upload para Internet Archive
6. Commit e push dos resultados

### ci.yml (PRs e Pushes)
- Lint com ruff
- Type checking com mypy
- Testes BDD com pytest-bdd

## Padroes de Codigo

- Codigo em ingles, documentacao em portugues
- Usar async/await para operacoes I/O
- Modelos Pydantic para validacao
- Testes BDD para funcionalidades principais
- Rate limiting para APIs externas

## Troubleshooting Comum

1. **Testes falhando**: `uv run pytest -v --tb=long`
2. **API Key**: Verificar `PSI_KEY` ou `PAGESPEED_API_KEY`
3. **Banco corrompido**: Deletar `data/sites_prefeituras.duckdb`
4. **Dependencias**: `uv sync --reinstall`

## Links Uteis

- [PageSpeed Insights API](https://developers.google.com/speed/docs/insights/v5/get-started)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [pytest-bdd](https://pytest-bdd.readthedocs.io/)
- [Internet Archive](https://archive.org/details/psi_brazilian_city_audits)
