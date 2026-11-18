import logging
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

BASE_DIR = Path(__file__).resolve().parent.parent

CHUNKSIZE = 50_000
SEPARATOR = ";"
ENCODING_CANDIDATES = ("utf-8", "latin1")
TABELA = "instituicoes"
TOTAL_ESPERADO = 120_222  # referência de uma execução anterior (SQLite, mesmo CSV)

VARIAVEIS_OBRIGATORIAS = (
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "CSV_PATH",
)

COLUMN_MAP = {
    "NO_ENTIDADE": "no_entidade",
    "CO_ENTIDADE": "co_entidade",
    "NO_UF": "no_uf",
    "SG_UF": "sg_uf",
    "CO_UF": "co_uf",
    "NO_MUNICIPIO": "no_municipio",
    "CO_MUNICIPIO": "co_municipio",
    "NU_ANO_CENSO": "nu_ano_censo",
    "QT_MAT_BAS": "qt_mat_bas",
    "QT_MAT_INF": "qt_mat_inf",
    "QT_MAT_FUND": "qt_mat_fund",
    "QT_MAT_MED": "qt_mat_med",
    "QT_MAT_PROF": "qt_mat_prof",
    "QT_MAT_EJA": "qt_mat_eja",
    "QT_MAT_ESP": "qt_mat_esp",
}
COLUNAS_TABELA = [*COLUMN_MAP.values(), "ativo"]

SIGLAS_NORDESTE = ("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE")
SIGLAS_SUDESTE = ("ES", "MG", "RJ", "SP")
CO_UF_NORDESTE = range(21, 30)  # 21..29
CO_UF_SUDESTE = range(31, 36)  # 31..35

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("etl-censo")


def carregar_configuracao() -> dict:
    """Lê o .env da raiz do projeto e falha cedo se faltar alguma variável."""
    load_dotenv(BASE_DIR / ".env")

    faltando = [v for v in VARIAVEIS_OBRIGATORIAS if not os.getenv(v)]
    if faltando:
        raise ValueError(
            f"Variáveis ausentes no .env: {', '.join(faltando)}. "
            "Copie o .env.example para .env e preencha os valores."
        )

    try:
        porta = int(os.environ["DB_PORT"])
    except ValueError:
        raise ValueError("DB_PORT deve ser um número inteiro.") from None

    return {
        "csv_path": BASE_DIR / os.environ["CSV_PATH"],
        "banco": {
            "host": os.environ["DB_HOST"],
            "port": porta,
            "dbname": os.environ["DB_NAME"],
            "user": os.environ["DB_USER"],
            "password": os.environ["DB_PASSWORD"],
        },
    }


def validar_colunas_origem(csv_path: Path, sep: str, encoding: str) -> None:
    """Valida a presença de todas as colunas obrigatórias no CSV de origem."""
    header = pd.read_csv(csv_path, sep=sep, encoding=encoding, nrows=0).columns.tolist()
    faltando = [c for c in COLUMN_MAP if c not in header]
    if faltando:
        raise ValueError(f"Colunas ausentes no arquivo {csv_path.name}: {faltando}")
    log.info(
        "Validação OK: todas as %d colunas obrigatórias presentes.", len(COLUMN_MAP)
    )


def detectar_encoding(csv_path: Path) -> str:
    for encoding in ENCODING_CANDIDATES:
        try:
            pd.read_csv(csv_path, sep=SEPARATOR, encoding=encoding, nrows=5)
            log.info("Encoding detectado: %s", encoding)
            return encoding
        except UnicodeDecodeError:
            log.info("Tentativa com %s falhou; testando próximo encoding...", encoding)
    raise UnicodeDecodeError(
        b"extractor",
        b"",
        0,
        0,
        "Não foi possível decodificar o CSV com os encodings de teste.",
    )


