from repositories.base_repository import BaseRepository


class InstituicaoEnsinoRepository(BaseRepository):
    tabela = "instituicoes"
    pk = "co_entidade"
    ordem_padrao = "co_entidade"
