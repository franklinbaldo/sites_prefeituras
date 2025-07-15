# 📦 Instalação

## Pré-requisitos

- **Python 3.11+** - Versão mínima suportada
- **UV** - Gerenciador de pacotes recomendado (10-100x mais rápido que pip)
- **Git** - Para clonar o repositório

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
git checkout python-migration  # Branch da migração Python
```

## Instalação com UV (Recomendado)

```bash
# Instalar dependências
uv sync

# Verificar instalação
uv run sites-prefeituras --help
```

## Instalação com pip (Alternativa)

```bash
# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# ou
.venv\Scripts\activate     # Windows

# Instalar projeto
pip install -e .

# Verificar instalação
sites-prefeituras --help
```

## Configuração da API

Para usar a API do PageSpeed Insights, você precisa de uma chave:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto ou selecione um existente
3. Ative a API PageSpeed Insights
4. Crie uma chave de API
5. Configure a variável de ambiente:

```bash
export PAGESPEED_API_KEY="sua_chave_aqui"
```

## Verificação da Instalação

```bash
# Testar CLI
uv run sites-prefeituras --version

# Executar testes
uv run pytest

# Servir documentação
uv run mkdocs serve
```

!!! success "Pronto!"
    Agora você pode começar a usar o Sites Prefeituras! 🎉