def filtrar_regioes(df: pd.DataFrame) -> pd.DataFrame:
    """O filtro é feito por SG_UF (sigla) com fallback por CO_UF (código IBGE):
    Nordeste: AL, BA, CE, MA, PB, PE, PI, RN, SE (CO_UF 21-29)
    Sudeste:  ES, MG, RJ, SP (CO_UF 31-35)
    """
    sg_uf = df["SG_UF"].astype(str).str.strip().str.upper()
    co_uf = pd.to_numeric(df["CO_UF"], errors="coerce")

    nordeste = sg_uf.isin(SIGLAS_NORDESTE) | co_uf.isin(CO_UF_NORDESTE)
    sudeste = sg_uf.isin(SIGLAS_SUDESTE) | co_uf.isin(CO_UF_SUDESTE)
    return df[nordeste | sudeste]


def preparar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Renomeia colunas, adiciona a flag `ativo` e ajusta os tipos para a carga."""
    df = df.rename(columns=COLUMN_MAP)
    df["ativo"] = 1  # exclusão lógica

    colunas_numericas = [
        "co_entidade",
        "co_uf",
        "co_municipio",
        "nu_ano_censo",
        "qt_mat_bas",
        "qt_mat_inf",
        "qt_mat_fund",
        "qt_mat_med",
        "qt_mat_prof",
        "qt_mat_eja",
        "qt_mat_esp",
    ]
    for col in colunas_numericas:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # .str.strip() preserva os nulos (o astype(str) os transformaria em "nan")
    for col in ["no_entidade", "no_uf", "sg_uf", "no_municipio"]:
        df[col] = df[col].str.strip()

    return df[COLUNAS_TABELA]


def conectar(banco: dict):
    try:
        return psycopg2.connect(**banco)
    except psycopg2.OperationalError as erro:
        # A mensagem do psycopg2 não inclui a senha.
        log.error(
            "Não foi possível conectar ao PostgreSQL em %s:%s (banco %s, usuário %s).\n"
            "Verifique se o container está de pé ('docker ps') e se as credenciais "
            "do .env estão corretas.\nDetalhe: %s",
            banco["host"],
            banco["port"],
            banco["dbname"],
            banco["user"],
            str(erro).strip(),
        )
        return None


def criar_tabela_se_necessario(cursor) -> None:
    """Cria a tabela `instituicoes` e seus índices, com o mesmo schema da API."""
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABELA} (
            id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            no_entidade TEXT NOT NULL,
            co_entidade INTEGER NOT NULL,
            no_uf TEXT,
            sg_uf TEXT,
            co_uf INTEGER,
            no_municipio TEXT,
            co_municipio INTEGER,
            nu_ano_censo INTEGER,
            qt_mat_bas INTEGER,
            qt_mat_inf INTEGER,
            qt_mat_fund INTEGER,
            qt_mat_med INTEGER,
            qt_mat_prof INTEGER,
            qt_mat_eja INTEGER,
            qt_mat_esp INTEGER,
            ativo INTEGER NOT NULL DEFAULT 1
        )
        """)
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{TABELA}_co_entidade "
        f"ON {TABELA} (co_entidade, ativo)"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{TABELA}_listagem "
        f"ON {TABELA} (ativo, co_entidade)"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{TABELA}_sg_uf ON {TABELA} (sg_uf)"
    )


def contar_registros(cursor) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM {TABELA}")
    return cursor.fetchone()[0]


def carregar_dataframe(cursor, df: pd.DataFrame) -> None:
    """Insere o bloco tratado em um único comando multi-linha (execute_values).

    Escolhido em vez de COPY porque aceita None como NULL sem serializar CSV
    e mantém a carga bloco a bloco dentro da mesma transação.
    """
    df = df.astype(object).where(df.notna(), None)  # NaN/NA -> NULL
    execute_values(
        cursor,
        f"INSERT INTO {TABELA} ({', '.join(df.columns)}) VALUES %s",
        list(df.itertuples(index=False, name=None)),
        page_size=5_000,
    )


def conferir_carga(cursor, totais_lidos: dict[str, int]) -> bool:
    """Compara o que está no banco (COUNT e GROUP BY sg_uf) com o que foi lido."""
    cursor.execute(f"SELECT sg_uf, COUNT(*) FROM {TABELA} GROUP BY sg_uf ORDER BY sg_uf")
    totais_banco = {uf: total for uf, total in cursor.fetchall()}
    total_banco = contar_registros(cursor)

    log.info("Conferência no banco: %d registros. Por UF: %s", total_banco, totais_banco)
    if totais_banco != totais_lidos:
        log.error("Divergência entre o lido (%s) e o gravado (%s).", totais_lidos, totais_banco)
        return False
    return True


