# 🛠️ Setup de Desenvolvimento

## Ambiente de Desenvolvimento

### 1. Clone e Branch

```bash
git clone https://github.com/franklinbaldo/sites_prefeituras.git
cd sites_prefeituras
git checkout python-migration
```

### 2. Instalação com UV

```bash
# Instalar todas as dependências (incluindo dev)
uv sync

# Verificar instalação
uv run sites-prefeituras --help
```

### 3. Configuração do Ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar variáveis necessárias
export PAGESPEED_API_KEY="sua_chave_api"
export DEBUG=true
```

## Estrutura do Projeto

```
sites_prefeituras/
├── src/
│   └── sites_prefeituras/
│       ├── __init__.py
│       ├── cli.py           # Interface CLI
│       ├── collector.py     # Coleta de dados
│       ├── models.py        # Modelos Pydantic
│       ├── storage.py       # Armazenamento DuckDB
│       └── web.py           # Interface web
├── tests/
│   ├── test_cli.py         # Testes CLI
│   ├── test_collector.py   # Testes coleta
│   └── test_e2e.py         # Testes E2E
├── docs/                   # Documentação MkDocs
├── pyproject.toml         # Configuração Python
└── mkdocs.yml            # Configuração docs
```

## Comandos de Desenvolvimento

### Executar Testes

```bash
# Todos os testes
uv run pytest

# Apenas testes E2E
uv run pytest -m e2e

# Com cobertura
uv run pytest --cov=sites_prefeituras

# Testes específicos
uv run pytest tests/test_cli.py -v
```

### Qualidade de Código

```bash
# Linting com Ruff
uv run ruff check src/ tests/

# Formatação
uv run ruff format src/ tests/

# Type checking
uv run mypy src/
```

### Documentação

```bash
# Servir localmente
uv run mkdocs serve

# Build para produção
uv run mkdocs build

# Deploy (GitHub Pages)
uv run mkdocs gh-deploy
```

### CLI Development

```bash
# Testar comandos durante desenvolvimento
uv run sites-prefeituras audit https://example.com

# Debug mode
uv run sites-prefeituras --debug audit https://example.com
```

## Workflow de Desenvolvimento

### 1. Criar Feature Branch

```bash
git checkout -b feature/nova-funcionalidade
```

### 2. Desenvolvimento TDD

```bash
# 1. Escrever teste E2E primeiro
uv run pytest tests/test_nova_funcionalidade.py -v

# 2. Implementar funcionalidade
# 3. Executar testes novamente
uv run pytest tests/test_nova_funcionalidade.py -v

# 4. Refatorar se necessário
```

### 3. Verificações Finais

```bash
# Executar todos os testes
uv run pytest

# Verificar qualidade
uv run ruff check src/ tests/
uv run mypy src/

# Atualizar documentação se necessário
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

Configuração recomendada em `.vscode/launch.json`:

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

1. **UV não encontrado**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc
   ```

2. **Dependências não instaladas**
   ```bash
   uv sync --reinstall
   ```

3. **Testes falhando**
   ```bash
   uv run pytest -v --tb=long
   ```

4. **API Key não configurada**
   ```bash
   export PAGESPEED_API_KEY="sua_chave"
   ```