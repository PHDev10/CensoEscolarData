import logging

import sqlite3

from flask import Flask, jsonify, request

from database import inicializar_banco
from repository import InstituicaoRepository, UsuarioRepository
from serializers import dump

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("censo_escolar")

inicializar_banco()

app = Flask(__name__)

repo_instituicoes = InstituicaoRepository()
repo_usuarios = UsuarioRepository()

SERIALIZACAO_IE = {"booleanos": ("ativo",), "renomear": None}
SERIALIZACAO_USUARIO = {
    "booleanos": ("ativo",),
    "renomear": {"ativo_usuario": "ativo"},
}

TIPOS_DELETES_VALIDOS = ("logico", "fisico")

LIMIT_MAXIMO_PAGINA = 1000


def _validar_tipo_delete(request_query):
    tipo = request_query.get("tipo", "logico")
    if tipo not in TIPOS_DELETES_VALIDOS:
        return None
    return tipo


def _ler_paginacao(qargs, limit_padrao=None):
    """Retorna None quando nenhum parâmetro é enviado (retrocompatível com o
    comportamento de lista completa) ou a tupla (page, limit) já validada.
    Lança ValueError para parâmetros inválidos (a rota responde 400).
    """
    raw_page = qargs.get("page")
    raw_limit = qargs.get("limit")
    if raw_page is None and raw_limit is None:
        return None

    page, limit = 1, limit_padrao
    try:
        if raw_page is not None:
            page = int(raw_page)
        if raw_limit is not None:
            limit = int(raw_limit)
    except (TypeError, ValueError):
        raise ValueError("Os parâmetros 'page' e 'limit' devem ser números inteiros")

    if page < 1 or (limit is not None and limit < 1):
        raise ValueError("Os parâmetros 'page' e 'limit' devem ser números inteiros positivos")

    if limit is not None:
        limit = min(limit, LIMIT_MAXIMO_PAGINA)
    return page, limit


def _resposta_lista(registros, serializacao, total=None):
    """Serializa uma lista com dump(many=True) e expõe X-Total-Count quando houver."""
    resposta = jsonify(dump(registros, many=True, **serializacao))
    if total is not None:
        resposta.headers["X-Total-Count"] = str(total)
    return resposta, 200


@app.route("/instituicoesensino", methods=["GET"])
@app.route("/instituicaoensino", methods=["GET"])
def get_instituicoes():
    cod_busca = request.args.get("codigo")
    if cod_busca:
        if not cod_busca.isdigit():
            return jsonify({"erro": "O parâmetro 'codigo' deve ser um número inteiro"}), 400
        instituicao = repo_instituicoes.obter(int(cod_busca))
        if instituicao is None:
            return jsonify({"erro": "Instituição de ensino não encontrada"}), 404
        return jsonify(dump(instituicao, **SERIALIZACAO_IE)), 200

    try:
        paginacao = _ler_paginacao(request.args, limit_padrao=100)
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    if paginacao is None:
        registros = repo_instituicoes.listar()
        return _resposta_lista(registros, SERIALIZACAO_IE)

    page, limit = paginacao
    total = repo_instituicoes.contar_ativos()
    registros = repo_instituicoes.listar(page=page, limit=limit)
    return _resposta_lista(registros, SERIALIZACAO_IE, total=total)


@app.route("/instituicoesensino/<int:co_entidade>", methods=["GET"])
@app.route("/instituicaoensino/<int:co_entidade>", methods=["GET"])
def get_instituicao_por_id(co_entidade):
    instituicao = repo_instituicoes.obter(co_entidade)
    if instituicao is None:
        return jsonify({"erro": "Instituição de ensino não encontrada"}), 404
    return jsonify(dump(instituicao, **SERIALIZACAO_IE)), 200


@app.route("/instituicoesensino", methods=["POST"])
@app.route("/instituicaoensino", methods=["POST"])
def criar_instituicao():
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict) or not corpo:
        return (
            jsonify({"erro": "Corpo da requisição inválido: envie um JSON válido"}),
            400,
        )

    co_entidade = corpo.get("co_entidade")
    if (
        co_entidade is None
        or isinstance(co_entidade, bool)
        or not isinstance(co_entidade, int)
    ):
        return (
            jsonify(
                {
                    "erro": "O campo 'co_entidade' é obrigatório e deve ser um número inteiro"
                }
            ),
            400,
        )
    if not corpo.get("no_entidade"):
        return jsonify({"erro": "O campo 'no_entidade' é obrigatório"}), 400

    try:
        if repo_instituicoes.existe_ativo("co_entidade", co_entidade):
            return (
                jsonify(
                    {"erro": f"Já existe uma instituição com co_entidade {co_entidade}"}
                ),
                409,
            )
        criada = repo_instituicoes.inserir(corpo)
    except sqlite3.Error:
        logger.exception("Erro ao inserir instituição %s", co_entidade)
        return jsonify({"erro": "Erro interno ao salvar a instituição"}), 500

    return jsonify(dump(criada, **SERIALIZACAO_IE)), 201


@app.route("/instituicoesensino/<int:co_entidade>", methods=["PUT"])
@app.route("/instituicaoensino/<int:co_entidade>", methods=["PUT"])
def atualizar_instituicao(co_entidade):
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict) or not corpo:
        return (
            jsonify({"erro": "Corpo da requisição inválido: envie um JSON válido"}),
            400,
        )
    if "co_entidade" in corpo and corpo["co_entidade"] != co_entidade:
        return (
            jsonify({"erro": "Não é permitido alterar o 'co_entidade' da instituição"}),
            400,
        )

    try:
        atualizada = repo_instituicoes.atualizar(co_entidade, corpo)
    except sqlite3.Error:
        logger.exception("Erro ao atualizar instituição %s", co_entidade)
        return jsonify({"erro": "Erro interno ao atualizar a instituição"}), 500
    if atualizada is None:
        return jsonify({"erro": "Instituição de ensino não encontrada"}), 404
    return jsonify(dump(atualizada, **SERIALIZACAO_IE)), 200


