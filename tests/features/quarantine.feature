# language: pt

Funcionalidade: Sistema de quarentena para sites com falhas persistentes
  Como um operador do sistema
  Eu quero identificar sites que falham consistentemente
  Para investigar se a URL mudou ou esta incorreta

  Contexto:
    Dado que existem auditorias no banco de dados

  Cenario: Identificar sites com falhas consecutivas
    Dado auditorias de um site que falhou por 5 dias consecutivos
    Quando eu atualizar a quarentena com minimo de 3 dias
    Entao o site deve ser adicionado a quarentena
    E o status deve ser "quarantined"
    E o numero de falhas consecutivas deve ser 5

  Cenario: Site com falhas intermitentes nao entra em quarentena
    Dado auditorias de um site com falhas em dias alternados
    Quando eu atualizar a quarentena com minimo de 3 dias
    Entao o site nao deve estar na quarentena

  Cenario: Atualizar status de um site em quarentena
    Dado um site na quarentena com status "quarantined"
    Quando eu atualizar o status para "investigating"
    Entao o status do site deve ser "investigating"
    E a data de atualizacao deve ser atualizada

  Cenario: Marcar site como URL errada
    Dado um site na quarentena
    Quando eu atualizar o status para "wrong_url" com nota "URL mudou para novo dominio"
    Entao o status do site deve ser "wrong_url"
    E a nota deve conter "URL mudou"

  Cenario: Remover site da quarentena
    Dado um site na quarentena com status "resolved"
    Quando eu remover o site da quarentena
    Entao o site nao deve estar mais na quarentena

  Cenario: Listar sites em quarentena por status
    Dado 5 sites em quarentena com status "quarantined"
    E 3 sites em quarentena com status "investigating"
    Quando eu listar sites com status "quarantined"
    Entao devo ver 5 sites na lista

  Cenario: Obter URLs para pular na coleta
    Dado sites em quarentena com status "quarantined"
    E sites em quarentena com status "wrong_url"
    E sites em quarentena com status "investigating"
    Quando eu obter URLs para pular
    Entao as URLs com status "quarantined" devem ser retornadas
    E as URLs com status "wrong_url" devem ser retornadas
    E as URLs com status "investigating" nao devem ser retornadas

  Cenario: Estatisticas da quarentena
    Dado sites em quarentena com varios status
    Quando eu solicitar estatisticas da quarentena
    Entao devo ver o total de sites
    E devo ver a contagem por status
    E devo ver a media de falhas
    E devo ver o maximo de falhas

  Cenario: Site volta a funcionar
    Dado um site em quarentena que voltou a funcionar
    Quando eu executar uma nova auditoria com sucesso
    E eu atualizar o status para "resolved"
    Entao o site pode ser removido da quarentena
    E futuras coletas devem incluir este site
