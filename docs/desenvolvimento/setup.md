# Setup de Desenvolvimento

## Ambiente de Desenvolvimento

### 1. Clone o Repositorio

```bash
git clone https://github.com/franklinbaldo/sites_prefeituras.git
cd sites_prefeituras
```

### 2. Instalacao com UV

```bash
# Instalar todas as dependencias (incluindo dev)
uv sync

# Verificar instalacao
uv run sites-prefeituras --help
```

### 3. Configuracao do Ambiente

```bash
# Configurar API key
export PSI_KEY="sua_chave_api"
# ou
export PAGESPEED_API_KEY="sua_chave_api"
```

## Estrutura do Projeto

```
sites_prefeituras/
├── src/
│   └── sites_prefeituras/
│       ├── __init__.py
│       ├── cli.py           # Interface CLI (Typer + Rich)
│       ├── collector.py     # Coletor async (httpx + tenacity)
│       ├── models.py        # Modelos Pydantic
│       └── storage.py       # Armazenamento DuckDB
├── tests/
│   ├── features/            # Features BDD (Gherkin PT-BR)
│   │   ├── parallel_chunks.feature
│   │   ├── aggregated_metrics.feature
│   │   ├── api_mock.feature
│   │   └── quarantine.feature
│   ├── step_defs/           # Step definitions
│   │   └── test_*.py
│   ├── conftest.py          # Fixtures compartilhadas
│   └── test_*.py            # Testes unitarios
├── docs/                    # Documentacao MkDocs + Dashboard
│   ├── data/                # JSONs do dashboard
│   ├── js/script.js         # Dashboard JavaScript
│   └── styles.css           # Estilos
├── pyproject.toml           # Configuracao Python
└── mkdocs.yml               # Configuracao docs
```

## Comandos de Desenvolvimento

### Executar Testes

```bash
# Todos os testes (incluindo BDD)
uv run pytest

# Apenas testes BDD
uv run pytest tests/step_defs/

# Com cobertura
uv run pytest --cov=sites_prefeituras

# Testes especificos
uv run pytest tests/test_cli.py -v

# Verbose com output
uv run pytest -v -s
```

### Qualidade de Codigo

```bash
# Linting com Ruff
uv run ruff check src/ tests/

# Formatacao
uv run ruff format src/ tests/

# Type checking
uv run mypy src/
```

### Documentacao

```bash
# Servir localmente
uv run mkdocs serve

# Build para producao
uv run mkdocs build

# Deploy (GitHub Pages)
uv run mkdocs gh-deploy
```

### CLI Development

```bash
# Testar comandos durante desenvolvimento
uv run sites-prefeituras audit https://example.com

# Ver todos os comandos
uv run sites-prefeituras --help

# Testar metricas
uv run sites-prefeituras metrics --worst 10

# Testar quarentena
uv run sites-prefeituras quarantine

# Exportar dashboard
uv run sites-prefeituras export-dashboard
```

## Desenvolvimento BDD

O projeto usa pytest-bdd para testes comportamentais em portugues.

### Estrutura de Features

```
tests/features/
├── parallel_chunks.feature      # Processamento paralelo
├── aggregated_metrics.feature   # Metricas agregadas
├── api_mock.feature             # Mocks de API
└── quarantine.feature           # Sistema de quarentena
```

### Exemplo de Feature

```gherkin
# language: pt
Funcionalidade: Sistema de quarentena

  Cenario: Identificar sites com falhas persistentes
    Dado um banco de dados com sites que falharam por 3 dias
    Quando o sistema atualiza a quarentena
    Entao os sites devem ser marcados como quarentenados
```

### Criar Nova Feature

1. Crie o arquivo `.feature` em `tests/features/`
2. Crie os step definitions em `tests/step_defs/test_<feature>.py`
3. Use as fixtures de `conftest.py`

## Workflow de Desenvolvimento

### 1. Criar Feature Branch

```bash
git checkout -b feature/nova-funcionalidade
```

### 2. Desenvolvimento BDD

```bash
# 1. Escrever feature primeiro
# tests/features/nova_feature.feature

# 2. Criar step definitions
# tests/step_defs/test_nova_feature.py

# 3. Implementar funcionalidade
# src/sites_prefeituras/...

# 4. Rodar testes
uv run pytest tests/step_defs/test_nova_feature.py -v
```

### 3. Verificacoes Finais

```bash
# Executar todos os testes
uv run pytest

# Verificar qualidade
uv run ruff check src/ tests/
uv run mypy src/

# Atualizar documentacao se necessario
uv run mkdocs serve
```

### 4. Commit e Push

```bash
git add .
git commit -m "feat: adiciona nova funcionalidade"
git push origin feature/nova-funcionalidade
```

## Debugging

### VS Code

Configuracao recomendada em `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug CLI",
            "type": "python",
            "request": "launch",
            "module": "sites_prefeituras.cli",
            "args": ["audit", "https://example.com"],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["-v", "-s"],
            "console": "integratedTerminal"
        }
    ]
}
```

### Logs

```python
import logging

# Configurar logging para debug
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
```

## Troubleshooting

### Problemas Comuns

1. **UV nao encontrado**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc
   ```

2. **Dependencias nao instaladas**
   ```bash
   uv sync --reinstall
   ```

3. **Testes falhando**
   ```bash
   uv run pytest -v --tb=long
   ```

4. **API Key nao configurada**
   ```bash
   export PSI_KEY="sua_chave"
   # ou
   export PAGESPEED_API_KEY="sua_chave"
   ```

5. **Banco de dados corrompido**
   ```bash
   rm data/sites_prefeituras.duckdb
   # O banco sera recriado automaticamente
   ```

6. **Mocks nao funcionando**
   ```bash
   # Verificar se respx esta instalado
   uv run python -c "import respx; print('OK')"
   ```
