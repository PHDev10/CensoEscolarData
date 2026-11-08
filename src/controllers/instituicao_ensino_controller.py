from flask import Blueprint, jsonify, request

from controllers.respostas import resposta_lista
from serializers import dump
from services.instituicao_ensino_service import InstituicaoEnsinoService

instituicao_ensino_bp = Blueprint("instituicao_ensino", __name__)

service = InstituicaoEnsinoService()

SERIALIZACAO = {"booleanos": ("ativo",), "renomear": None}


@instituicao_ensino_bp.route("/instituicoesensino", methods=["GET"])
@instituicao_ensino_bp.route("/instituicaoensino", methods=["GET"])
def get_instituicoes():
    codigo = request.args.get("codigo")
    if codigo:
        instituicao = service.buscar_por_codigo(codigo)
        return jsonify(dump(instituicao, **SERIALIZACAO)), 200

    registros, total = service.listar(
        request.args.get("page"), request.args.get("limit")
    )
    return resposta_lista(registros, SERIALIZACAO, total=total)


@instituicao_ensino_bp.route("/instituicoesensino/<int:co_entidade>", methods=["GET"])
@instituicao_ensino_bp.route("/instituicaoensino/<int:co_entidade>", methods=["GET"])
def get_instituicao_por_id(co_entidade):
    instituicao = service.obter(co_entidade)
    return jsonify(dump(instituicao, **SERIALIZACAO)), 200


@instituicao_ensino_bp.route("/instituicoesensino", methods=["POST"])
@instituicao_ensino_bp.route("/instituicaoensino", methods=["POST"])
def criar_instituicao():
    criada = service.criar(request.get_json(silent=True))
    return jsonify(dump(criada, **SERIALIZACAO)), 201


@instituicao_ensino_bp.route("/instituicoesensino/<int:co_entidade>", methods=["PUT"])
@instituicao_ensino_bp.route("/instituicaoensino/<int:co_entidade>", methods=["PUT"])
def atualizar_instituicao(co_entidade):
    atualizada = service.atualizar(co_entidade, request.get_json(silent=True))
    return jsonify(dump(atualizada, **SERIALIZACAO)), 200


@instituicao_ensino_bp.route(
    "/instituicoesensino/<int:co_entidade>", methods=["DELETE"]
)
@instituicao_ensino_bp.route("/instituicaoensino/<int:co_entidade>", methods=["DELETE"])
def remover_instituicao(co_entidade):
    tipo = request.args.get("tipo", "logico")
    removida, mensagem = service.remover(co_entidade, tipo)
    return (
        jsonify(
            {
                "mensagem": mensagem,
                "tipo": tipo,
                "instituicao": dump(removida, **SERIALIZACAO),
            }
        ),
        200,
    )