@app.route("/instituicoesensino/<int:co_entidade>", methods=["DELETE"])
@app.route("/instituicaoensino/<int:co_entidade>", methods=["DELETE"])
def remover_instituicao(co_entidade):
    tipo = _validar_tipo_delete(request.args)
    if tipo is None:
        return (
            jsonify({"erro": "O parâmetro 'tipo' deve ser 'logico' ou 'fisico'"}),
            400,
        )

    try:
        removida = repo_instituicoes.remover(co_entidade, tipo=tipo)
    except sqlite3.Error:
        logger.exception("Erro ao remover instituição %s", co_entidade)
        return jsonify({"erro": "Erro interno ao remover a instituição"}), 500
    if removida is None:
        return jsonify({"erro": "Instituição de ensino não encontrada"}), 404

    logger.info("Instituição %s removida (delete %s)", co_entidade, tipo)
    return (
        jsonify(
            {
                "mensagem": (
                    "Instituição excluída logicamente (ativo = 0)"
                    if tipo == "logico"
                    else "Instituição excluída fisicamente do banco de dados"
                ),
                "tipo": tipo,
                "instituicao": dump(removida, **SERIALIZACAO_IE),
            }
        ),
        200,
    )


@app.route("/usuarios", methods=["GET"])
def get_usuarios():
    try:
        paginacao = _ler_paginacao(request.args, limit_padrao=None)
    except ValueError as erro:
        return ((jsonify({"erro": str(erro)})), 400)

    if paginacao is None:
        registros = repo_usuarios.listar()
        return _resposta_lista(registros, SERIALIZACAO_USUARIO)

    page, limit = paginacao
    total = repo_usuarios.contar_ativos()
    registros = repo_usuarios.listar(page=page, limit=limit)
    return _resposta_lista(registros, SERIALIZACAO_USUARIO, total=total)


@app.route("/usuarios/<int:id_usuario>", methods=["GET"])
def get_usuario_por_id(id_usuario):
    usuario = repo_usuarios.obter(id_usuario)
    if usuario is None:
        return jsonify({"erro": "Usuário não encontrado"}), 404
    return jsonify(dump(usuario, **SERIALIZACAO_USUARIO)), 200


@app.route("/usuarios", methods=["POST"])
def criar_usuario():
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict) or not corpo:
        return (
            jsonify({"erro": "Corpo da requisição inválido: envie um JSON válido"}),
            400,
        )
    if not corpo.get("nome"):
        return jsonify({"erro": "O campo 'nome' é obrigatório"}), 400
    if not corpo.get("email"):
        return jsonify({"erro": "O campo 'email' é obrigatório"}), 400

    try:
        if repo_usuarios.existe_email(corpo["email"]):
            return jsonify({"erro": "Já existe um usuário com este e-mail"}), 409

        id_usuario = corpo.get("id")
        if id_usuario is None:
            corpo["id"] = repo_usuarios.proximo_id()
        elif (
            isinstance(id_usuario, bool)
            or not isinstance(id_usuario, int)
            or repo_usuarios.id_ja_utilizado(id_usuario)
        ):
            return (
                jsonify(
                    {
                        "erro": "O campo 'id' deve ser um número inteiro ainda não utilizado"
                    }
                ),
                400,
            )

        criado = repo_usuarios.inserir(corpo)
    except sqlite3.Error:
        logger.exception("Erro ao inserir usuário")
        return jsonify({"erro": "Erro interno ao salvar o usuário"}), 500

    return jsonify(dump(criado, **SERIALIZACAO_USUARIO)), 201


@app.route("/usuarios/<int:id_usuario>", methods=["PUT"])
def atualizar_usuario(id_usuario):
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict) or not corpo:
        return (
            jsonify({"erro": "Corpo da requisição inválido: envie um JSON válido"}),
            400,
        )
    if "id" in corpo and corpo["id"] != id_usuario:
        return jsonify({"erro": "Não é permitido alterar o 'id' do usuário"}), 400

    try:
        atualizado = repo_usuarios.atualizar(id_usuario, corpo)
    except sqlite3.Error:
        logger.exception("Erro ao atualizar usuário %s", id_usuario)
        return jsonify({"erro": "Erro interno ao atualizar o usuário"}), 500
    if atualizado is None:
        return jsonify({"erro": "Usuário não encontrado"}), 404
    return jsonify(dump(atualizado, **SERIALIZACAO_USUARIO)), 200


@app.route("/usuarios/<int:id_usuario>", methods=["DELETE"])
def remover_usuario(id_usuario):
    tipo = _validar_tipo_delete(request.args)
    if tipo is None:
        return (
            jsonify({"erro": "O parâmetro 'tipo' deve ser 'logico' ou 'fisico'"}),
            400,
        )

    try:
        removido = repo_usuarios.remover(id_usuario, tipo=tipo)
    except sqlite3.Error:
        logger.exception("Erro ao remover usuário %s", id_usuario)
        return jsonify({"erro": "Erro interno ao remover o usuário"}), 500
    if removido is None:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    logger.info("Usuário %s removido (delete %s)", id_usuario, tipo)
    return (
        jsonify(
            {
                "mensagem": (
                    "Usuário excluído logicamente (ativo = 0)"
                    if tipo == "logico"
                    else "Usuário excluído fisicamente do banco de dados"
                ),
                "tipo": tipo,
                "usuario": dump(removido, **SERIALIZACAO_USUARIO),
            }
        ),
        200,
    )


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
    app.run(port=5000, debug=True)
