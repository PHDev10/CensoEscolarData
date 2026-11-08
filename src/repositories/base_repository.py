import sqlite3

from helpers.database import obter_conexao
from helpers.logger import logger

CAMPOS_IGNORADOS_ESCRITA = ("ativo",)


class BaseRepository:
    """Operações CRUD + exclusão lógica e física genéricas para uma tabela."""

    tabela = ""
    pk = ""
    ordem_padrao = ""
    renomear = {}

    def _executar(self, sql, parametros=(), fetch="all"):
        """Executa uma query parametrizada"""
        conexao = obter_conexao()
        try:
            cursor = conexao.execute(sql, parametros)
            if fetch == "all":
                resultado = cursor.fetchall()
            elif fetch == "one":
                resultado = cursor.fetchone()
            else:
                resultado = None
            conexao.commit()
            return resultado
        except sqlite3.Error:
            logger.error("Falha na query da tabela '%s': %s", self.tabela, sql)
            raise
        finally:
            conexao.close()

    def _colunas(self):
        conexao = obter_conexao()
        try:
            linhas = conexao.execute(f"PRAGMA table_info({self.tabela})").fetchall()
            return {linha["name"] for linha in linhas}
        finally:
            conexao.close()

    def _mapear_campos(self, corpo, colunas, ignorar_pk=True):
        campos = {}
        for chave, valor in corpo.items():
            coluna = self.renomear.get(chave, chave)
            if chave in CAMPOS_IGNORADOS_ESCRITA or (ignorar_pk and coluna == self.pk):
                continue
            if coluna in colunas:
                campos[coluna] = valor
        return campos

    def listar(self, page=None, limit=None):
        sql = f"SELECT * FROM {self.tabela} WHERE ativo = 1"
        if self.ordem_padrao:
            sql += f" ORDER BY {self.ordem_padrao}"
        if page is not None and limit is not None:
            offset = (page - 1) * limit
            sql += f" LIMIT ? OFFSET ?"
            return self._executar(sql, (limit, offset))
        return self._executar(sql)

    def contar_ativos(self):
        linha = self._executar(
            f"SELECT COUNT(*) AS total FROM {self.tabela} WHERE ativo = 1", fetch="one"
        )
        return linha["total"] if linha else 0

    def obter(self, id_valor):
        return self._executar(
            f"SELECT * FROM {self.tabela} WHERE {self.pk} = ? AND ativo = 1",
            (id_valor,),
            fetch="one",
        )

    def existe_ativo(self, campo, valor):
        return (
            self._executar(
                f"SELECT 1 FROM {self.tabela} WHERE {campo} = ? AND ativo = 1",
                (valor,),
                fetch="one",
            )
            is not None
        )

    def inserir(self, dados):
        colunas = self._colunas()
        campos = self._mapear_campos(dados, colunas, ignorar_pk=False)
        if not campos:
            logger.error("Nenhum campo válido para inserir em '%s'", self.tabela)
            raise sqlite3.OperationalError("Nenhum campo válido para inserção")
        nomes = list(campos)
        sql = (
            f"INSERT INTO {self.tabela} ({', '.join(nomes)}) "
            f"VALUES ({', '.join('?' * len(nomes))})"
        )
        if campos.get(self.pk) is not None:
            self._executar(
                f"DELETE FROM {self.tabela} WHERE {self.pk} = ? AND ativo = 0",
                (campos[self.pk],),
                fetch=None,
            )
        self._executar(sql, tuple(campos.values()), fetch=None)
        logger.info(
            "Registro inserido em '%s' (chave: %s)", self.tabela, campos.get(self.pk)
        )
        return self.obter(campos[self.pk])

    def atualizar(self, id_valor, dados):
        if self.obter(id_valor) is None:
            return None
        campos = self._mapear_campos(dados, self._colunas())
        if campos:
            atribuicoes = ", ".join(f"{coluna} = ?" for coluna in campos)
            sql = f"UPDATE {self.tabela} SET {atribuicoes} WHERE {self.pk} = ?"
            self._executar(sql, tuple(campos.values()) + (id_valor,), fetch=None)
            logger.info("Registro %s atualizado em '%s'", id_valor, self.tabela)
        return self.obter(id_valor)

    def remover(self, id_valor, tipo="logico"):
        existente = self._executar(
            f"SELECT * FROM {self.tabela} WHERE {self.pk} = ?", (id_valor,), fetch="one"
        )
        if existente is None:
            return None

        if tipo == "logico":
            if not existente["ativo"]:
                return None
            self._executar(
                f"UPDATE {self.tabela} SET ativo = 0 WHERE {self.pk} = ?",
                (id_valor,),
                fetch=None,
            )
            logger.info("Exclusão LÓGICA em '%s' (chave: %s)", self.tabela, id_valor)
        else:
            self._executar(
                f"DELETE FROM {self.tabela} WHERE {self.pk} = ?",
                (id_valor,),
                fetch=None,
            )
            logger.info("Exclusão FÍSICA em '%s' (chave: %s)", self.tabela, id_valor)
        return existente
