"""Testes de caracterização da análise estatística (números citados no app e no relatório)."""

import pytest

import analise_estatistica as an


def test_media_ponderada_simples():
    import pandas as pd
    assert an.media_ponderada(pd.Series([0.0, 100.0]), pd.Series([1, 3])) == pytest.approx(75.0)


def test_ranking_sp(tabela):
    r = an.ranking_uf(tabela).set_index("uf")
    assert r.loc["SP", "n_municipios"] == 616
    assert r.loc["SP", "media_simples"] == pytest.approx(6.7083, abs=1e-3)
    assert r.loc["SP", "media_ponderada"] == pytest.approx(7.8879, abs=1e-3)
    assert r.loc["SP", "posicao_simples"] == 20
    assert r.loc["SP", "posicao_ponderada"] == 16
    assert r.loc["RR", "media_simples"] == pytest.approx(100.0)
    assert len(r) == 27


REGIOES = {  # n, média simples, média ponderada, P(=100), P(=0)
    "Centro-Oeste": (424, 51.7536, 33.5149, 0.4717, 0.4127),
    "Nordeste": (1341, 56.4697, 35.1755, 0.5474, 0.4191),
    "Norte": (387, 78.2575, 53.3993, 0.7442, 0.1860),
    "Sudeste": (1558, 20.2518, 10.3228, 0.1733, 0.7657),
    "Sul": (1144, 4.2679, 1.9027, 0.0288, 0.9222),
}


def test_regioes(tabela):
    r = an.resumo_regioes(tabela).set_index("regiao")
    assert set(r.index) == set(REGIOES)
    for regiao, (n, simples, pond, cem, zero) in REGIOES.items():
        assert r.loc[regiao, "n_municipios"] == n
        assert r.loc[regiao, "media_simples"] == pytest.approx(simples, abs=1e-3)
        assert r.loc[regiao, "media_ponderada"] == pytest.approx(pond, abs=1e-3)
        assert r.loc[regiao, "prob_cem"] == pytest.approx(cem, abs=1e-3)
        assert r.loc[regiao, "prob_zero"] == pytest.approx(zero, abs=1e-3)


DESCRITIVA = {  # média, média ponderada, % zero, % cem
    "IRS0001": (81.653, 92.631, 0.0, 30.944),
    "IRS0005": (20.795, 40.560, 70.849, 4.821),
    "IRS1004": (0.875, 1.136, 0.0, 0.0),
    "IRS3001": (4.394, 4.108, 70.499, 0.021),
    "IRS3002": (33.867, 20.789, 62.979, 31.417),
    "IRS3010": (2.810, 2.348, 68.624, 0.0),
}


def test_descritiva_completa(tabela):
    d = an.estatistica_descritiva(tabela).set_index("indicador")
    for codigo, (media, pond, zero, cem) in DESCRITIVA.items():
        assert d.loc[codigo, "n"] == 4854
        assert d.loc[codigo, "media"] == pytest.approx(media, abs=1e-3)
        assert d.loc[codigo, "media_ponderada"] == pytest.approx(pond, abs=1e-3)
        assert d.loc[codigo, "pct_zero"] == pytest.approx(zero, abs=1e-3)
        assert d.loc[codigo, "pct_cem"] == pytest.approx(cem, abs=1e-3)


def test_empate_no_ranking_usa_posicao_minima(tabela):
    r = an.ranking_uf(tabela).set_index("uf")
    assert r.loc["AL", "posicao_simples"] == r.loc["DF", "posicao_simples"] == 26


def test_regressao_e_correlacoes(tabela):
    reg = an.regressao_simples(tabela, "IRS3010", "IRS0005")
    assert reg["n"] == 4854
    assert reg["inclinacao"] == pytest.approx(0.0821, abs=1e-4)
    assert reg["intercepto"] == pytest.approx(1.1024, abs=1e-3)
    assert reg["r2"] == pytest.approx(0.1583, abs=1e-3)
    assert an.matriz_correlacao(tabela, "spearman").loc["IRS0001", "IRS3002"] == pytest.approx(-0.2316, abs=1e-3)
    assert an.matriz_correlacao(tabela).loc["IRS0005", "IRS3010"] == pytest.approx(0.3978, abs=1e-3)


def test_probabilidades_condicionais(tabela):
    p = an.probabilidades_condicionais(tabela)
    assert p["n_sem_coleta"] == 3439
    assert p["n_com_coleta"] == 1415
    assert p["p_rec_zero_dado_sem_coleta"] == pytest.approx(0.9654, abs=1e-3)
    assert p["p_rec_zero_dado_com_coleta"] == pytest.approx(0.00777, abs=1e-4)


def test_mann_whitney_sp(tabela):
    t = an.comparar_uf_com_demais(tabela)
    assert t["n_uf"] == 616 and t["n_demais"] == 4238
    assert t["prob_uf_menor"] == pytest.approx(0.6654, abs=1e-3)
    assert t["p_valor"] < 1e-50
