import os
from pathlib import Path

from dotenv import load_dotenv

# src/helpers/environment/__init__.py -> raiz do projeto está 3 níveis acima
RAIZ_PROJETO = Path(__file__).resolve().parents[3]

load_dotenv(RAIZ_PROJETO / ".env")


def _texto(chave, padrao):
    return os.environ.get(chave) or padrao


def _inteiro(chave, padrao):
    valor = os.environ.get(chave)
    if not valor:
        return padrao
    try:
        return int(valor)
    except ValueError:
        raise ValueError(f"A variável de ambiente {chave} deve ser um número inteiro")


def _booleano(chave, padrao):
    valor = os.environ.get(chave)
    if not valor:
        return padrao
    return valor.strip().lower() in ("1", "true", "yes", "on")


def _caminho(chave, padrao):
    caminho = Path(_texto(chave, padrao))
    return str(caminho if caminho.is_absolute() else RAIZ_PROJETO / caminho)


DB_NAME = _caminho("DB_NAME", "datasets/censo_escolar.db")
CAMINHO_JSON_INSTITUICOES = _caminho(
    "CAMINHO_JSON_INSTITUICOES", "datasets/escolas_pb_matriculas_2025.json"
)
CAMINHO_JSON_USUARIOS = _caminho("CAMINHO_JSON_USUARIOS", "datasets/usuarios.json")

FLASK_DEBUG = _booleano("FLASK_DEBUG", False)
FLASK_PORT = _inteiro("FLASK_PORT", 5000)
LIMIT_MAXIMO_PAGINA = _inteiro("LIMIT_MAXIMO_PAGINA", 1000)
