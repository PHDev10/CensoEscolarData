from helpers.logger import logger
from repositories.usuario_repository import UsuarioRepository
from services.base_service import BaseService
from services.excecoes import ConflitoError, NaoEncontradoError, ValidacaoError

NAO_ENCONTRADO = "Usuário não encontrado"


class UsuarioService(BaseService):
    def __init__(self, repositorio=None):
        super().__init__(repositorio or UsuarioRepository())

    def obter(self, id_usuario):
        usuario = self.repositorio.obter(id_usuario)
        if usuario is None:
            raise NaoEncontradoError(NAO_ENCONTRADO)
        return usuario

    def criar(self, corpo):
        self._validar_corpo(corpo)
        if not corpo.get("nome"):
            raise ValidacaoError("O campo 'nome' é obrigatório")
        if not corpo.get("email"):
            raise ValidacaoError("O campo 'email' é obrigatório")

        dados = dict(corpo)
        with self._erro_interno("Erro interno ao salvar o usuário"):
            if self.repositorio.existe_email(dados["email"]):
                raise ConflitoError("Já existe um usuário com este e-mail")

            id_usuario = dados.get("id")
            if id_usuario is None:
                dados["id"] = self.repositorio.proximo_id()
            elif (
                isinstance(id_usuario, bool)
                or not isinstance(id_usuario, int)
                or self.repositorio.id_ja_utilizado(id_usuario)
            ):
                raise ValidacaoError(
                    "O campo 'id' deve ser um número inteiro ainda não utilizado"
                )

            return self.repositorio.inserir(dados)

    def atualizar(self, id_usuario, corpo):
        self._validar_corpo(corpo)
        if "id" in corpo and corpo["id"] != id_usuario:
            raise ValidacaoError("Não é permitido alterar o 'id' do usuário")

        with self._erro_interno("Erro interno ao atualizar o usuário"):
            atualizado = self.repositorio.atualizar(id_usuario, corpo)
        if atualizado is None:
            raise NaoEncontradoError(NAO_ENCONTRADO)
        return atualizado

    def remover(self, id_usuario, tipo):
        self._validar_tipo_delete(tipo)

        with self._erro_interno("Erro interno ao remover o usuário"):
            removido = self.repositorio.remover(id_usuario, tipo=tipo)
        if removido is None:
            raise NaoEncontradoError(NAO_ENCONTRADO)

        logger.info("Usuário %s removido (delete %s)", id_usuario, tipo)
        mensagem = (
            "Usuário excluído logicamente (ativo = 0)"
            if tipo == "logico"
            else "Usuário excluído fisicamente do banco de dados"
        )
        return removido, mensagem
