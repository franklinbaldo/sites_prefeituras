# Auditoria de Sites de Prefeituras Brasileiras com PageSpeed Insights

## Visão Geral

Este projeto audita automaticamente os sites das prefeituras brasileiras usando a API do Google PageSpeed Insights (PSI). Ele coleta métricas de desempenho, acessibilidade, SEO e melhores práticas, e armazena os dados em formato Parquet no Internet Archive.

## Arquitetura

A arquitetura do projeto é dividida em três componentes principais:

1.  **Coletor**: Um script Node.js (`collector/collect-psi.js`) responsável por coletar os dados do PageSpeed Insights.
2.  **Processamento de Dados**: Scripts Python (`src/psi_auditor/`) para processar os dados, gerar arquivos Parquet particionados e fazer upload para o Internet Archive.
3.  **Front-end**: Uma página HTML estática (`index.html`) com JavaScript para visualizar os dados diretamente do Internet Archive usando DuckDB-wasm e HTTPFS.

Para mais detalhes, consulte a [documentação completa](https://TODO-ADD-LINK-TO-MKDOCS-SITE).

## Como Funciona

O projeto usa uma combinação de um arquivo de dados, uma Ação do GitHub e scripts Node.js e Python para coletar e apresentar dados da API do PageSpeed Insights.

### Fonte de Dados

A lista primária de sites a serem auditados é proveniente do arquivo `sites_das_prefeituras_brasileiras.csv`.

### Fluxo de Trabalho da Ação do GitHub

Uma Ação do GitHub, definida em `.github/workflows/psi.yml`, automatiza o processo de coleta e arquivamento de dados. Este fluxo de trabalho:
- Executa em um cronograma (diariamente às 3 AM UTC).
- Pode ser acionado manualmente.
- Executa testes para os componentes Python, Node.js e de documentação em paralelo.
- Coleta dados do PSI e os salva em um banco de dados DuckDB.
- Exporta os dados para o formato Parquet, particionado por data e estratégia.
- Faz o upload dos dados para o Internet Archive.
- Gera um arquivo JSON para visualização da web.

### Coleta de Dados

O script `collector/collect-psi.js` é o núcleo da coleta de dados. Ele:
- Lê URLs de `sites_das_prefeituras_brasileiras.csv` usando streaming.
- Busca métricas do PSI para estratégias móveis e de desktop.
- Implementa novas tentativas com backoff exponencial.
- Armazena todos os dados coletados em um banco de dados DuckDB.

### Armazenamento e Arquivamento de Resultados

- **Armazenamento Primário de Dados**: Os resultados da auditoria são armazenados em um banco de dados DuckDB e exportados para o formato Parquet particionado.
- **Arquivamento**: Após cada execução bem-sucedida do script de coleta de dados, os dados Parquet são enviados para o Internet Archive.

## Acessando e Analisando os Dados

Os dados coletados são armazenados em formato Parquet no Internet Archive. A página `index.html` neste repositório apresenta uma visão dos resultados mais recentes, consultando os dados diretamente do Internet Archive.

## Contribuições

Contribuições são bem-vindas! Por favor, envie um pull request com suas alterações.
