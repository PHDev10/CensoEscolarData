class ServicoError(Exception):
    """Base dos erros de regra de negócio. A mensagem é a que o cliente recebe."""


class ValidacaoError(ServicoError):
    """Dados ou parâmetros inválidos"""


class ConflitoError(ServicoError):
    """Operação conflita com um registro já existente"""


class NaoEncontradoError(ServicoError):
    """Registro inexistente (ou inativo)."""


class ErroInternoError(ServicoError):
    """Falha inesperada de infraestrutura (ex: banco de dados)."""
