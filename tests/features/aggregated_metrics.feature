# language: pt

Funcionalidade: Metricas agregadas e dashboard
  Como um analista de dados
  Eu quero visualizar metricas agregadas dos sites auditados
  Para entender o panorama geral de acessibilidade e performance

  Contexto:
    Dado que existem auditorias no banco de dados

  Cenario: Visualizar estatisticas gerais
    Dado 100 auditorias no banco de dados
    Quando eu executar o comando "stats"
    Entao devo ver o total de sites auditados
    E devo ver a taxa de sucesso
    E devo ver a taxa de erros

  Cenario: Calcular medias de performance
    Dado 50 auditorias com scores de performance variados
    Quando eu solicitar as metricas agregadas
    Entao devo ver a media de performance mobile
    E devo ver a media de performance desktop
    E devo ver o desvio padrao

  Cenario: Agrupar metricas por estado
    Dado auditorias de sites de diferentes estados brasileiros
    Quando eu solicitar metricas agrupadas por estado
    Entao devo ver a media de acessibilidade por estado
    E devo ver o ranking de estados por performance

  Cenario: Identificar sites com pior performance
    Dado 100 auditorias no banco de dados
    Quando eu solicitar os 10 piores sites
    Entao devo ver uma lista ordenada por score de performance
    E o primeiro da lista deve ter o menor score

  Cenario: Identificar sites com melhor acessibilidade
    Dado 100 auditorias no banco de dados
    Quando eu solicitar os 10 melhores sites em acessibilidade
    Entao devo ver uma lista ordenada por score de acessibilidade
    E o primeiro da lista deve ter o maior score

  Cenario: Exportar metricas para JSON
    Dado auditorias no banco de dados
    Quando eu exportar as metricas agregadas para JSON
    Entao um arquivo JSON deve ser criado
    E deve conter as medias de todas as categorias
    E deve conter a data de geracao

  Cenario: Comparar evolucao temporal
    Dado auditorias de diferentes datas para o mesmo site
    Quando eu solicitar a evolucao temporal
    Entao devo ver a variacao de performance ao longo do tempo
    E devo identificar tendencias de melhoria ou piora
