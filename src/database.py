import logging
import os
import sqlite3

from storage import CAMINHO_ARQUIVO_IE, CAMINHO_ARQUIVO_USUARIOS, carregar_json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "datasets")
DB_PATH = os.path.join(DATA_DIR, "censo_escolar.db")

logger = logging.getLogger("censo_escolar")


SCHEMA = """
CREATE TABLE IF NOT EXISTS instituicoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    no_entidade   TEXT NOT NULL,
    co_entidade   INTEGER NOT NULL,
    no_uf         TEXT,
    sg_uf         TEXT,
    co_uf         INTEGER,
    no_municipio  TEXT,
    co_municipio  INTEGER,
    nu_ano_censo  INTEGER,
    qt_mat_bas    INTEGER,
    qt_mat_inf    INTEGER,
    qt_mat_fund   INTEGER,
    qt_mat_med    INTEGER,
    qt_mat_prof   INTEGER,
    qt_mat_eja    INTEGER,
    qt_mat_esp    INTEGER,
    ativo         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT NOT NULL,
    email         TEXT NOT NULL,
    perfil        TEXT,
    ativo_usuario INTEGER NOT NULL DEFAULT 1,
    ativo         INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_instituicoes_co_entidade ON instituicoes (co_entidade, ativo);
CREATE INDEX IF NOT EXISTS idx_instituicoes_listagem ON instituicoes (ativo, co_entidade);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios (email, ativo);
CREATE INDEX IF NOT EXISTS idx_usuarios_listagem ON usuarios (ativo, id);
"""

CAMPOS_INSTITUICAO = (
    "no_entidade", "no_uf", "sg_uf", "co_uf", "no_municipio", "co_municipio",
    "no_mesorregiao", "co_mesorregiao", "no_microrregiao", "co_microrregiao",
    "nu_ano_censo", "no_regiao", "co_regiao", "qt_mat_bas", "qt_mat_inf",
    "qt_mat_fund", "qt_mat_med", "qt_mat_prof", "qt_mat_eja", "qt_mat_esp",
)


def obter_conexao():
    """Retorna uma nova conexão SQLite com linhas acessíveis por nome de coluna."""
    conexao = sqlite3.connect(DB_PATH)
    conexao.row_factory = sqlite3.Row
    return conexao


def colunas_da_tabela(conexao, tabela):
    linhas = conexao.execute(f"PRAGMA table_info({tabela})").fetchall()
    return {linha["name"] for linha in linhas}


def _popular_instituicoes(conexao):
    total = conexao.execute("SELECT COUNT(*) FROM instituicoes").fetchone()[0]
    if total > 0:
        return
    existentes = colunas_da_tabela(conexao, "instituicoes")
    colunas = tuple(
        ("co_entidade",) + tuple(c for c in CAMPOS_INSTITUICAO if c in existentes)
    )
    registros = carregar_json(CAMINHO_ARQUIVO_IE)
    parametros = [
        tuple(ie.get(campo) for campo in colunas)
        for ie in registros
    ]
    conexao.executemany(
        f"INSERT INTO instituicoes ({', '.join(colunas)}) "
        f"VALUES ({', '.join('?' * len(colunas))})",
        parametros,
    )
    logger.info("Carga inicial: %d instituições inseridas em 'instituicoes'", len(parametros))


def _popular_usuarios(conexao):
    total = conexao.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if total > 0:
        return
    registros = carregar_json(CAMINHO_ARQUIVO_USUARIOS)
    parametros = [
        (
            usuario["id"],
            usuario.get("nome"),
            usuario.get("email"),
            usuario.get("perfil"),
            1 if usuario.get("ativo", True) else 0,
        )
        for usuario in registros
    ]
    conexao.executemany(
        "INSERT INTO usuarios (id, nome, email, perfil, ativo_usuario) "
        "VALUES (?, ?, ?, ?, ?)",
        parametros,
    )
    logger.info("Carga inicial: %d usuários inseridos em 'usuarios'", len(parametros))


def inicializar_banco():
    """Cria o arquivo, as tabelas, os índices e povoa a base se ela estiver vazia (idempotente)."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        conexao = obter_conexao()
        try:
            conexao.executescript(SCHEMA)
            _popular_instituicoes(conexao)
            _popular_usuarios(conexao)
            conexao.commit()
        finally:
            conexao.close()
    except (OSError, sqlite3.Error, ValueError):
        logger.exception("Falha ao inicializar o banco de dados em %s", DB_PATH)
        raise
    return DB_PATH
