# CensoEscolarData

API Flask com dados do Censo Escolar 2025, persistidos em SQLite.

Projeto de extração dos dados: https://github.com/PHDev10/CensoEscolarApiRegional

## Arquitetura

O fluxo de uma requisição é **Controller → Service → Repository**:

| Camada | Pasta | Responsabilidade |
|---|---|---|
| Controller | `src/controllers/` | HTTP: lê request, chama o service, devolve JSON e status |
| Service | `src/services/` | Regras de negócio e validações; sinaliza erros com exceções de domínio |
| Repository | `src/repositories/` | Acesso ao banco (SQL parametrizado) |
| Helpers | `src/helpers/` | Configuração (`.env`), conexão/schema do banco, logger, leitura de JSON, tratamento de erros |

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Variáveis de ambiente

Crie o arquivo `.env` a partir do exemplo (o `.env` não é versionado):

```powershell
Copy-Item .env.example .env
```

| Variável | Descrição | Padrão |
|---|---|---|
| `DB_NAME` | Caminho do SQLite, relativo à raiz do projeto | `datasets/censo_escolar.db` |
| `CAMINHO_JSON_INSTITUICOES` | JSON da carga inicial de instituições | `datasets/escolas_pb_matriculas_2025.json` |
| `CAMINHO_JSON_USUARIOS` | JSON da carga inicial de usuários | `datasets/usuarios.json` |
| `FLASK_DEBUG` | Modo debug do Flask (`true`/`false`) | `false` |
| `FLASK_PORT` | Porta do servidor | `5000` |
| `LIMIT_MAXIMO_PAGINA` | Maior valor aceito em `limit` | `1000` |

Se a variável não existir no `.env`, vale o padrão da tabela.

## Execução

```powershell
cd src
python main.py
```

A API sobe em `http://127.0.0.1:5000` (ou na porta definida em `FLASK_PORT`). Na primeira execução, se o banco estiver vazio, ele é criado e populado a partir dos JSONs.

## Rotas

| Método | Rota | Descrição |
|---|---|---|
| GET | `/instituicoesensino` ou `/instituicaoensino` | Lista (aceita `codigo`, `page` e `limit`) |
| GET | `/instituicoesensino/<co_entidade>` | Busca por código |
| POST | `/instituicoesensino` | Cria |
| PUT | `/instituicoesensino/<co_entidade>` | Atualiza |
| DELETE | `/instituicoesensino/<co_entidade>?tipo=logico\|fisico` | Remove (padrão: lógico) |
| GET | `/usuarios` | Lista (aceita `page` e `limit`) |
| GET | `/usuarios/<id>` | Busca por id |
| POST | `/usuarios` | Cria |
| PUT | `/usuarios/<id>` | Atualiza |
| DELETE | `/usuarios/<id>?tipo=logico\|fisico` | Remove (padrão: lógico) |

Com `page` ou `limit`, a resposta traz o total de registros no header `X-Total-Count`.

## Teste

Com a API rodando, em outro terminal:

```powershell
python teste.py
```

O `teste.py` faz POST, PUT e DELETE, **alterando o banco**. Faça uma cópia de `datasets/censo_escolar.db` antes de rodar.
