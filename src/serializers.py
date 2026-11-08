def toDict(linha, booleanos=("ativo",), renomear=None):
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
    """Serializa dados para o formato de resposta JSON da API"""
    if many:
        return [toDict(item, booleanos=booleanos, renomear=renomear) for item in dados]
    return toDict(dados, booleanos=booleanos, renomear=renomear)
