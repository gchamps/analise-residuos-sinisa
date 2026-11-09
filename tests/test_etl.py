"""Testes unitários das regras do ETL (sem ler a planilha real)."""

import pandas as pd
import pytest

import etl_sqlite as etl


def test_codigo_ibge_como_texto():
    serie = pd.Series([3548708, 3548708.0, "3548708", None, "abc"])
    saida = etl.codigo_ibge_como_texto(serie)
    assert saida.iloc[0] == saida.iloc[1] == saida.iloc[2] == "3548708"
    assert pd.isna(saida.iloc[3]) and pd.isna(saida.iloc[4])


def _planilha_sintetica():
    base = {"Cod_IBGE": [1100015, 1100023, 1100031, 1100049, 1100056]}
    valores = {
        "IRS0001": [50, 120, 80, "null", 90],
        "IRS0005": [10, 10, 10, "null", 10],
        "IRS1004": [0.8, 3.5, 3.0, "null", 1.0],
        "IRS3001": [5, 5, 101, "null", 5],
        "IRS3002": [0, 100, 50, "null", 100.5],
        "IRS3010": [1, 1, 1, "null", 1],
    }
    return pd.DataFrame({**base, **valores})


def test_resultados_descartam_nao_numericos_e_sinalizam():
    r = etl.preparar_resultados(_planilha_sintetica())
    assert (r["cod_ibge"] != "1100049").all()          # linha só com "null" some
    assert len(r) == 4 * 6
    flags = r.dropna(subset=["flag_qualidade"]).set_index(["cod_ibge", "codigo_indicador"])["flag_qualidade"].to_dict()
    assert flags == {
        ("1100023", "IRS0001"): "PERCENTUAL_ACIMA_100",
        ("1100023", "IRS1004"): "MASSA_PER_CAPITA_ALTA",
        ("1100031", "IRS3001"): "PERCENTUAL_ACIMA_100",
        ("1100056", "IRS3002"): "PERCENTUAL_ACIMA_100",
    }                                                    # 3,0 kg/hab.dia exato NÃO é sinalizado
    assert (r["ano_referencia"] == etl.ANO_REFERENCIA).all()


def test_nenhum_valor_e_apagado_pela_sinalizacao():
    r = etl.preparar_resultados(_planilha_sintetica())
    assert r.loc[r["flag_qualidade"].notna(), "valor"].gt(0).all()
    assert 101 in r["valor"].values and 3.5 in r["valor"].values


def test_municipios_respondeu_e_duplicatas():
    dados = pd.DataFrame({
        "Cod_IBGE": [1, 1, 2, None], "Nom_Mun": ["A", "A", "B", "C"], "UF": ["SP"] * 4,
        "Nom_Região": ["Sudeste"] * 4, "DFE0001": [100, 100, "200", 300], "Sim/Não": ["Sim", "Sim", " não ", "Sim"]})
    m = etl.preparar_municipios(dados)
    assert list(m["cod_ibge"]) == ["1", "2"]
    assert list(m["respondeu"]) == [1, 0]
    assert m["populacao_total"].sum() == 300


def test_exigir_colunas_interrompe():
    with pytest.raises(SystemExit):
        etl.exigir_colunas(pd.DataFrame({"a": [1]}), ["a", "b"])
