# language: pt

Funcionalidade: Processamento em chunks paralelos
  Como um operador do sistema
  Eu quero que multiplas URLs sejam processadas em paralelo
  Para que a coleta seja mais rapida respeitando o rate limit da API

  Contexto:
    Dado que a API PSI tem limite de 4 requisicoes por segundo
    E que cada site requer 2 requisicoes (mobile + desktop)

  Cenario: Processar chunk de URLs em paralelo
    Dado uma lista de 10 URLs para auditar
    E um tamanho de chunk de 5
    Quando eu processar as URLs em chunks paralelos
    Entao 5 URLs devem ser processadas simultaneamente
    E o rate limit de 4 req/s deve ser respeitado
    E todas as 10 URLs devem ser auditadas

  Cenario: Rate limit e respeitado mesmo com paralelismo
    Dado uma lista de 20 URLs para auditar
    E um rate limit de 3.5 requisicoes por segundo
    Quando eu processar as URLs em chunks paralelos
    Entao o tempo total deve ser aproximadamente 20 * 2 / 3.5 segundos
    E nenhum erro de rate limit deve ocorrer

  Cenario: Falha em uma URL nao afeta as outras do chunk
    Dado uma lista de 5 URLs onde 1 retorna erro
    Quando eu processar as URLs em chunks paralelos
    Entao 4 URLs devem ter resultado de sucesso
    E 1 URL deve ter mensagem de erro
    E o processamento deve continuar normalmente

  Cenario: Chunks respeitam o semaforo de concorrencia
    Dado uma lista de 100 URLs para auditar
    E um limite de 10 conexoes simultaneas
    Quando eu processar as URLs em chunks paralelos
    Entao no maximo 10 requisicoes HTTP devem estar ativas ao mesmo tempo
