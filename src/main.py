import threading
from flask import Flask, jsonify, request
from storage import CAMINHO_ARQUIVO_IE, CAMINHO_ARQUIVO_USUARIOS, carregar_json, salvar_json

app = Flask(__name__)

LOCK = threading.Lock()

CAMPOS_IGNORADOS = ("codigo",)


@app.route("/instituicaoensino", methods=["GET"])
def get_instituicoes():
    dados_ie = carregar_json(CAMINHO_ARQUIVO_IE)

    cod_busca = request.args.get("codigo")
    if not cod_busca:
        return jsonify(dados_ie), 200

    if not cod_busca.isdigit():
        return jsonify({"erro": "O parâmetro 'codigo' deve ser um número inteiro"}), 400

    for ie in dados_ie:
        if ie["co_entidade"] == int(cod_busca):
            return jsonify(ie), 200
    return jsonify({"erro": "Instituição de ensino não encontrada"}), 404


@app.route("/instituicaoensino/<int:co_entidade>", methods=["GET"])
def get_instituicao_por_id(co_entidade):
    for ie in carregar_json(CAMINHO_ARQUIVO_IE):
        if ie["co_entidade"] == co_entidade:
            return jsonify(ie), 200
    return jsonify({"erro": "Instituição de ensino não encontrada"}), 404


@app.route("/instituicaoensino", methods=["POST"])
def criar_instituicao():
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict) or not corpo:
        return jsonify({"erro": "Corpo da requisição inválido: envie um JSON válido"}), 400

    co_entidade = corpo.get("co_entidade")
    if co_entidade is None or isinstance(co_entidade, bool) or not isinstance(co_entidade, int):
        return jsonify({"erro": "O campo 'co_entidade' é obrigatório e deve ser um número inteiro"}), 400
    if not corpo.get("no_entidade"):
        return jsonify({"erro": "O campo 'no_entidade' é obrigatório"}), 400

    with LOCK:
        dados_ie = carregar_json(CAMINHO_ARQUIVO_IE)
        if any(ie["co_entidade"] == co_entidade for ie in dados_ie):
            return jsonify({"erro": f"Já existe uma instituição com co_entidade {co_entidade}"}), 409

        dados_ie.append(corpo)
        salvar_json(CAMINHO_ARQUIVO_IE, dados_ie)

    return jsonify(corpo), 201


@app.route("/instituicaoensino/<int:co_entidade>", methods=["PUT"])
def atualizar_instituicao(co_entidade):
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict) or not corpo:
        return jsonify({"erro": "Corpo da requisição inválido: envie um JSON válido"}), 400
    if "co_entidade" in corpo and corpo["co_entidade"] != co_entidade:
        return jsonify({"erro": "Não é permitido alterar o 'co_entidade' da instituição"}), 400

    with LOCK:
        dados_ie = carregar_json(CAMINHO_ARQUIVO_IE)
        for indice, ie in enumerate(dados_ie):
            if ie["co_entidade"] == co_entidade:
                dados_ie[indice] = {**ie, **corpo}
                salvar_json(CAMINHO_ARQUIVO_IE, dados_ie)
                return jsonify(dados_ie[indice]), 200

    return jsonify({"erro": "Instituição de ensino não encontrada"}), 404


@app.route("/instituicaoensino/<int:co_entidade>", methods=["DELETE"])
def remover_instituicao(co_entidade):
    with LOCK:
        dados_ie = carregar_json(CAMINHO_ARQUIVO_IE)
        for indice, ie in enumerate(dados_ie):
            if ie["co_entidade"] == co_entidade:
                removida = dados_ie.pop(indice)
                salvar_json(CAMINHO_ARQUIVO_IE, dados_ie)
                return jsonify({"mensagem": "Instituição removida com sucesso", "instituicao": removida}), 200

    return jsonify({"erro": "Instituição de ensino não encontrada"}), 404


@app.route("/usuarios", methods=["GET"])
def get_usuarios():
    return jsonify(carregar_json(CAMINHO_ARQUIVO_USUARIOS)), 200


@app.route("/usuarios/<int:id_usuario>", methods=["GET"])
def get_usuario_por_id(id_usuario):
    for usuario in carregar_json(CAMINHO_ARQUIVO_USUARIOS):
        if usuario["id"] == id_usuario:
            return jsonify(usuario), 200
    return jsonify({"erro": "Usuário não encontrado"}), 404


@app.route("/usuarios", methods=["POST"])
def criar_usuario():
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict) or not corpo:
        return jsonify({"erro": "Corpo da requisição inválido: envie um JSON válido"}), 400
    if not corpo.get("nome"):
        return jsonify({"erro": "O campo 'nome' é obrigatório"}), 400
    if not corpo.get("email"):
        return jsonify({"erro": "O campo 'email' é obrigatório"}), 400

    with LOCK:
        usuarios = carregar_json(CAMINHO_ARQUIVO_USUARIOS)

        if any(usuario["email"] == corpo["email"] for usuario in usuarios):
            return jsonify({"erro": "Já existe um usuário com este e-mail"}), 409

        id_usuario = corpo.get("id")
        if id_usuario is None:
            id_usuario = max((usuario["id"] for usuario in usuarios), default=0) + 1
            corpo["id"] = id_usuario
        elif (isinstance(id_usuario, bool) or not isinstance(id_usuario, int)
              or any(usuario["id"] == id_usuario for usuario in usuarios)):
            return jsonify({"erro": "O campo 'id' deve ser um número inteiro ainda não utilizado"}), 400

        usuarios.append(corpo)
        salvar_json(CAMINHO_ARQUIVO_USUARIOS, usuarios)

    return jsonify(corpo), 201


@app.route("/usuarios/<int:id_usuario>", methods=["PUT"])
def atualizar_usuario(id_usuario):
    corpo = request.get_json(silent=True)
    if not isinstance(corpo, dict) or not corpo:
        return jsonify({"erro": "Corpo da requisição inválido: envie um JSON válido"}), 400
    if "id" in corpo and corpo["id"] != id_usuario:
        return jsonify({"erro": "Não é permitido alterar o 'id' do usuário"}), 400

    with LOCK:
        usuarios = carregar_json(CAMINHO_ARQUIVO_USUARIOS)
        for indice, usuario in enumerate(usuarios):
            if usuario["id"] == id_usuario:
                usuarios[indice] = {**usuario, **corpo}
                salvar_json(CAMINHO_ARQUIVO_USUARIOS, usuarios)
                return jsonify(usuarios[indice]), 200

    return jsonify({"erro": "Usuário não encontrado"}), 404


@app.route("/usuarios/<int:id_usuario>", methods=["DELETE"])
def remover_usuario(id_usuario):
    with LOCK:
        usuarios = carregar_json(CAMINHO_ARQUIVO_USUARIOS)
        for indice, usuario in enumerate(usuarios):
            if usuario["id"] == id_usuario:
                removido = usuarios.pop(indice)
                salvar_json(CAMINHO_ARQUIVO_USUARIOS, usuarios)
                return jsonify({"mensagem": "Usuário removido com sucesso", "usuario": removido}), 200

    return jsonify({"erro": "Usuário não encontrado"}), 404


@app.errorhandler(404)
def rota_nao_encontrada(_erro):
    return jsonify({"erro": "Rota não encontrada"}), 404


@app.errorhandler(405)
def metodo_nao_permitido(_erro):
    return jsonify({"erro": "Método não permitido para esta rota"}), 405


@app.errorhandler(ValueError)
def arquivo_dados_corrompido(_erro):
    return jsonify({"erro": "Erro interno: arquivo de dados corrompido ou ilegível"}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
