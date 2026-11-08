import sqlite3
from contextlib import contextmanager

from helpers.environment import LIMIT_MAXIMO_PAGINA
from helpers.logger import logger
from services.excecoes import ErroInternoError, ValidacaoError

TIPOS_DELETE_VALIDOS = ("logico", "fisico")


class BaseService:
    """Regras comuns aos services: paginação, validação do corpo e do tipo de delete."""

    limit_padrao = None

    def __init__(self, repositorio):
        self.repositorio = repositorio

    def listar(self, page=None, limit=None):
        """Retorna (registros, total). O total é None quando não há paginação."""
        paginacao = self._ler_paginacao(page, limit)
        if paginacao is None:
            return self.repositorio.listar(), None

        page, limit = paginacao
        total = self.repositorio.contar_ativos()
        return self.repositorio.listar(page=page, limit=limit), total

    def _ler_paginacao(self, raw_page, raw_limit):
        if raw_page is None and raw_limit is None:
            return None

        page, limit = 1, self.limit_padrao
        try:
            if raw_page is not None:
                page = int(raw_page)
            if raw_limit is not None:
                limit = int(raw_limit)
        except (TypeError, ValueError):
            raise ValidacaoError(
                "Os parâmetros 'page' e 'limit' devem ser números inteiros"
            )

        if page < 1 or (limit is not None and limit < 1):
            raise ValidacaoError(
                "Os parâmetros 'page' e 'limit' devem ser números inteiros positivos"
            )

        if limit is not None:
            limit = min(limit, LIMIT_MAXIMO_PAGINA)
        return page, limit

    @staticmethod
    def _validar_corpo(corpo):
        if not isinstance(corpo, dict) or not corpo:
            raise ValidacaoError("Corpo da requisição inválido: envie um JSON válido")

    @staticmethod
    def _validar_tipo_delete(tipo):
        if tipo not in TIPOS_DELETE_VALIDOS:
            raise ValidacaoError("O parâmetro 'tipo' deve ser 'logico' ou 'fisico'")

    @staticmethod
    @contextmanager
    def _erro_interno(mensagem):
        """Converte falhas do SQLite em ErroInternoError, registrando o log."""
        try:
            yield
        except sqlite3.Error:
            logger.exception(mensagem)
            raise ErroInternoError(mensagem)
