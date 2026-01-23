# language: pt

Funcionalidade: Camada de armazenamento com Ibis
  Como um desenvolvedor do sistema
  Eu quero usar Ibis para operacoes de banco de dados
  Para ter queries tipadas e independentes de backend

  Contexto:
    Dado uma conexao Ibis com DuckDB em memoria

  # ========================================================================
  # Esquemas e Tabelas
  # ========================================================================

  Cenario: Criar esquema de auditorias
    Quando eu criar as tabelas via Ibis
    Entao a tabela "audits" deve existir
    E a tabela "audit_summaries" deve existir
    E a tabela "quarantine" deve existir

  Cenario: Verificar colunas da tabela audits
    Dado que as tabelas foram criadas via Ibis
    Quando eu consultar o esquema da tabela "audits"
    Entao deve ter a coluna "id" do tipo inteiro
    E deve ter a coluna "url" do tipo string
    E deve ter a coluna "timestamp" do tipo timestamp
    E deve ter a coluna "mobile_result" do tipo JSON
    E deve ter a coluna "desktop_result" do tipo JSON

  Cenario: Verificar colunas da tabela audit_summaries
    Dado que as tabelas foram criadas via Ibis
    Quando eu consultar o esquema da tabela "audit_summaries"
    Entao deve ter a coluna "mobile_performance" do tipo float
    E deve ter a coluna "mobile_accessibility" do tipo float
    E deve ter a coluna "has_errors" do tipo boolean

  # ========================================================================
  # Operacoes CRUD
  # ========================================================================

  Cenario: Inserir auditoria via Ibis
    Dado que as tabelas foram criadas via Ibis
    Quando eu inserir uma auditoria para "https://teste.sp.gov.br"
    Entao a auditoria deve ser salva com sucesso
    E o resumo deve ser criado automaticamente

  Cenario: Consultar auditorias recentes via Ibis
    Dado auditorias salvas nas ultimas 24 horas
    Quando eu consultar URLs auditadas recentemente
    Entao devo receber a lista de URLs distintas

  Cenario: Inserir site na quarentena via Ibis
    Dado que as tabelas foram criadas via Ibis
    Quando eu adicionar "https://falhou.gov.br" a quarentena com 5 falhas
    Entao o site deve aparecer na lista de quarentena
    E deve ter status "quarantined"

  # ========================================================================
  # Consultas Agregadas
  # ========================================================================

  Cenario: Calcular metricas agregadas via Ibis
    Dado 10 auditorias com scores variados
    Quando eu calcular as metricas agregadas via Ibis
    Entao devo receber o total de auditorias
    E devo receber a media de performance mobile
    E devo receber o desvio padrao

  Cenario: Agrupar por estado via Ibis
    Dado auditorias de sites de SP, RJ e MG
    Quando eu agrupar metricas por estado via Ibis
    Entao devo ver SP na lista de estados
    E devo ver RJ na lista de estados
    E devo ver MG na lista de estados

  Cenario: Obter piores sites via Ibis
    Dado 20 auditorias com performance variada
    Quando eu consultar os 5 piores sites via Ibis
    Entao devo receber 5 sites
    E o primeiro deve ter a menor performance

  Cenario: Obter melhores sites em acessibilidade via Ibis
    Dado 20 auditorias com acessibilidade variada
    Quando eu consultar os 5 melhores sites em acessibilidade via Ibis
    Entao devo receber 5 sites
    E o primeiro deve ter a maior acessibilidade

  # ========================================================================
  # Quarentena
  # ========================================================================

  Cenario: Atualizar quarentena com falhas consecutivas via Ibis
    Dado auditorias com falhas em 5 dias consecutivos para "https://problema.gov.br"
    Quando eu atualizar a quarentena via Ibis com minimo de 3 dias
    Entao "https://problema.gov.br" deve entrar na quarentena
    E deve ter 5 falhas consecutivas registradas

  Cenario: Obter estatisticas de quarentena via Ibis
    Dado 3 sites em quarentena com status "quarantined"
    E 2 sites em quarentena com status "investigating"
    Quando eu consultar estatisticas da quarentena via Ibis
    Entao o total deve ser 5
    E o total em quarentena deve ser 3
    E o total em investigacao deve ser 2

  Cenario: Obter URLs para pular na coleta via Ibis
    Dado sites em quarentena com varios status
    Quando eu obter URLs para pular via Ibis
    Entao URLs com status "quarantined" devem ser retornadas
    E URLs com status "wrong_url" devem ser retornadas
    E URLs com status "investigating" nao devem ser retornadas

  # ========================================================================
  # Evolucao Temporal
  # ========================================================================

  Cenario: Consultar evolucao temporal via Ibis
    Dado 5 auditorias do mesmo site em datas diferentes
    Quando eu consultar a evolucao temporal via Ibis
    Entao devo receber 5 registros ordenados por data
    E cada registro deve ter metricas de performance

  # ========================================================================
  # Ranking e Dashboard
  # ========================================================================

  Cenario: Gerar ranking de sites via Ibis
    Dado 50 auditorias de sites diferentes
    Quando eu gerar o ranking via Ibis
    Entao cada site deve aparecer apenas uma vez
    E devem estar ordenados por acessibilidade
    E cada registro deve ter posicao no ranking

  Cenario: Exportar dados para dashboard via Ibis
    Dado auditorias e quarentena populadas
    Quando eu exportar dados para dashboard via Ibis
    Entao o arquivo "summary.json" deve ser criado
    E o arquivo "ranking.json" deve ser criado
    E o arquivo "by-state.json" deve ser criado
    E o arquivo "quarantine.json" deve ser criado
