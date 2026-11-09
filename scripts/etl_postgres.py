"""
ETL do SINISA para PostgreSQL (camada de banco de dados do projeto).

Fluxo, no estilo ELT:
    1. EXTRAÇÃO   lê a planilha do SINISA (reaproveita scripts/etl_sqlite.py).
    2. CARGA BRUTA grava a planilha, sem tratamento, em staging.stg_planilha.
    3. TRANSFORMAÇÃO e CARGA FINAL  limpeza e tipos em SQL, dentro do banco
       (sql/postgres/02_transformacao.sql), gerando o esquema estrela em "sinisa".
    4. VIEWS e papel de leitura (sql/postgres/03_views_e_consultas.sql).
    5. VALIDAÇÃO  verificações de integridade (04_validacao.sql) e comparação dos
       totais com o banco SQLite (dados_tratados/projeto_residuos.db).

Conexão (variáveis de ambiente, com padrão para o Postgres portátil local):
    PGHOST=localhost  PGPORT=5433  PGUSER=postgres  PGPASSWORD=(vazio)  PGDATABASE=residuos_sinisa

Uso, a partir da raiz do projeto:
    python scripts/etl_postgres.py
"""

import os
import sqlite3
import sys

import pandas as pd
import psycopg
import psycopg.sql

from etl_sqlite import (ANO_REFERENCIA, CAMINHO_BANCO as CAMINHO_SQLITE, CAMINHO_EXCEL, CODIGOS_INDICADORES,
                        INDICADORES, ler_planilha)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_SQL = os.path.join(BASE_DIR, "sql", "postgres")

CONEXAO = {
    "host": os.environ.get("PGHOST", "localhost"),
    "port": int(os.environ.get("PGPORT", "5433")),
    "user": os.environ.get("PGUSER", "postgres"),
    "password": os.environ.get("PGPASSWORD", ""),
}
NOME_BANCO = os.environ.get("PGDATABASE", "residuos_sinisa")

# Colunas da planilha que vão para o staging (na ordem de stg_planilha)
COLUNAS_PLANILHA = ["Cod_IBGE", "Nom_Mun", "UF", "Nom_Região", "DFE0001", "Sim/Não"] + CODIGOS_INDICADORES
COLUNAS_STAGING = ["linha_origem", "cod_ibge", "nom_mun", "uf", "nom_regiao", "dfe0001", "respondeu",
                   "irs0001", "irs0005", "irs1004", "irs3001", "irs3002", "irs3010", "ano_referencia"]


def ler_sql(nome):
    with open(os.path.join(PASTA_SQL, nome), encoding="utf-8") as arquivo:
        return arquivo.read()


def criar_banco_se_necessario():
    """Cria o banco residuos_sinisa se ainda não existir (conecta no banco padrão 'postgres')."""
    with psycopg.connect(dbname="postgres", autocommit=True, **CONEXAO) as conn:
        existe = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (NOME_BANCO,)).fetchone()
        if not existe:
            conn.execute(psycopg.sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0 LC_COLLATE 'C' LC_CTYPE 'C'")
                         .format(psycopg.sql.Identifier(NOME_BANCO)))
            print(f"Banco '{NOME_BANCO}' criado.")
        else:
            print(f"Banco '{NOME_BANCO}' já existe (será recriado o conteúdo dos schemas).")


def texto_ou_nulo(valor):
    return None if pd.isna(valor) else str(valor)


def carregar_staging(conn, dados):
    """Cópia fiel da planilha, tudo em texto, com a posição da linha de origem."""
    with conn.cursor() as cur:
        with cur.copy(f"COPY staging.stg_planilha ({', '.join(COLUNAS_STAGING)}) FROM STDIN") as copia:
            for posicao, (_, linha) in enumerate(dados[COLUNAS_PLANILHA].iterrows(), start=1):
                copia.write_row([posicao] + [texto_ou_nulo(linha[c]) for c in COLUNAS_PLANILHA] + [ANO_REFERENCIA])
    return conn.execute("SELECT count(*) FROM staging.stg_planilha").fetchone()[0]


def carregar_catalogo(conn):
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO sinisa.indicador (codigo, nome, unidade, grupo, definicao) VALUES (%s, %s, %s, %s, %s)",
            INDICADORES)


