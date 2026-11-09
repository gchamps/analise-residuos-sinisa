"""Testes de caracterização do banco: travam os números hoje publicados no app e no relatório."""

import pandas as pd
import pytest

INDICADORES = ["IRS0001", "IRS0005", "IRS1004", "IRS3001", "IRS3002", "IRS3010"]


def escalar(conn, sql):
    return conn.execute(sql).fetchone()[0]


def test_contagens_principais(conn):
    assert escalar(conn, "SELECT COUNT(*) FROM municipio") == 5570
    assert escalar(conn, "SELECT COUNT(*) FROM municipio WHERE respondeu = 1") == 4854
    assert escalar(conn, "SELECT COUNT(*) FROM resultado_indicador") == 29124
    assert escalar(conn, "SELECT SUM(populacao_total) FROM municipio") == 212_583_750


def test_cada_indicador_cobre_todos_os_respondentes(conn):
    for codigo in INDICADORES:
        n = escalar(conn, f"SELECT COUNT(DISTINCT cod_ibge) FROM resultado_indicador WHERE codigo_indicador = '{codigo}'")
        assert n == 4854, codigo


def test_sinalizacoes_de_qualidade(conn):
    sinais = {(i, f): n for i, f, n in conn.execute(
        "SELECT codigo_indicador, flag_qualidade, COUNT(*) FROM resultado_indicador "
        "WHERE flag_qualidade IS NOT NULL GROUP BY 1, 2")}
    assert sinais == {("IRS1004", "MASSA_PER_CAPITA_ALTA"): 59, ("IRS3001", "PERCENTUAL_ACIMA_100"): 4}


def test_sem_resultados_de_nao_respondentes(conn):
    n = escalar(conn, "SELECT COUNT(*) FROM resultado_indicador r JOIN municipio m USING (cod_ibge) WHERE m.respondeu = 0")
    assert n == 0


def test_integridade_referencial(conn):
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_csvs_identicos_ao_banco(conn):
    from conftest import RAIZ
    import os
    mun = pd.read_csv(os.path.join(RAIZ, "dados_tratados", "municipios.csv"), dtype={"cod_ibge": str}, encoding="utf-8-sig")
    mun_db = pd.read_sql_query("SELECT * FROM municipio ORDER BY cod_ibge", conn)
    pd.testing.assert_frame_equal(mun.reset_index(drop=True), mun_db, check_dtype=False)

    res = pd.read_csv(os.path.join(RAIZ, "dados_tratados", "resultados_indicadores_mpv.csv"),
                      dtype={"cod_ibge": str}, encoding="utf-8-sig")
    res_db = pd.read_sql_query(
        "SELECT cod_ibge, codigo_indicador, valor, ano_referencia, flag_qualidade FROM resultado_indicador "
        "ORDER BY codigo_indicador, cod_ibge", conn)
    assert res["cod_ibge"].str.fullmatch(r"\d{7}").all()
    pd.testing.assert_frame_equal(res.reset_index(drop=True), res_db, check_dtype=False)


def test_medias_nacionais_publicadas(tabela):
    assert len(tabela) == 4854
    assert tabela["IRS3002"].mean() == pytest.approx(33.8669, abs=1e-3)
    assert tabela["IRS0001"].mean() == pytest.approx(81.6535, abs=1e-3)
    assert tabela["IRS1004"].mean() == pytest.approx(0.8749, abs=1e-3)
    assert (tabela["IRS3002"] == 0).mean() * 100 == pytest.approx(62.979, abs=1e-2)
