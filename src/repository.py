import logging
import sqlite3

from database import obter_conexao

logger = logging.getLogger("censo_escolar")

CAMPOS_IGNORADOS_ESCRITA = ("ativo",)


class RepositorioBase:
    """Operações CRUD + exclusão lógica/física genéricas para uma tabela."""

    tabela = ""
    pk = ""
    renomear = {}

    def _executar(self, sql, parametros=(), fetch="all"):
        """Executa uma query parametrizada com log de erro e conexão segura."""
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
        """Filtra o corpo da requisição para chaves que são colunas reais da tabela."""
        campos = {}
        for chave, valor in corpo.items():
            coluna = self.renomear.get(chave, chave)
            if chave in CAMPOS_IGNORADOS_ESCRITA or (ignorar_pk and coluna == self.pk):
                continue
            if coluna in colunas:
                campos[coluna] = valor
        return campos

    # ---------- LEITURA (get by all / get by id) ----------

    def listar(self):
        """get by all: retorna apenas registros ativos (filtro WHERE ativo = 1)."""
        return self._executar(f"SELECT * FROM {self.tabela} WHERE ativo = 1")

    def obter(self, id_valor):
        """get by id: retorna o registro ativo com a PK informada (ou None)."""
        return self._executar(
            f"SELECT * FROM {self.tabela} WHERE {self.pk} = ? AND ativo = 1",
            (id_valor,),
            fetch="one",
        )

    def existe_ativo(self, campo, valor):
        """Verifica duplicidade considerando apenas registros ativos."""
        return (
            self._executar(
                f"SELECT 1 FROM {self.tabela} WHERE {campo} = ? AND ativo = 1",
                (valor,),
                fetch="one",
            )
            is not None
        )

    def inserir(self, dados):
        """Insere um registro a partir do corpo (dict) da requisição."""
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
        """Atualiza (merge parcial) apenas campos válidos de um registro ativo."""
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
        """Remove um registro por exclusão lógica (ativo = 0) ou física (DELETE).

        Retorna a linha removida (pré-operação) ou None se não houver registro
        compatível (inexistente ou, no delete lógico, já inativo).
        """
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


class InstituicaoRepository(RepositorioBase):
    """Repository da tabela 'instituicoes' (PK natural: co_entidade)."""

    tabela = "instituicoes"
    pk = "co_entidade"


class UsuarioRepository(RepositorioBase):
    """Repository da tabela 'usuarios' (PK: id)."""

    tabela = "usuarios"
    pk = "id"
    renomear = {"ativo": "ativo_usuario"}

    proximo_id_sql = "SELECT COALESCE(MAX(id), 0) + 1 AS proximo FROM usuarios"

    def proximo_id(self):
        linha = self._executar(self.proximo_id_sql, fetch="one")
        return linha["proximo"]

    def id_ja_utilizado(self, id_valor):
        """Verifica a PK entre TODOS os registros (ativos e inativos)."""
        return (
            self._executar(
                f"SELECT 1 FROM {self.tabela} WHERE {self.pk} = ?",
                (id_valor,),
                fetch="one",
            )
            is not None
        )

    def existe_email(self, email):
        return self.existe_ativo("email", email)
