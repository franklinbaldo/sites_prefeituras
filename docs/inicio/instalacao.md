# Instalacao

## Pre-requisitos

- **Python 3.11+** - Versao minima suportada
- **UV** - Gerenciador de pacotes recomendado (10-100x mais rapido que pip)
- **Git** - Para clonar o repositorio

## Instalando UV

=== "Unix/macOS"
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"
    ```powershell
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

=== "pipx"
    ```bash
    pipx install uv
    ```

## Clonando o Projeto

```bash
git clone https://github.com/franklinbaldo/sites_prefeituras.git
cd sites_prefeituras
```

## Instalacao com UV (Recomendado)

```bash
# Instalar dependencias
uv sync

# Verificar instalacao
uv run sites-prefeituras --help
```

## Instalacao com pip (Alternativa)

```bash
# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate     # Windows

# Instalar projeto
pip install -e .

# Verificar instalacao
sites-prefeituras --help
```

## Configuracao da API

Para usar a API do PageSpeed Insights, voce precisa de uma chave:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto ou selecione um existente
3. Ative a API PageSpeed Insights
4. Crie uma chave de API
5. Configure a variavel de ambiente:

```bash
# Ambos os nomes sao aceitos
export PSI_KEY="sua_chave_aqui"
# ou
export PAGESPEED_API_KEY="sua_chave_aqui"
```

## Verificacao da Instalacao

```bash
# Testar CLI
uv run sites-prefeituras --help

# Ver comandos disponiveis
uv run sites-prefeituras --help

# Executar testes
uv run pytest

# Servir documentacao
uv run mkdocs serve
```

## Comandos Principais

```bash
# Auditar um site
uv run sites-prefeituras audit https://www.prefeitura.sp.gov.br

# Auditoria em lote
uv run sites-prefeituras batch sites_das_prefeituras_brasileiras.csv

# Ver estatisticas
uv run sites-prefeituras stats

# Metricas agregadas
uv run sites-prefeituras metrics

# Gerenciar quarentena
uv run sites-prefeituras quarantine

# Exportar dashboard
uv run sites-prefeituras export-dashboard
```

## Proximos Passos

- Consulte a [documentacao da CLI](../cli.md) para todos os comandos
- Veja a [arquitetura](../arq.md) para entender o sistema
- Configure o [ambiente de desenvolvimento](../desenvolvimento/setup.md)
