def toDict(linha, booleanos=("ativo",), renomear=None):
    """Converte uma única linha do banco (sqlite3.Row/dict) em dicionário.

    - `renomear`: mapeia nome de coluna -> nome de campo da resposta
      (ex.: {"ativo_usuario": "ativo"} para expor o `ativo` de negócio
      dos usuários sem colidir com a coluna de exclusão lógica).
    - `booleanos`: nomes de colunas 0/1 que devem ser expostas como bool.
    """
    if linha is None:
        return None
    registro = dict(linha)
    if renomear:
        for origem, destino in renomear.items():
            if origem in registro:
                registro[destino] = registro.pop(origem)
    for campo in booleanos:
        if campo in registro:
            registro[campo] = bool(registro[campo])
    return registro


def dump(dados, many=False, booleanos=("ativo",), renomear=None):
    """Serializa dados para o formato de resposta JSON da API.

    - `many=False` (padrão): converte um único registro.
    - `many=True`: itera e converte uma lista de registros.
    """
    if many:
        return [toDict(item, booleanos=booleanos, renomear=renomear) for item in dados]
    return toDict(dados, booleanos=booleanos, renomear=renomear)