def executar_carga(conexao, csv_path: Path, encoding: str) -> bool:
    """Carrega o CSV inteiro em uma única transação. Retorna True se confirmada."""
    total_lido = 0
    total_inserido = 0
    totais_por_uf: dict[str, int] = {}
    ids_vistos: set[int] = set()
    duplicados = 0

    with conexao.cursor() as cursor:
        criar_tabela_se_necessario(cursor)

        existentes = contar_registros(cursor)
        if existentes > 0:
            log.error(
                "A tabela %s já tem %d registros. Carga abortada para não duplicar "
                "dados; nada foi alterado.",
                TABELA,
                existentes,
            )
            conexao.rollback()
            return False

        log.info("Iniciando extração paginada de %s", csv_path.name)
        blocos = pd.read_csv(
            csv_path,
            sep=SEPARATOR,
            encoding=encoding,
            chunksize=CHUNKSIZE,
            low_memory=False,
            usecols=list(COLUMN_MAP.keys()),
        )

        for i, bloco in enumerate(blocos, start=1):
            preparado = preparar_dataframe(filtrar_regioes(bloco))
            total_lido += len(bloco)
            total_inserido += len(preparado)

            for uf, qtd in preparado["sg_uf"].value_counts().items():
                totais_por_uf[uf] = totais_por_uf.get(uf, 0) + int(qtd)

            for co_entidade in preparado["co_entidade"].dropna():
                if co_entidade in ids_vistos:
                    duplicados += 1
                ids_vistos.add(co_entidade)

            if not preparado.empty:
                carregar_dataframe(cursor, preparado)

            log.info(
                "Bloco %d: linhas lidas no bloco=%d, filtradas/inseridas=%d, "
                "total inserido até agora=%d",
                i,
                len(bloco),
                len(preparado),
                total_inserido,
            )

        log.info(
            "Concluído: %d linhas lidas, %d instituições filtradas e inseridas.",
            total_lido,
            total_inserido,
        )
        log.info("Por UF: %s", dict(sorted(totais_por_uf.items())))
        log.info(
            "co_entidade duplicados no CSV filtrado: %d (nenhuma linha foi descartada).",
            duplicados,
        )
        if total_inserido != TOTAL_ESPERADO or len(totais_por_uf) != 13:
            log.warning(
                "Resultado difere da referência anterior (%d escolas em 13 UFs): "
                "obtido %d em %d UFs.",
                TOTAL_ESPERADO,
                total_inserido,
                len(totais_por_uf),
            )

        if not conferir_carga(cursor, dict(sorted(totais_por_uf.items()))):
            conexao.rollback()
            return False

    conexao.commit()
    return True


def main() -> int:
    try:
        config = carregar_configuracao()
    except ValueError as erro:
        log.error("%s", erro)
        return 1

    csv_path = config["csv_path"]
    if not csv_path.is_file():
        log.error(
            "Arquivo de origem não encontrado: %s\n"
            "Baixe os microdados do Censo Escolar 2025 no INEP, extraia em "
            "datasets/dados_censo_escolar/ ou ajuste CSV_PATH no .env.",
            csv_path,
        )
        return 1

    encoding = detectar_encoding(csv_path)
    validar_colunas_origem(csv_path, SEPARATOR, encoding)

    conexao = conectar(config["banco"])
    if conexao is None:
        return 1

    try:
        if not executar_carga(conexao, csv_path, encoding):
            return 1
        log.info("Carga confirmada (commit) no banco %s.", config["banco"]["dbname"])
        return 0
    except Exception:
        conexao.rollback()
        log.exception("Erro fatal no pipeline; transação revertida, nenhum dado gravado.")
        return 1
    finally:
        conexao.close()


if __name__ == "__main__":
    sys.exit(main())
