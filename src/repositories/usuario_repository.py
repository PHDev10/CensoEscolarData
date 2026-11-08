from repositories.base_repository import BaseRepository


class UsuarioRepository(BaseRepository):
    tabela = "usuarios"
    pk = "id"
    ordem_padrao = "id"
    renomear = {"ativo": "ativo_usuario"}

    proximo_id_sql = "SELECT COALESCE(MAX(id), 0) + 1 AS proximo FROM usuarios"

    def proximo_id(self):
        linha = self._executar(self.proximo_id_sql, fetch="one")
        return linha["proximo"]

    def id_ja_utilizado(self, id_valor):
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
