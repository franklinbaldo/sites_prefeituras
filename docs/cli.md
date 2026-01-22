# Interface de Linha de Comando (CLI)

O Sites Prefeituras oferece uma CLI completa para coleta, analise e exportacao de dados.

## Instalacao

```bash
# Instalar dependencias
uv sync

# Verificar instalacao
uv run sites-prefeituras --help
```

## Comandos Disponiveis

### audit

Audita um site individual.

```bash
uv run sites-prefeituras audit <URL> [OPCOES]
```

**Opcoes:**
- `--output`: Formato de saida (`console` ou `json`)
- `--no-save-to-db`: Nao salvar no banco de dados

**Exemplo:**
```bash
uv run sites-prefeituras audit https://www.prefeitura.sp.gov.br --output json
```

---

### batch

Executa auditoria em lote a partir de um arquivo CSV.

```bash
uv run sites-prefeituras batch <CSV_FILE> [OPCOES]
```

**Opcoes:**
- `--output-dir`: Diretorio de saida (default: `./output`)
- `--max-concurrent`: Maximo de requisicoes simultaneas (default: 10)
- `--requests-per-second`: Taxa de requisicoes por segundo (default: 3.5, max: 4.0)
- `--url-column`: Nome da coluna com URLs (default: `url`)
- `--skip-recent`: Pular sites auditados nas ultimas N horas (default: 24, 0=desativado)
- `--export-parquet / --no-export-parquet`: Exportar para Parquet
- `--export-json / --no-export-json`: Exportar para JSON

**Exemplo:**
```bash
# Coleta completa
uv run sites-prefeituras batch sites_das_prefeituras_brasileiras.csv \
  --max-concurrent 10 \
  --requests-per-second 3.5

# Coleta incremental (pula sites recentes)
uv run sites-prefeituras batch sites_das_prefeituras_brasileiras.csv \
  --skip-recent 24
```

---

### stats

Mostra estatisticas dos dados coletados.

```bash
uv run sites-prefeituras stats [OPCOES]
```

**Opcoes:**
- `--db-path`: Caminho do banco de dados

**Exemplo:**
```bash
uv run sites-prefeituras stats --db-path ./data/sites_prefeituras.duckdb
```

---

### metrics

Mostra metricas agregadas das auditorias.

```bash
uv run sites-prefeituras metrics [OPCOES]
```

**Opcoes:**
- `--db-path`: Caminho do banco de dados
- `--by-state`: Agrupar metricas por estado
- `--worst N`: Mostrar N piores sites em performance
- `--best N`: Mostrar N melhores sites em acessibilidade
- `--export FILE`: Exportar metricas para arquivo JSON

**Exemplos:**
```bash
# Metricas gerais
uv run sites-prefeituras metrics

# Por estado
uv run sites-prefeituras metrics --by-state

# Top 20 piores em performance
uv run sites-prefeituras metrics --worst 20

# Top 20 melhores em acessibilidade
uv run sites-prefeituras metrics --best 20

# Exportar para JSON
uv run sites-prefeituras metrics --export metricas.json
```

---

### quarantine

Gerencia sites em quarentena (sites com falhas persistentes).

```bash
uv run sites-prefeituras quarantine [OPCOES]
```

**Opcoes:**
- `--db-path`: Caminho do banco de dados
- `--update`: Atualizar lista de quarentena
- `--min-days N`: Minimo de dias com falha para quarentena (default: 3)
- `--status STATUS`: Filtrar por status
- `--url URL`: URL para operacoes especificas
- `--set-status STATUS`: Definir status de uma URL
- `--remove`: Remover URL da quarentena
- `--export-json FILE`: Exportar para JSON
- `--export-csv FILE`: Exportar para CSV

**Status disponiveis:**
- `quarantined`: Em quarentena (default)
- `investigating`: Em investigacao
- `resolved`: Resolvido
- `wrong_url`: URL incorreta

**Exemplos:**
```bash
# Listar todos em quarentena
uv run sites-prefeituras quarantine

# Atualizar quarentena (identifica novos sites com falhas)
uv run sites-prefeituras quarantine --update --min-days 3

# Filtrar por status
uv run sites-prefeituras quarantine --status investigating

# Alterar status de um site
uv run sites-prefeituras quarantine --url "https://site.gov.br" --set-status investigating

# Remover da quarentena
uv run sites-prefeituras quarantine --url "https://site.gov.br" --remove

# Exportar
uv run sites-prefeituras quarantine --export-json quarantine.json
uv run sites-prefeituras quarantine --export-csv quarantine.csv
```

---

### export-dashboard

Exporta JSONs estaticos para o dashboard web.

```bash
uv run sites-prefeituras export-dashboard [OPCOES]
```

**Opcoes:**
- `--db-path`: Caminho do banco de dados
- `--output-dir`: Diretorio de saida (default: `./docs/data`)

**Arquivos gerados:**
- `summary.json` - Metricas agregadas
- `ranking.json` - Ranking completo de sites
- `top50.json` - Melhores 50 sites (acessibilidade)
- `worst50.json` - Piores 50 sites (acessibilidade)
- `by-state.json` - Metricas agrupadas por estado
- `quarantine.json` - Sites em quarentena

**Exemplo:**
```bash
uv run sites-prefeituras export-dashboard --output-dir docs/data
```

---

### cleanup

Remove arquivos legados (JavaScript/Node.js).

```bash
uv run sites-prefeituras cleanup [OPCOES]
```

**Opcoes:**
- `--remove-js`: Remove arquivos JavaScript
- `--remove-node-modules`: Remove node_modules
- `--confirm`: Confirma remocao sem perguntar

**Exemplo:**
```bash
uv run sites-prefeituras cleanup --remove-js --remove-node-modules --confirm
```

---

### serve

Inicia servidor de visualizacao (em desenvolvimento).

```bash
uv run sites-prefeituras serve [OPCOES]
```

**Nota:** Para visualizacao, use o MkDocs:
```bash
uv run mkdocs serve
```

## Variaveis de Ambiente

| Variavel | Descricao |
|----------|-----------|
| `PAGESPEED_API_KEY` | Chave da API PageSpeed Insights |
| `PSI_KEY` | Alias para PAGESPEED_API_KEY |

Ambas as variaveis sao aceitas para compatibilidade.

## Exemplos de Uso

### Fluxo Completo de Coleta

```bash
# 1. Configurar API key
export PSI_KEY="sua_chave_aqui"

# 2. Executar coleta incremental
uv run sites-prefeituras batch sites_das_prefeituras_brasileiras.csv \
  --skip-recent 24 \
  --requests-per-second 3.5

# 3. Ver estatisticas
uv run sites-prefeituras stats

# 4. Atualizar quarentena
uv run sites-prefeituras quarantine --update

# 5. Exportar para dashboard
uv run sites-prefeituras export-dashboard

# 6. Visualizar
uv run mkdocs serve
```

### Analise de Dados

```bash
# Ver metricas gerais
uv run sites-prefeituras metrics

# Ranking por estado
uv run sites-prefeituras metrics --by-state

# Sites que precisam de atencao
uv run sites-prefeituras metrics --worst 50

# Sites em quarentena
uv run sites-prefeituras quarantine
```
