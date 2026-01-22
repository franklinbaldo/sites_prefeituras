# Arquitetura

## Visao Geral

O projeto e 100% Python, utilizando uma arquitetura assincrona otimizada para coleta de dados em larga escala.

```
                    ┌─────────────────────────────────────┐
                    │       CSV (5570 municipios)         │
                    └─────────────────┬───────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Python (Typer)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐│
│  │  audit   │ │  batch   │ │ metrics  │ │ quarantine │ export  ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘│
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Coletor Async (httpx + tenacity)              │
│  • Rate limiting: 3.5 req/s                                     │
│  • Retry com backoff exponencial                                │
│  • Processamento em chunks paralelos                            │
│  • Coleta incremental (skip recent)                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PageSpeed Insights API                        │
│  • Limite: 25.000 req/dia, 400 req/100s                         │
│  • Mobile + Desktop por site                                     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DuckDB Storage                           │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────────┐   │
│  │    audits      │ │ audit_summaries│ │   quarantine       │   │
│  │ (raw results)  │ │ (metrics only) │ │ (failed sites)     │   │
│  └────────────────┘ └────────────────┘ └────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│  JSON Estatico   │ │   Parquet    │ │ Internet Archive │
│  (Dashboard)     │ │  (Analytics) │ │   (Backup)       │
└────────┬─────────┘ └──────────────┘ └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Dashboard Web (MkDocs)                        │
│  • Tabulator.js para tabelas interativas                        │
│  • Filtros por estado                                           │
│  • Busca por cidade                                             │
│  • Ranking de acessibilidade                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Componentes

### 1. CLI (cli.py)

Interface de linha de comando usando Typer + Rich.

**Comandos:**
- `audit`: Auditoria individual
- `batch`: Auditoria em lote
- `stats`: Estatisticas do banco
- `metrics`: Metricas agregadas
- `quarantine`: Gerenciamento de quarentena
- `export-dashboard`: Exporta JSONs para dashboard

### 2. Coletor (collector.py)

Coletor assincrono usando httpx + tenacity.

**Caracteristicas:**
- Rate limiting configuravel (default: 3.5 req/s)
- Retry com backoff exponencial
- Coleta Mobile + Desktop simultanea
- Processamento em chunks paralelos
- Suporte a coleta incremental

```python
# Exemplo de configuracao
BatchAuditConfig(
    max_concurrent=10,          # Requisicoes paralelas
    requests_per_second=3.5,    # Rate limit
    skip_recent_hours=24,       # Coleta incremental
)
```

### 3. Storage (storage.py)

Camada de persistencia usando DuckDB.

**Tabelas:**
- `audits`: Resultados completos (JSON)
- `audit_summaries`: Metricas extraidas
- `quarantine`: Sites com falhas persistentes

**Exports:**
- `export_dashboard_json()`: JSONs estaticos
- `export_to_parquet()`: Parquet particionado
- `export_quarantine_json/csv()`: Lista de quarentena

### 4. Models (models.py)

Modelos Pydantic para validacao de dados.

**Principais:**
- `SiteAudit`: Resultado completo de auditoria
- `AuditSummary`: Resumo com metricas
- `BatchAuditConfig`: Configuracao de coleta

### 5. Dashboard (docs/)

Dashboard web estatico usando MkDocs + JavaScript.

**Arquivos:**
- `index.md`: Pagina HTML do dashboard
- `js/script.js`: Logica de carregamento e filtros
- `styles.css`: Estilos CSS
- `data/`: JSONs gerados pelo CLI

**JSONs do Dashboard:**
```
docs/data/
├── summary.json        # Metricas agregadas
├── ranking.json        # Ranking completo
├── top50.json          # Melhores 50 sites
├── worst50.json        # Piores 50 sites
├── by-state.json       # Por estado
└── quarantine.json     # Sites em quarentena
```

## Fluxo de Dados

### Coleta Diaria (GitHub Actions)

```
1. Workflow dispara (03:00 UTC)
       │
2. Restaura cache do DuckDB
       │
3. Executa coleta incremental
   • Pula sites auditados nas ultimas 24h
   • Pula sites em quarentena
       │
4. Atualiza quarentena
   • Identifica sites com 3+ dias de falha
       │
5. Exporta JSONs do dashboard
       │
6. Upload para Internet Archive
       │
7. Commit e push dos resultados
```

### Processamento de Auditoria

```
URL -> httpx.get(PSI API)
           │
     Mobile + Desktop (paralelo)
           │
     Parse JSON -> Pydantic models
           │
     Extract metrics (FCP, LCP, CLS, scores)
           │
     Save to DuckDB (audits + summaries)
```

## Sistema de Quarentena

Sites com falhas consistentes sao quarentenados para investigacao:

```
Falha dia 1 -> Retry normal
Falha dia 2 -> Retry normal
Falha dia 3 -> Adicionado a quarentena
```

**Estados:**
- `quarantined`: Em quarentena, sera pulado na coleta
- `investigating`: Em investigacao manual
- `resolved`: Problema resolvido
- `wrong_url`: URL incorreta na lista original

## Otimizacoes

### Rate Limiting

```python
# API permite 4 req/s, usamos 3.5 para margem
async with Limiter(rate=3.5, capacity=1):
    await client.get(url)
```

### Coleta Incremental

```python
# Pula sites auditados recentemente
recently_audited = await storage.get_recently_audited_urls(hours=24)
urls_to_audit = [u for u in all_urls if u not in recently_audited]
```

### Processamento em Chunks

```python
# Processa em lotes para melhor gerenciamento de memoria
for chunk in chunked(urls, size=100):
    results = await process_chunk(chunk)
    await save_batch(results)
```

## Testes BDD

Os testes usam pytest-bdd com features em portugues:

```
tests/
├── features/                    # Gherkin features
│   ├── parallel_chunks.feature
│   ├── aggregated_metrics.feature
│   ├── api_mock.feature
│   └── quarantine.feature
├── step_defs/                   # Step definitions
│   └── test_*.py
└── conftest.py                  # Fixtures compartilhadas
```

**Exemplo de Feature:**
```gherkin
Funcionalidade: Sistema de quarentena

  Cenario: Identificar sites com falhas persistentes
    Dado um banco com sites que falharam 3 dias seguidos
    Quando o sistema atualiza a quarentena
    Entao esses sites devem ser marcados como quarentenados
```
