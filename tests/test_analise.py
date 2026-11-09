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


def test_regioes(tabela):
    r = an.resumo_regioes(tabela).set_index("regiao")
    assert r.loc["Norte", "media_simples"] == pytest.approx(78.257, abs=1e-2)
    assert r.loc["Sul", "media_simples"] == pytest.approx(4.268, abs=1e-2)


def test_probabilidades_condicionais(tabela):
    p = an.probabilidades_condicionais(tabela)
    assert p["n_sem_coleta"] == 3439
    assert p["n_com_coleta"] == 1415
    assert p["p_rec_zero_dado_sem_coleta"] == pytest.approx(0.9654, abs=1e-3)


def test_mann_whitney_sp(tabela):
    t = an.comparar_uf_com_demais(tabela)
    assert t["n_uf"] == 616 and t["n_demais"] == 4238
    assert t["prob_uf_menor"] == pytest.approx(0.6654, abs=1e-3)
    assert t["p_valor"] < 1e-50
