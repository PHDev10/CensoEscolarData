import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CAMINHO_ARQUIVO_IE = os.path.join(
    BASE_DIR, "datasets", "escolas_pb_matriculas_2025.json"
)
CAMINHO_ARQUIVO_USUARIOS = os.path.join(BASE_DIR, "datasets", "usuarios.json")


def carregar_json(caminho):
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)
