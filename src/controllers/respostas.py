from flask import jsonify

from serializers import dump


def resposta_lista(registros, serializacao, total=None):
    """Serializa uma lista e expõe o header X-Total-Count quando houver paginação"""
    resposta = jsonify(dump(registros, many=True, **serializacao))
    if total is not None:
        resposta.headers["X-Total-Count"] = str(total)
    return resposta, 200
