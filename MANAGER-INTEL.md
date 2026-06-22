# Inteligência do Repositório (MANAGER-INTEL)

## 1. O que este repo faz
O **Sites Prefeituras** é um sistema automatizado para auditoria de desempenho, acessibilidade, SEO e melhores práticas dos sites das 5.570 prefeituras brasileiras. Utilizando a API do Google PageSpeed Insights (PSI), ele coleta métricas diárias, as armazena e exibe em um dashboard web leve, mantendo histórico no Internet Archive.

## 2. Stack Tecnológica
- **Linguagem Principal**: Python 3.11+
- **Gerenciamento de Pacotes**: `uv`
- **Coleta de Dados e Requisições**: `httpx` (async) e `tenacity` (retries), limitados a 3.5 req/s.
- **Banco de Dados/Armazenamento**: DuckDB para analytics local, exportando JSONs estáticos.
- **CLI**: `Typer` com `Rich`.
- **Frontend/Dashboard**: Documentação gerada via `MkDocs Material` e tabelas/visualizações usando `Tabulator.js` consumindo JSONs estáticos.
- **Testes**: BDD (Behavior-Driven Development) em português utilizando `pytest-bdd`.
- **CI/CD**: Automação diária (e em PRs) via GitHub Actions.

## 3. Estado Atual
- **O que funciona**: Coleta diária em massa automatizada, limites da API sendo respeitados através de *rate limiting* e coletas incrementais (pulando recentes). Armazenamento em DuckDB e geração do dashboard estático.
- **O que está quebrado / Observações Críticas**: Existem erros de requisição no arquivo `psi_errors.log` (ex: "Simulated fetch error for non-existent URL", problemas de arquivos ausentes como `test_sites.csv` na collection). Além disso, há inconsistências de dados reportadas em *issues* abertas.
- **Issues Críticas Abertas**:
  - Issue de URLs inconsistentes (ex: *São João do Paraíso de MG com URL de MA*).
  - Issue com lista de *Sites de prefeituras que tiveram atualização* anexada num Excel, precisando de higienização e atualização no dataset principal.
  - Alerta de segurança do Dependabot (atualização de `js-yaml` no pacote de collector).
  - Falhas de execução esporádicas nos logs (TODO.md menciona erros de `psi_errors_<run_id>.log`).

## 4. Top 3 Issues/Melhorias Priorizadas para um agente Jules implementar
1. **Correção de URLs incorretas e desatualizadas no Dataset Base (`sites_das_prefeituras_brasileiras.csv`)**
   - *Justificativa*: A qualidade do projeto depende da precisão dos URLs. A Issue #1 já aponta um erro claro (MG usando URL do MA), e a Issue #2 fornece uma planilha rica para atualizar dezenas de sites. Um script automatizado pode cruzar as planilhas e atualizar o CSV base.
2. **Tratamento Resiliente de Erros na Coleta (Corrigir falhas listadas no TODO.md / psi_errors.log)**
   - *Justificativa*: O sistema aponta `psi_errors.log` e falhas como `test_sites.csv` não encontrado ou URLs corrompidas. Melhorar a captura e reporte de erros (`try/except` refinado, limpeza automática ou exclusão de URLs inválidas da fila) previne falhas nas Actions diárias.
3. **Atualização de Dependências Críticas e de Segurança**
   - *Justificativa*: Há *issues/PRs* abertos pelo Dependabot para resolver vulnerabilidades de *Prototype Pollution* (ex: `js-yaml` v3.14.2) e atualizar actions (`checkout`, `setup-python`, `setup-uv`). Resolver a dívida técnica é rápido e essencial para a CI continuar funcional de forma segura.

## 5. Observações Técnicas Relevantes
- **Padrões**: Todo o código principal deve ser escrito em Inglês, mas as funcionalidades e Gherkin (testes BDD via `pytest-bdd`) e as documentações (`MkDocs`, `CLAUDE.md`) devem ser em Português.
- **Armadilhas de Limite de API**: O uso da API do PSI é limitado a 4 req/s e 25.000 requisições diárias. A configuração em código está ajustada em 3.5 req/s (como segurança) e faz coleta incremental. Um agente **não deve** mexer nesses limites de concorrência sem justificar muito bem.
- **Sistema de Quarentena**: URLs com problemas persistentes (por mais de 3 dias seguidos) recebem tag de quarentena. Evite forçar requests em URLs marcadas como `quarantined`.
- **Arquitetura de Dados**: O banco não utiliza DuckDB WASM no front, sendo substituído por arquivos estáticos (`.json`) gerados no passo de exportação, o que deve ser mantido para garantir a leveza do frontend.
