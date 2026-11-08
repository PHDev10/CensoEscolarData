import sqlite3

from flask import Flask, jsonify, request

from helpers.database import inicializar_banco
from helpers.environment import FLASK_DEBUG, FLASK_PORT
from helpers.logger import logger
from serializers import dump
from services.excecoes import (
    ConflitoError,
    ErroInternoError,
    NaoEncontradoError,
    ServicoError,
    ValidacaoError,
)
from services.instituicao_ensino_service import InstituicaoEnsinoService
from services.usuario_service import UsuarioService

inicializar_banco()

app = Flask(__name__)

service_instituicoes = InstituicaoEnsinoService()
service_usuarios = UsuarioService()

SERIALIZACAO_IE = {"booleanos": ("ativo",), "renomear": None}
SERIALIZACAO_USUARIO = {
    "booleanos": ("ativo",),
    "renomear": {"ativo_usuario": "ativo"},
}

STATUS_POR_ERRO = {
    ValidacaoError: 400,
    NaoEncontradoError: 404,
    ConflitoError: 409,
    ErroInternoError: 500,
}


def _resposta_lista(registros, serializacao, total=None):
    """Serializa uma lista com dump(many=True) e expõe X-Total-Count quando houver"""
    resposta = jsonify(dump(registros, many=True, **serializacao))
    if total is not None:
        resposta.headers["X-Total-Count"] = str(total)
    return resposta, 200


@app.route("/instituicoesensino", methods=["GET"])
@app.route("/instituicaoensino", methods=["GET"])
def get_instituicoes():
    codigo = request.args.get("codigo")
    if codigo:
        instituicao = service_instituicoes.buscar_por_codigo(codigo)
        return jsonify(dump(instituicao, **SERIALIZACAO_IE)), 200

    registros, total = service_instituicoes.listar(
        request.args.get("page"), request.args.get("limit")
    )
    return _resposta_lista(registros, SERIALIZACAO_IE, total=total)


@app.route("/instituicoesensino/<int:co_entidade>", methods=["GET"])
@app.route("/instituicaoensino/<int:co_entidade>", methods=["GET"])
def get_instituicao_por_id(co_entidade):
    instituicao = service_instituicoes.obter(co_entidade)
    return jsonify(dump(instituicao, **SERIALIZACAO_IE)), 200


@app.route("/instituicoesensino", methods=["POST"])
@app.route("/instituicaoensino", methods=["POST"])
def criar_instituicao():
    criada = service_instituicoes.criar(request.get_json(silent=True))
    return jsonify(dump(criada, **SERIALIZACAO_IE)), 201


@app.route("/instituicoesensino/<int:co_entidade>", methods=["PUT"])
@app.route("/instituicaoensino/<int:co_entidade>", methods=["PUT"])
def atualizar_instituicao(co_entidade):
    atualizada = service_instituicoes.atualizar(
        co_entidade, request.get_json(silent=True)
    )
    return jsonify(dump(atualizada, **SERIALIZACAO_IE)), 200


@app.route("/instituicoesensino/<int:co_entidade>", methods=["DELETE"])
@app.route("/instituicaoensino/<int:co_entidade>", methods=["DELETE"])
def remover_instituicao(co_entidade):
    tipo = request.args.get("tipo", "logico")
    removida, mensagem = service_instituicoes.remover(co_entidade, tipo)
    return (
        jsonify(
            {
                "mensagem": mensagem,
                "tipo": tipo,
                "instituicao": dump(removida, **SERIALIZACAO_IE),
            }
        ),
        200,
    )


@app.route("/usuarios", methods=["GET"])
def get_usuarios():
    registros, total = service_usuarios.listar(
        request.args.get("page"), request.args.get("limit")
    )
    return _resposta_lista(registros, SERIALIZACAO_USUARIO, total=total)


@app.route("/usuarios/<int:id_usuario>", methods=["GET"])
def get_usuario_por_id(id_usuario):
    usuario = service_usuarios.obter(id_usuario)
    return jsonify(dump(usuario, **SERIALIZACAO_USUARIO)), 200


@app.route("/usuarios", methods=["POST"])
def criar_usuario():
    criado = service_usuarios.criar(request.get_json(silent=True))
    return jsonify(dump(criado, **SERIALIZACAO_USUARIO)), 201


@app.route("/usuarios/<int:id_usuario>", methods=["PUT"])
def atualizar_usuario(id_usuario):
    atualizado = service_usuarios.atualizar(id_usuario, request.get_json(silent=True))
    return jsonify(dump(atualizado, **SERIALIZACAO_USUARIO)), 200


@app.route("/usuarios/<int:id_usuario>", methods=["DELETE"])
def remover_usuario(id_usuario):
    tipo = request.args.get("tipo", "logico")
    removido, mensagem = service_usuarios.remover(id_usuario, tipo)
    return (
        jsonify(
            {
                "mensagem": mensagem,
                "tipo": tipo,
                "usuario": dump(removido, **SERIALIZACAO_USUARIO),
            }
        ),
        200,
    )


@app.errorhandler(ServicoError)
def erro_de_servico(erro):
    return jsonify({"erro": str(erro)}), STATUS_POR_ERRO[type(erro)]


@app.errorhandler(404)
def rota_nao_encontrada(_erro):
    return jsonify({"erro": "Rota não encontrada"}), 404


@app.errorhandler(405)
def metodo_nao_permitido(_erro):
    return jsonify({"erro": "Método não permitido para esta rota"}), 405


@app.errorhandler(sqlite3.Error)
def erro_banco(_erro):
    logger.exception("Erro de banco de dados não tratado")
    return jsonify({"erro": "Erro interno: falha no banco de dados"}), 500


if __name__ == "__main__":
    app.run(port=FLASK_PORT, debug=FLASK_DEBUG)
