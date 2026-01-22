# language: pt

Funcionalidade: Testes com mock da API PSI
  Como um desenvolvedor
  Eu quero testar o sistema sem depender da API real
  Para ter testes rapidos e confiaveis no CI

  Contexto:
    Dado que a API PSI esta mockada

  Cenario: Auditar site com resposta de sucesso mockada
    Dado uma resposta mockada com score de performance 0.85
    E uma resposta mockada com score de acessibilidade 0.90
    Quando eu auditar o site "https://exemplo.gov.br"
    Entao o resultado deve ter performance 0.85
    E o resultado deve ter acessibilidade 0.90
    E nao deve haver mensagem de erro

  Cenario: Auditar site com erro de timeout mockado
    Dado uma resposta mockada que retorna timeout
    Quando eu auditar o site "https://site-lento.gov.br"
    Entao o resultado deve ter mensagem de erro contendo "timeout"
    E o retry deve ser tentado 3 vezes

  Cenario: Auditar site com erro 429 (rate limit) mockado
    Dado uma resposta mockada que retorna erro 429
    Quando eu auditar o site "https://site.gov.br"
    Entao o sistema deve aguardar antes de tentar novamente
    E o retry deve usar backoff exponencial

  Cenario: Auditar site com resposta invalida mockada
    Dado uma resposta mockada com JSON invalido
    Quando eu auditar o site "https://site.gov.br"
    Entao o resultado deve ter mensagem de erro
    E o erro deve ser registrado no log

  Cenario: Batch de sites com mix de sucesso e erro
    Dado 5 respostas mockadas de sucesso
    E 2 respostas mockadas de erro
    Quando eu processar um batch de 7 sites
    Entao 5 sites devem ter resultado de sucesso
    E 2 sites devem ter mensagem de erro
    E todos os 7 devem ser salvos no banco

  Cenario: Verificar que mock nao faz requisicoes reais
    Dado que o mock esta ativo
    Quando eu auditar qualquer site
    Entao nenhuma requisicao HTTP real deve ser feita
    E o teste deve completar em menos de 1 segundo

  Cenario: Mock retorna Core Web Vitals
    Dado uma resposta mockada com metricas CWV
    Quando eu auditar o site "https://site.gov.br"
    Entao o resultado deve conter FCP
    E o resultado deve conter LCP
    E o resultado deve conter CLS

  Cenario: Testar fluxo completo com mock
    Dado respostas mockadas para 10 sites
    Quando eu executar o comando batch com mock
    Entao o banco de dados deve conter 10 registros
    E o arquivo Parquet deve ser gerado
    E o arquivo JSON deve ser gerado