def comparar_com_sqlite(conn):
    """Confere contagens e somas por indicador contra o banco SQLite. Devolve a lista de divergências."""
    if not os.path.exists(CAMINHO_SQLITE):
        print("SQLite não encontrado; comparação ignorada.")
        return []
    lite = sqlite3.connect(CAMINHO_SQLITE)
    divergencias = []
    try:
        pares = [
            ("municípios", "SELECT count(*) FROM municipio", "SELECT count(*) FROM sinisa.municipio"),
            ("respondentes", "SELECT count(*) FROM municipio WHERE respondeu = 1",
             "SELECT count(*) FROM sinisa.municipio WHERE respondeu"),
            ("resultados", "SELECT count(*) FROM resultado_indicador", "SELECT count(*) FROM sinisa.resultado_indicador"),
            ("resultados sinalizados", "SELECT count(*) FROM resultado_indicador WHERE flag_qualidade IS NOT NULL",
             "SELECT count(*) FROM sinisa.resultado_indicador WHERE flag_qualidade IS NOT NULL"),
            ("soma da população", "SELECT sum(populacao_total) FROM municipio", "SELECT sum(populacao_total) FROM sinisa.municipio"),
        ]
        for codigo in CODIGOS_INDICADORES:
            pares.append((f"{codigo}: n e soma",
                          f"SELECT count(*), round(sum(valor), 4) FROM resultado_indicador WHERE codigo_indicador = '{codigo}'",
                          f"SELECT count(*), round(sum(valor)::numeric, 4)::float FROM sinisa.resultado_indicador "
                          f"WHERE codigo_indicador = '{codigo}'"))
        print(f"\n{'Conferência':<28}{'SQLite':>28}{'PostgreSQL':>28}  ok?")
        for nome, sql_lite, sql_pg in pares:
            a = tuple(float(x) if x is not None else None for x in lite.execute(sql_lite).fetchone())
            b = tuple(float(x) if x is not None else None for x in conn.execute(sql_pg).fetchone())
            igual = all(abs(x - y) < 1e-3 for x, y in zip(a, b)) and len(a) == len(b)
            print(f"{nome:<28}{str(a):>28}{str(b):>28}  {'sim' if igual else 'NÃO'}")
            if not igual:
                divergencias.append(nome)
    finally:
        lite.close()
    return divergencias


def executar():
    if not os.path.exists(CAMINHO_EXCEL):
        sys.exit(f"Planilha não encontrada: {CAMINHO_EXCEL}")
    print("1) Extração: lendo a planilha do SINISA...")
    dados = ler_planilha(CAMINHO_EXCEL)
    print(f"   {len(dados)} linhas lidas.")

    try:
        criar_banco_se_necessario()
    except psycopg.OperationalError as erro:
        sys.exit(f"Não consegui conectar ao PostgreSQL em {CONEXAO['host']}:{CONEXAO['port']}.\n"
                 f"Suba o servidor (scripts/postgres_portatil.ps1 iniciar) e tente de novo.\nDetalhe: {erro}")

    with psycopg.connect(dbname=NOME_BANCO, **CONEXAO) as conn:
        print("2) Esquema: recriando os schemas 'staging' e 'sinisa'...")
        conn.execute(ler_sql("01_schema.sql"))
        carregar_catalogo(conn)

        print("3) Carga bruta: gravando a planilha em staging.stg_planilha...")
        n_staging = carregar_staging(conn, dados)
        print(f"   {n_staging} linhas no staging.")

        print("4) Transformação em SQL: limpeza e carga no esquema estrela...")
        conn.execute(ler_sql("02_transformacao.sql"))
        conn.execute(ler_sql("03_views_e_consultas.sql"))
        conn.commit()

        print("5) Validação...")
        problemas = 0
        for verificacao, n in conn.execute(ler_sql("04_validacao.sql")).fetchall():
            print(f"   {'OK ' if n == 0 else 'ERRO'} {verificacao}: {n}")
            problemas += n
        divergencias = comparar_com_sqlite(conn)

    if problemas or divergencias:
        sys.exit("\nCarga concluída COM PROBLEMAS (veja acima).")
    print("\nETL para PostgreSQL finalizado sem problemas.")


if __name__ == "__main__":
    executar()
