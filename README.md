# CensoEscolarData

Extrai os microdados do Censo Escolar 2025 (INEP), filtra as escolas do Nordeste e do Sudeste e faz a **carga inicial** na tabela `instituicoes` de um PostgreSQL rodando em Docker. Este repositório não tem endpoints: a API que consome o banco é o CensoEscolarApi.

## 1. Baixar o CSV

Baixe os microdados do Censo Escolar 2025: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar

Extraia o conteúdo em `datasets/dados_censo_escolar/`. O arquivo usado é:

```
datasets/dados_censo_escolar/microdados_censo_escolar_2025_v2/dados/Tabela_Matricula_2025_V2.csv
```

A pasta `datasets/dados_censo_escolar/` é ignorada pelo git.

## 2. Subir o PostgreSQL (Docker)

Imagem: https://hub.docker.com/_/postgres

```bash
docker run --name postgres20262 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=<sua_senha_aqui> \
  -e POSTGRES_DB=censoescolar \
  -p 5435:5432 \
  -d postgres:18.7-alpine3.24
```

- Container `postgres20262`, banco `censoescolar`, usuário `postgres`.
- Porta `5435` no host (evita conflito com um Postgres local na `5432`) apontando para a `5432` do container.
- As variáveis `POSTGRES_*` só valem na **primeira** inicialização do container.
- Se for usar volume, nesta versão o ponto de montagem é `/var/lib/postgresql` (e não `/var/lib/postgresql/data`).

## 3. Configurar o `.env`

```bash
cp .env.example .env
```

Edite o `.env` e troque `<sua_senha_aqui>` pela mesma senha usada no `docker run`. O `.env` não é versionado.

| Variável | Significado |
|---|---|
| `DB_HOST` / `DB_PORT` | Endereço e porta do host (`localhost` / `5435`) |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Banco, usuário e senha |
| `CSV_PATH` | Caminho do CSV, relativo à raiz do projeto |

## 4. Instalar as dependências

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`psycopg2-binary` é a versão com o `libpq` pré-compilado, então não é preciso compilar nada.

## 5. Executar a carga

```bash
python src/extractor.py
```

- Tudo é gravado em **uma única transação**: se algo falhar, nada fica gravado.
- Se a tabela `instituicoes` já tiver registros, a carga é abortada sem alterar nada.
- Ao final, o script confere `COUNT(*)` e `GROUP BY sg_uf` no banco contra o que foi lido. Referência: 120.222 escolas em 13 UFs.

## 6. Conferir no banco

```bash
docker exec -it postgres20262 psql -U postgres -d censoescolar
```

```sql
SELECT COUNT(*) FROM instituicoes;
SELECT sg_uf, COUNT(*) FROM instituicoes GROUP BY sg_uf ORDER BY sg_uf;
\d instituicoes
\q
```

## Comandos básicos do Docker

```bash
docker ps                          # containers em execução
docker ps -a                       # todos os containers (inclusive parados)
docker start postgres20262         # inicia
docker stop postgres20262          # para
docker restart postgres20262       # reinicia
docker logs postgres20262          # logs (-f para acompanhar)
docker exec -it postgres20262 sh   # shell dentro do container
```
