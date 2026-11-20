"""Executa os comandos reais no PostgreSQL local e grava a saída de cada um (texto UTF-8),
para virar figura no artigo. Rodar na raiz do projeto, com o servidor ligado (porta 5433).

Uso: python docs/entrega_abd/gerar_evidencias.py [pasta_de_saida]
"""
import os
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else RAIZ / "docs/entrega_abd/evidencias")
OUT.mkdir(parents=True, exist_ok=True)
BIN = pathlib.Path.home() / "tools/pg/pgsql/bin"
# As mensagens do psql saem em cp1252; usar a mesma codificação no cliente evita texto misturado.
ENV = dict(os.environ, PGCLIENTENCODING="WIN1252")
PSQL = [str(BIN / "psql.exe"), "-h", "localhost", "-p", "5433", "-U", "postgres"]
BASE = PSQL + ["-d", "residuos_sinisa", "-a", "-q"]

BLOCOS = {
    "01_estrutura": r"""\pset pager off
\dn staging|sinisa
\dt sinisa.*
\dv sinisa.*
""",
    "02_tabela_fato": r"""\pset pager off
\d sinisa.resultado_indicador
""",
    "04_carga": r"""\pset pager off
\pset null '(nulo)'
SELECT cod_ibge, nom_mun, respondeu, irs0001, irs3002
FROM staging.stg_planilha
WHERE respondeu <> 'Sim'
LIMIT 3;
SELECT (SELECT count(*) FROM staging.stg_planilha)                 AS linhas_staging,
       (SELECT count(*) FROM sinisa.municipio)                     AS municipios,
       (SELECT count(*) FROM sinisa.municipio WHERE respondeu)     AS respondentes,
       (SELECT count(*) FROM sinisa.resultado_indicador)           AS linhas_fato,
       (SELECT count(*) FROM sinisa.municipio WHERE respondeu) * 6 AS respondentes_x_6;
""",
    "06_integridade": r"""\pset pager off
BEGIN;
INSERT INTO sinisa.resultado_indicador (cod_ibge, codigo_indicador, ano_referencia, valor) VALUES ('3550308', 'IRS3002', 2024, -5);
ROLLBACK;
BEGIN;
INSERT INTO sinisa.resultado_indicador (cod_ibge, codigo_indicador, ano_referencia, valor) VALUES ('9999999', 'IRS3002', 2024, 10);
ROLLBACK;
BEGIN;
INSERT INTO sinisa.resultado_indicador (cod_ibge, codigo_indicador, ano_referencia, valor) VALUES ('3550308', 'IRS3002', 2024, 10);
ROLLBACK;
SELECT count(*) AS linhas_fato_depois FROM sinisa.resultado_indicador;
""",
    "07_views": r"""\pset pager off
SELECT nome_municipio, uf, populacao_total,
       round(irs0001_cobertura_coleta::numeric, 1)      AS cobertura_coleta,
       round(irs3002_disposicao_inadequada::numeric, 1) AS disposicao_inadequada
FROM sinisa.vw_municipio_indicadores
WHERE uf = 'SP' AND nome_municipio IN ('São Paulo', 'São Bernardo do Campo', 'Santo André')
ORDER BY populacao_total DESC;
SELECT uf, media_simples, media_ponderada, mediana,
       rank() OVER (ORDER BY media_simples DESC) AS posicao
FROM sinisa.vw_resumo_uf
ORDER BY posicao
LIMIT 5;
""",
    "08_explain": r"""\pset pager off
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, BUFFERS OFF)
SELECT avg(valor) FROM sinisa.resultado_indicador WHERE codigo_indicador = 'IRS3002';
SET enable_indexscan = off;
SET enable_bitmapscan = off;
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, BUFFERS OFF)
SELECT avg(valor) FROM sinisa.resultado_indicador WHERE codigo_indicador = 'IRS3002';
RESET enable_indexscan;
RESET enable_bitmapscan;
""",
    "09_seguranca": r"""\pset pager off
\du leitor_sinisa
\dp sinisa.municipio
\c residuos_sinisa leitor_sinisa
SELECT current_user, count(*) AS leitura_permitida FROM sinisa.municipio;
DELETE FROM sinisa.municipio;
\c residuos_sinisa postgres
SELECT count(*) AS municipios_depois FROM sinisa.municipio;
""",
    "10_armazenamento": r"""\pset pager off
\db
SELECT c.relname AS objeto,
       CASE c.relkind WHEN 'r' THEN 'tabela' ELSE 'indice' END AS tipo,
       coalesce(t.spcname, 'pg_default') AS tablespace
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_tablespace t ON t.oid = c.reltablespace
WHERE n.nspname = 'sinisa' AND c.relkind IN ('r', 'i')
ORDER BY c.relkind DESC, c.relname;
SELECT pg_relation_filepath('sinisa.resultado_indicador') AS arquivo_da_tabela_fato,
       current_setting('block_size')                     AS bytes_por_pagina;
SELECT pg_size_pretty(pg_database_size('residuos_sinisa'))             AS banco_inteiro,
       pg_size_pretty(pg_table_size('sinisa.resultado_indicador'))     AS tabela_fato,
       pg_size_pretty(pg_indexes_size('sinisa.resultado_indicador'))   AS indices_da_fato,
       pg_size_pretty(pg_total_relation_size('staging.stg_planilha'))  AS staging;
""",
}


