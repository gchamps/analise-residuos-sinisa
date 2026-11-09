"""Etapa 4: caminhos de falha do ETL, validação do IRS3002 e comparação de bancos."""

import os
import sqlite3

import pandas as pd
import pytest

import comparar_bancos
import etl_sqlite as etl
from conftest import RAIZ


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    nomes = {"CAMINHO_EXCEL": "i.xlsx", "CAMINHO_EXCEL_MANEJO": "m.xlsx", "CAMINHO_SCHEMA": "s.sql",
             "CAMINHO_BANCO": "banco.db", "CAMINHO_CSV_MUNICIPIOS": "m.csv", "CAMINHO_CSV_RESULTADOS": "r.csv"}
    caminhos = {k: str(tmp_path / v) for k, v in nomes.items()}
    (tmp_path / "i.xlsx").write_bytes(b"1")
    (tmp_path / "m.xlsx").write_bytes(b"2")
    (tmp_path / "s.sql").write_bytes(b"x")
    (tmp_path / "banco.db").write_bytes(b"banco antigo")
    (tmp_path / "m.csv").write_bytes(b"csv m antigo")
    (tmp_path / "r.csv").write_bytes(b"csv r antigo")
    for k, v in caminhos.items():
        monkeypatch.setattr(etl, k, v)
    # etapas de leitura/carga trocadas por versões mínimas; a validação é a parte que cada teste controla
    municipios = pd.DataFrame({"cod_ibge": ["1"], "nome_municipio": ["A"], "uf": ["SP"], "regiao": ["Sudeste"],
                               "populacao_total": [10], "respondeu": [1]})
    monkeypatch.setattr(etl, "ler_planilha", lambda c: None)
    monkeypatch.setattr(etl, "preparar_municipios", lambda d: municipios)
    monkeypatch.setattr(etl, "preparar_resultados", lambda d: pd.DataFrame())
    monkeypatch.setattr(etl, "ler_rotas_destino", lambda c: None)
    monkeypatch.setattr(etl, "ler_massas_manejo", lambda c: None)
    monkeypatch.setattr(etl, "preparar_destinacao", lambda *a: pd.DataFrame())
    monkeypatch.setattr(etl, "criar_esquema", lambda conn: conn.execute(
        "CREATE TABLE etl_meta (chave TEXT PRIMARY KEY, valor TEXT NOT NULL)"))
    monkeypatch.setattr(etl, "carregar", lambda *a: None)
    monkeypatch.setattr(etl, "exportar_csvs", lambda conn, sufixo="": (
        open(caminhos["CAMINHO_CSV_MUNICIPIOS"] + sufixo, "w").write("novo m"),
        open(caminhos["CAMINHO_CSV_RESULTADOS"] + sufixo, "w").write("novo r"), (1, 1))[2])
    monkeypatch.setattr(etl, "validar_carga", lambda conn: [])
    return tmp_path


def sobras(pasta):
    return [p.name for p in pasta.iterdir() if p.name.endswith(".tmp")]


def test_sucesso_troca_banco_e_csvs_e_nao_deixa_temporarios(ambiente):
    etl.executar_etl(forcar=True)
    assert (ambiente / "m.csv").read_text() == "novo m" and (ambiente / "r.csv").read_text() == "novo r"
    assert (ambiente / "banco.db").read_bytes() != b"banco antigo"
    assert sobras(ambiente) == []


def test_validacao_com_problema_mantem_tudo_e_limpa(ambiente, monkeypatch):
    monkeypatch.setattr(etl, "validar_carga", lambda conn: ["problema"])
    with pytest.raises(SystemExit):
        etl.executar_etl(forcar=True)
    assert (ambiente / "banco.db").read_bytes() == b"banco antigo"
    assert (ambiente / "m.csv").read_bytes() == b"csv m antigo"
    assert sobras(ambiente) == []


def test_excecao_no_meio_da_carga_limpa_temporarios(ambiente, monkeypatch):
    def quebra(*a):
        raise RuntimeError("falha simulada")
    monkeypatch.setattr(etl, "carregar", quebra)
    with pytest.raises(RuntimeError):
        etl.executar_etl(forcar=True)
    assert (ambiente / "banco.db").read_bytes() == b"banco antigo"
    assert sobras(ambiente) == []


def test_banco_aberto_no_windows_da_mensagem_clara_e_mantem_csvs(ambiente, monkeypatch):
    real = os.replace

    def replace_negado(origem, destino):
        if str(destino).endswith("banco.db"):
            raise PermissionError("[WinError 5] Acesso negado")
        return real(origem, destino)
    monkeypatch.setattr(os, "replace", replace_negado)
    with pytest.raises(SystemExit) as erro:
        etl.executar_etl(forcar=True)
    assert "aberto em outro programa" in str(erro.value)
    assert (ambiente / "banco.db").read_bytes() == b"banco antigo"
    assert (ambiente / "m.csv").read_bytes() == b"csv m antigo"        # CSVs também intocados
    assert sobras(ambiente) == []


def test_csv_aberto_depois_do_banco_orienta_a_rodar_de_novo(ambiente, monkeypatch):
    real = os.replace

    def replace_negado(origem, destino):
        if str(destino).endswith("r.csv"):
            raise PermissionError("em uso")
        return real(origem, destino)
    monkeypatch.setattr(os, "replace", replace_negado)
    with pytest.raises(SystemExit) as erro:
        etl.executar_etl(forcar=True)
    assert "--forcar" in str(erro.value) and "r.csv" in str(erro.value)
    assert sobras(ambiente) == []


