# Arquitetura

A arquitetura do projeto é dividida em três componentes principais:

1.  **Coletor**: Um script Node.js (`collector/collect-psi.js`) responsável por coletar os dados do PageSpeed Insights.
2.  **Processamento de Dados**: Scripts Python (`src/psi_auditor/`) para processar os dados, gerar arquivos JSON e fazer upload para o Internet Archive.
3.  **Front-end**: Uma página HTML estática (`index.html`) com JavaScript para visualizar os dados.
