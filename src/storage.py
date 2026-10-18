import json
import os
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CAMINHO_ARQUIVO_IE = os.path.join(BASE_DIR, "datasets", "escolas_pb_matriculas_2025.json")
CAMINHO_ARQUIVO_USUARIOS = os.path.join(BASE_DIR, "datasets", "usuarios.json")


def carregar_json(caminho):
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def salvar_json(caminho, dados):
    diretorio = os.path.dirname(caminho) or "."
    fd, caminho_temp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=diretorio)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo_temp:
            json.dump(dados, arquivo_temp, ensure_ascii=False, indent=2)
            arquivo_temp.write("\n")
            arquivo_temp.flush()
            os.fsync(arquivo_temp.fileno())
        os.replace(caminho_temp, caminho)
    except Exception:
        if os.path.exists(caminho_temp):
            os.remove(caminho_temp)
        raise
