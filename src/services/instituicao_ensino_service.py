from helpers.logger import logger
from repositories.instituicao_ensino_repository import InstituicaoEnsinoRepository
from services.base_service import BaseService
from services.excecoes import ConflitoError, NaoEncontradoError, ValidacaoError

NAO_ENCONTRADA = "Instituição de ensino não encontrada"


class InstituicaoEnsinoService(BaseService):
    limit_padrao = 100

    def __init__(self, repositorio=None):
        super().__init__(repositorio or InstituicaoEnsinoRepository())

    def obter(self, co_entidade):
        instituicao = self.repositorio.obter(co_entidade)
        if instituicao is None:
            raise NaoEncontradoError(NAO_ENCONTRADA)
        return instituicao

    def buscar_por_codigo(self, codigo):
        if not codigo.isdigit():
            raise ValidacaoError("O parâmetro 'codigo' deve ser um número inteiro")
        return self.obter(int(codigo))

    def criar(self, corpo):
        self._validar_corpo(corpo)

        co_entidade = corpo.get("co_entidade")
        if isinstance(co_entidade, bool) or not isinstance(co_entidade, int):
            raise ValidacaoError(
                "O campo 'co_entidade' é obrigatório e deve ser um número inteiro"
            )
        if not corpo.get("no_entidade"):
            raise ValidacaoError("O campo 'no_entidade' é obrigatório")

        with self._erro_interno("Erro interno ao salvar a instituição"):
            if self.repositorio.existe_ativo("co_entidade", co_entidade):
                raise ConflitoError(
                    f"Já existe uma instituição com co_entidade {co_entidade}"
                )
            return self.repositorio.inserir(corpo)

    def atualizar(self, co_entidade, corpo):
        self._validar_corpo(corpo)
        if "co_entidade" in corpo and corpo["co_entidade"] != co_entidade:
            raise ValidacaoError(
                "Não é permitido alterar o 'co_entidade' da instituição"
            )

        with self._erro_interno("Erro interno ao atualizar a instituição"):
            atualizada = self.repositorio.atualizar(co_entidade, corpo)
        if atualizada is None:
            raise NaoEncontradoError(NAO_ENCONTRADA)
        return atualizada

    def remover(self, co_entidade, tipo):
        self._validar_tipo_delete(tipo)

        with self._erro_interno("Erro interno ao remover a instituição"):
            removida = self.repositorio.remover(co_entidade, tipo=tipo)
        if removida is None:
            raise NaoEncontradoError(NAO_ENCONTRADA)

        logger.info("Instituição %s removida (delete %s)", co_entidade, tipo)
        mensagem = (
            "Instituição excluída logicamente (ativo = 0)"
            if tipo == "logico"
            else "Instituição excluída fisicamente do banco de dados"
        )
        return removida, mensagem