def test_hash_muda_com_a_planilha_de_manejo(ambiente):
    base = etl.calcular_hash_entradas()
    (ambiente / "m.xlsx").write_bytes(b"outra")
    assert etl.calcular_hash_entradas() != base


# ---------------------------------------------------------------- validar_carga: o IRS3002 deve bater com as rotas
@pytest.fixture
def banco_minimo():
    conn = sqlite3.connect(":memory:")
    with open(os.path.join(RAIZ, "sql", "01_schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.execute("PRAGMA foreign_keys = ON")
    for codigo, nome, un, grupo in [("IRS0001", "a", "Percentual", "Cobertura"), ("IRS0005", "b", "Percentual", "Cobertura"),
                                    ("IRS1004", "c", "Kg/hab.dia", "Operacional"), ("IRS3001", "d", "Percentual", "Qualidade"),
                                    ("IRS3002", "e", "Percentual", "Qualidade"), ("IRS3010", "f", "Percentual", "Qualidade")]:
        conn.execute("INSERT INTO indicador VALUES (?,?,?,?,NULL)", (codigo, nome, un, grupo))
    conn.execute("INSERT INTO municipio VALUES ('1','A','SP','Sudeste',100,1)")
    for codigo in ("IRS0001", "IRS0005", "IRS1004", "IRS3001", "IRS3002", "IRS3010"):
        conn.execute("INSERT INTO resultado_indicador (cod_ibge,codigo_indicador,ano_referencia,valor) VALUES ('1',?,2024,25)",
                     (codigo,))
    conn.execute("INSERT INTO destinacao_municipio VALUES ('1', 25, 75, 0, 100, 0)")    # 25 / 100 = 25%: confere
    return conn


def test_validar_carga_aceita_irs3002_reproduzido(banco_minimo):
    assert etl.validar_carga(banco_minimo) == []


def test_validar_carga_acusa_irs3002_que_nao_bate_com_as_rotas(banco_minimo):
    banco_minimo.execute("UPDATE resultado_indicador SET valor = 40 WHERE codigo_indicador = 'IRS3002'")
    problemas = etl.validar_carga(banco_minimo)
    assert any("diferente do recalculado pelas rotas" in p for p in problemas)


def test_validar_carga_acusa_municipio_que_nao_pode_ser_conferido(banco_minimo):
    banco_minimo.execute("UPDATE destinacao_municipio SET massa_coletada = NULL")
    problemas = etl.validar_carga(banco_minimo)           # antes: TypeError por MAX() nulo
    assert any("puderam ser conferidos" in p for p in problemas)


def test_validar_carga_acusa_zero_com_rota_inadequada(banco_minimo):
    banco_minimo.execute("UPDATE resultado_indicador SET valor = 0 WHERE codigo_indicador = 'IRS3002'")
    problemas = etl.validar_carga(banco_minimo)
    assert any("declaram rota a lixão" in p for p in problemas)


# ---------------------------------------------------------------- comparar_bancos
def _banco(caminho, valor):
    conn = sqlite3.connect(caminho)
    for tabela in comparar_bancos.TABELAS:
        conn.execute(f"CREATE TABLE {tabela} (a TEXT, b TEXT, c TEXT)")
        conn.execute(f"INSERT INTO {tabela} VALUES ('1', '2', ?)", (valor,))
    conn.commit()
    conn.close()


def test_comparar_bancos_iguais_e_diferentes(tmp_path):
    _banco(tmp_path / "a.db", "x")
    _banco(tmp_path / "b.db", "x")
    _banco(tmp_path / "c.db", "y")
    assert comparar_bancos.diferencas(tmp_path / "a.db", tmp_path / "b.db") == []
    achados = comparar_bancos.diferencas(tmp_path / "a.db", tmp_path / "c.db")
    assert len(achados) == len(comparar_bancos.TABELAS)


def test_comparar_bancos_com_o_banco_real_versionado():
    """Regressão do achado alto da auditoria final: o script quebrava com as tabelas reais (etl_meta tem 2 colunas)."""
    banco = os.path.join(RAIZ, "dados_tratados", "projeto_residuos.db")
    assert comparar_bancos.diferencas(banco, banco) == []


def test_comparar_bancos_acusa_tabela_ausente(tmp_path):
    _banco(tmp_path / "a.db", "x")
    vazio = sqlite3.connect(tmp_path / "vazio.db")
    vazio.close()
    achados = comparar_bancos.diferencas(tmp_path / "a.db", tmp_path / "vazio.db")
    assert len(achados) == len(comparar_bancos.TABELAS) and all("não pôde ser lida" in a for a in achados)


def test_comparar_bancos_detecta_uma_celula_alterada_no_banco_real(tmp_path):
    import shutil
    original = os.path.join(RAIZ, "dados_tratados", "projeto_residuos.db")
    copia = tmp_path / "copia.db"
    shutil.copyfile(original, copia)
    conn = sqlite3.connect(copia)
    conn.execute("UPDATE resultado_indicador SET valor = valor + 1 WHERE id_resultado = 1")
    conn.commit()
    conn.close()
    achados = comparar_bancos.diferencas(original, copia)
    assert len(achados) == 1 and achados[0].startswith("resultado_indicador")


def test_banco_com_caractere_especial_no_caminho(tmp_path):
    pasta = tmp_path / "dados #1 100%"
    pasta.mkdir()
    _banco(pasta / "a.db", "x")
    _banco(tmp_path / "b.db", "x")
    assert comparar_bancos.diferencas(pasta / "a.db", tmp_path / "b.db") == []
