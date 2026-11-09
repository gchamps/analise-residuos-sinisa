"""Etapa 4: ETL incremental, banco reproduzível e carga segura."""

import sqlite3

import pytest

import etl_sqlite as etl


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """Aponta o ETL para arquivos temporários pequenos."""
    arquivos = {"CAMINHO_EXCEL": tmp_path / "indicadores.xlsx", "CAMINHO_EXCEL_MANEJO": tmp_path / "manejo.xlsx",
                "CAMINHO_SCHEMA": tmp_path / "schema.sql", "CAMINHO_BANCO": tmp_path / "banco.db",
                "CAMINHO_CSV_MUNICIPIOS": tmp_path / "m.csv", "CAMINHO_CSV_RESULTADOS": tmp_path / "r.csv"}
    arquivos["CAMINHO_EXCEL"].write_bytes(b"planilha 1")
    arquivos["CAMINHO_EXCEL_MANEJO"].write_bytes(b"planilha 2")
    arquivos["CAMINHO_SCHEMA"].write_bytes(b"CREATE TABLE etl_meta (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);\n")
    for nome, caminho in arquivos.items():
        monkeypatch.setattr(etl, nome, str(caminho))
    return arquivos


def gravar_banco(caminho, hash_entradas):
    conn = sqlite3.connect(caminho)
    conn.execute("CREATE TABLE etl_meta (chave TEXT PRIMARY KEY, valor TEXT NOT NULL)")
    conn.execute("INSERT INTO etl_meta VALUES ('hash_entradas', ?)", (hash_entradas,))
    conn.commit()
    conn.close()


def test_hash_muda_quando_qualquer_entrada_muda(ambiente):
    base = etl.calcular_hash_entradas()
    assert etl.calcular_hash_entradas() == base                       # estável
    ambiente["CAMINHO_EXCEL"].write_bytes(b"planilha 1 alterada")
    assert etl.calcular_hash_entradas() != base
    ambiente["CAMINHO_EXCEL"].write_bytes(b"planilha 1")
    assert etl.calcular_hash_entradas() == base
    ambiente["CAMINHO_SCHEMA"].write_bytes(b"CREATE TABLE x (a INT);\n")
    assert etl.calcular_hash_entradas() != base


def test_hash_ignora_diferenca_de_fim_de_linha_no_esquema(ambiente):
    ambiente["CAMINHO_SCHEMA"].write_bytes(b"linha 1\nlinha 2\n")
    com_lf = etl.calcular_hash_entradas()
    ambiente["CAMINHO_SCHEMA"].write_bytes(b"linha 1\r\nlinha 2\r\n")
    assert etl.calcular_hash_entradas() == com_lf                     # Windows x Linux


def test_banco_esta_atualizado(ambiente):
    hash_atual = etl.calcular_hash_entradas()
    assert not etl.banco_esta_atualizado(hash_atual)                  # nada gerado ainda
    gravar_banco(ambiente["CAMINHO_BANCO"], hash_atual)
    assert not etl.banco_esta_atualizado(hash_atual)                  # faltam os CSVs
    ambiente["CAMINHO_CSV_MUNICIPIOS"].write_text("x")
    ambiente["CAMINHO_CSV_RESULTADOS"].write_text("x")
    assert etl.banco_esta_atualizado(hash_atual)
    assert not etl.banco_esta_atualizado("outro hash")


def test_banco_sem_tabela_de_metadados_conta_como_desatualizado(ambiente):
    sqlite3.connect(ambiente["CAMINHO_BANCO"]).close()
    ambiente["CAMINHO_CSV_MUNICIPIOS"].write_text("x")
    ambiente["CAMINHO_CSV_RESULTADOS"].write_text("x")
    assert not etl.banco_esta_atualizado(etl.calcular_hash_entradas())


def test_executar_etl_pula_quando_atualizado(ambiente, capsys):
    hash_atual = etl.calcular_hash_entradas()
    gravar_banco(ambiente["CAMINHO_BANCO"], hash_atual)
    ambiente["CAMINHO_CSV_MUNICIPIOS"].write_text("x")
    ambiente["CAMINHO_CSV_RESULTADOS"].write_text("x")
    etl.executar_etl()                                                 # não lê as "planilhas" falsas
    assert "já está atualizado" in capsys.readouterr().out


def test_banco_versionado_foi_gerado_com_as_entradas_versionadas():
    """Falha se alguém mudar planilha, esquema ou ETL e esquecer de regerar o banco versionado."""
    assert etl.banco_esta_atualizado(etl.calcular_hash_entradas()), \
        "Rode: python scripts/etl_sqlite.py --forcar e faça commit do banco e dos CSVs."
