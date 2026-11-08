from flask import Blueprint, jsonify, request

from controllers.respostas import resposta_lista
from serializers import dump
from services.usuario_service import UsuarioService

usuario_bp = Blueprint("usuario", __name__)

service = UsuarioService()

SERIALIZACAO = {"booleanos": ("ativo",), "renomear": {"ativo_usuario": "ativo"}}


@usuario_bp.route("/usuarios", methods=["GET"])
def get_usuarios():
    registros, total = service.listar(
        request.args.get("page"), request.args.get("limit")
    )
    return resposta_lista(registros, SERIALIZACAO, total=total)


@usuario_bp.route("/usuarios/<int:id_usuario>", methods=["GET"])
def get_usuario_por_id(id_usuario):
    usuario = service.obter(id_usuario)
    return jsonify(dump(usuario, **SERIALIZACAO)), 200


@usuario_bp.route("/usuarios", methods=["POST"])
def criar_usuario():
    criado = service.criar(request.get_json(silent=True))
    return jsonify(dump(criado, **SERIALIZACAO)), 201


@usuario_bp.route("/usuarios/<int:id_usuario>", methods=["PUT"])
def atualizar_usuario(id_usuario):
    atualizado = service.atualizar(id_usuario, request.get_json(silent=True))
    return jsonify(dump(atualizado, **SERIALIZACAO)), 200


@usuario_bp.route("/usuarios/<int:id_usuario>", methods=["DELETE"])
def remover_usuario(id_usuario):
    tipo = request.args.get("tipo", "logico")
    removido, mensagem = service.remover(id_usuario, tipo)
    return (
        jsonify(
            {
                "mensagem": mensagem,
                "tipo": tipo,
                "usuario": dump(removido, **SERIALIZACAO),
            }
        ),
        200,
    )
