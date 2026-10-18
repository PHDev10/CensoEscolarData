import json
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:5000"

TOTAL = 0
FALHAS = []


def requisitar(metodo, caminho, corpo=None, status_esperado=200, descricao=""):
    global TOTAL
    TOTAL += 1
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    requisicao = urllib.request.Request(
        BASE_URL + caminho,
        data=dados,
        method=metodo,
        headers={"Content-Type": "application/json"} if dados else {},
    )
    try:
        with urllib.request.urlopen(requisicao) as resposta:
            status, conteudo = resposta.status, resposta.read()
    except urllib.error.HTTPError as erro:
        status, conteudo = erro.code, erro.read()

    try:
        resposta_json = json.loads(conteudo)
    except json.JSONDecodeError:
        resposta_json = conteudo.decode("utf-8", errors="replace")

    if status == status_esperado:
        print(f"[OK]   {metodo:6} {caminho} -> {status}  {descricao}")
    else:
        print(f"[FAIL] {metodo:6} {caminho} -> {status} (esperado {status_esperado})  {descricao}")
        FALHAS.append(descricao or caminho)
    return status, resposta_json


print("--- Instituições de ensino ---")

_, lista = requisitar("GET", "/instituicaoensino", status_esperado=200,
                      descricao="lista todas as instituições")
assert len(lista) > 0, "A lista de instituições não deveria estar vazia"

requisitar("GET", "/instituicaoensino?codigo=25096850", status_esperado=200,
           descricao="busca instituição por querystring 'codigo'")
requisitar("GET", "/instituicaoensino?codigo=99999999", status_esperado=404,
           descricao="busca por código inexistente retorna 404")
requisitar("GET", "/instituicaoensino?codigo=abc", status_esperado=400,
           descricao="busca por código inválido retorna 400")
requisitar("GET", "/instituicaoensino/25139401", status_esperado=200,
           descricao="busca instituição por ID na URL")
requisitar("GET", "/instituicaoensino/0", status_esperado=404,
           descricao="busca por ID inexistente retorna 404")

novo_cod = 25999999
requisitar("POST", "/instituicaoensino",
           corpo={"co_entidade": novo_cod, "no_entidade": "ESCOLA DE TESTES LTDA", "sg_uf": "PB"},
           status_esperado=201, descricao="cria nova instituição")
requisitar("POST", "/instituicaoensino",
           corpo={"co_entidade": novo_cod, "no_entidade": "DUPLICADA LTDA"},
           status_esperado=409, descricao="criação com código duplicado retorna 409")
requisitar("POST", "/instituicaoensino", corpo={"no_entidade": "SEM CODIGO"},
           status_esperado=400, descricao="criação sem 'co_entidade' retorna 400")
requisitar("POST", "/instituicaoensino", None, status_esperado=400,
           descricao="criação sem corpo JSON retorna 400")

requisitar("PUT", f"/instituicaoensino/{novo_cod}",
           corpo={"no_entidade": "ESCOLA DE TESTES ATUALIZADA", "qt_mat_bas": 100},
           status_esperado=200, descricao="atualiza instituição existente")
_, atualizada = requisitar("GET", f"/instituicaoensino/{novo_cod}", status_esperado=200,
                           descricao="confirma atualização persistida")
assert atualizada["no_entidade"] == "ESCOLA DE TESTES ATUALIZADA", "Atualização não persistida!"
assert atualizada["qt_mat_bas"] == 100, "Novo campo não persistido!"
requisitar("PUT", f"/instituicaoensino/{novo_cod}", corpo={"co_entidade": 12345},
           status_esperado=400, descricao="alterar 'co_entidade' retorna 400")
requisitar("PUT", "/instituicaoensino/0", corpo={"no_entidade": "FANTASMA"},
           status_esperado=404, descricao="atualização de inexistente retorna 404")

requisitar("DELETE", f"/instituicaoensino/{novo_cod}", status_esperado=200,
           descricao="remove instituição criada")
requisitar("DELETE", f"/instituicaoensino/{novo_cod}", status_esperado=404,
           descricao="remoção repetida retorna 404")
requisitar("GET", f"/instituicaoensino/{novo_cod}", status_esperado=404,
           descricao="confirma remoção persistida")

print("\n--- Usuários ---")

_, usuarios = requisitar("GET", "/usuarios", status_esperado=200,
                         descricao="lista todos os usuários")
assert len(usuarios) > 0, "A lista de usuários não deveria estar vazia"

requisitar("GET", "/usuarios/1", status_esperado=200, descricao="busca usuário por ID")
requisitar("GET", "/usuarios/9999", status_esperado=404, descricao="usuário inexistente retorna 404")

requisitar("POST", "/usuarios",
           corpo={"nome": "Diego Teste", "email": "diego.teste@example.com", "perfil": "pesquisador"},
           status_esperado=201, descricao="cria novo usuário (id automático)")
requisitar("POST", "/usuarios",
           corpo={"nome": "Duplicado", "email": "diego.teste@example.com"},
           status_esperado=409, descricao="e-mail duplicado retorna 409")
requisitar("POST", "/usuarios", corpo={"nome": "Sem Email"}, status_esperado=400,
           descricao="criação sem 'email' retorna 400")

requisitar("PUT", "/usuarios/1", corpo={"ativo": False}, status_esperado=200,
           descricao="atualiza usuário existente")
_, atualizado = requisitar("GET", "/usuarios/1", status_esperado=200,
                           descricao="confirma atualização persistida")
assert atualizado["ativo"] is False, "Atualização de usuário não persistida!"
requisitar("PUT", "/usuarios/1", corpo={"id": 50}, status_esperado=400,
           descricao="alterar 'id' do usuário retorna 400")
requisitar("PUT", "/usuarios/9999", corpo={"nome": "Fantasma"}, status_esperado=404,
           descricao="atualização de usuário inexistente retorna 404")

_, usuarios = requisitar("GET", "/usuarios", status_esperado=200,
                         descricao="recarrega lista para localizar id criado")
id_criado = next(u["id"] for u in usuarios if u["email"] == "diego.teste@example.com")
requisitar("DELETE", f"/usuarios/{id_criado}", status_esperado=200, descricao="remove usuário criado")
requisitar("DELETE", f"/usuarios/{id_criado}", status_esperado=404, descricao="remoção repetida retorna 404")

print(f"\n{'=' * 60}")
if FALHAS:
    print(f"Resultado: {TOTAL - len(FALHAS)}/{TOTAL} testes passaram. Falhas:")
    for falha in FALHAS:
        print(f"  - {falha}")
    raise SystemExit(1)
print(f"Resultado: {TOTAL}/{TOTAL} testes passaram. Persistência nos arquivos JSON OK!")