def rodar(cmd, entrada=None):
    r = subprocess.run(cmd, input=entrada, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       cwd=RAIZ, env=ENV, timeout=300)
    return r.stdout.decode("cp1252", errors="replace").replace("\r\n", "\n")


def alinhar_identidade():
    """Os INSERTs recusados dos testes consomem valores da identidade (ela não volta no ROLLBACK).
    Alinha a sequência ao maior id existente para que a evidência mostre o próximo id real (29125)."""
    rodar(PSQL + ["-d", "residuos_sinisa", "-q", "-c",
                  "SELECT setval(pg_get_serial_sequence('sinisa.resultado_indicador','id_resultado'), "
                  "(SELECT max(id_resultado) FROM sinisa.resultado_indicador));"])


# 05: saída da validação sem repetir o texto do arquivo (ele está no Apêndice D)
r05 = subprocess.run(PSQL + ["-d", "residuos_sinisa", "-q", "-f", str(RAIZ / "sql/postgres/04_validacao.sql")],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=RAIZ, env=dict(os.environ, PGCLIENTENCODING="UTF8"))
txt05 = "\\i sql/postgres/04_validacao.sql\n" + r05.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
(OUT / "05_validacao.txt").write_text(txt05, encoding="utf-8")
print("05_validacao", len(txt05.splitlines()), "linhas")

for nome, sql in BLOCOS.items():
    if nome == "06_integridade":
        alinhar_identidade()
    if nome == "08_explain":   # descarta as linhas mortas deixadas pelos INSERTs recusados do bloco 06
        rodar(PSQL + ["-d", "residuos_sinisa", "-q", "-c", "VACUUM ANALYZE sinisa.resultado_indicador;"])
    txt = rodar(BASE, sql.encode("cp1252"))
    (OUT / f"{nome}.txt").write_text(txt, encoding="utf-8")
    print(nome, len(txt.splitlines()), "linhas")

# --- 11: backup e restauração (comandos reais; banco descartável residuos_teste) -----------
alinhar_identidade()
bkp = pathlib.Path(os.environ.get("TEMP", ".")) / "backup_residuos_sinisa.sql"
linhas = []


def passo(mostrado, cmd):
    linhas.append("$ " + mostrado)
    saida = rodar(cmd).rstrip()
    if saida:
        linhas.append(saida)


passo("pg_dump -h localhost -p 5433 -U postgres -d residuos_sinisa --no-owner -f backup_residuos_sinisa.sql",
      [str(BIN / "pg_dump.exe"), "-h", "localhost", "-p", "5433", "-U", "postgres",
       "-d", "residuos_sinisa", "--no-owner", "-f", str(bkp)])
linhas.append("$ ls -l backup_residuos_sinisa.sql")
linhas.append(f"{bkp.stat().st_size:,} bytes".replace(",", "."))
passo('psql -d postgres -c "CREATE DATABASE residuos_teste ..."',
      PSQL + ["-d", "postgres", "-q", "-c", "DROP DATABASE IF EXISTS residuos_teste;",
              "-c", "CREATE DATABASE residuos_teste ENCODING 'UTF8' TEMPLATE template0 LC_COLLATE 'C' LC_CTYPE 'C';"])
passo("psql -d residuos_teste -v ON_ERROR_STOP=1 -q -f backup_residuos_sinisa.sql",
      PSQL + ["-d", "residuos_teste", "-v", "ON_ERROR_STOP=1", "-q", "-f", str(bkp)])
consulta = ("SELECT (SELECT count(*) FROM sinisa.municipio) AS municipios, "
            "(SELECT count(*) FROM sinisa.resultado_indicador) AS fato, "
            "(SELECT sum(populacao_total) FROM sinisa.municipio) AS populacao, "
            "(SELECT count(*) FROM staging.stg_planilha) AS staging, "
            "(SELECT round(avg(valor)::numeric,2) FROM sinisa.resultado_indicador WHERE codigo_indicador='IRS3002') AS media_irs3002;")
for banco in ("residuos_sinisa", "residuos_teste"):
    passo(f'psql -d {banco} -c "SELECT contagens, soma e media ..."', PSQL + ["-d", banco, "-c", consulta])
passo('psql -d postgres -c "DROP DATABASE residuos_teste;"   -- limpa o banco de teste',
      PSQL + ["-d", "postgres", "-q", "-c", "DROP DATABASE residuos_teste;"])
(OUT / "11_backup_restore.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
print("11_backup_restore", len(linhas), "linhas")
