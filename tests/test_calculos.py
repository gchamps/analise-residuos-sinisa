"""Testes do módulo comum de cálculos (usado pelo app, pela análise e pela planilha)."""

import pandas as pd
import pytest

import analise_estatistica as an
import calculos as c


def test_media_ponderada_ignora_ausentes():
    v = pd.Series([0.0, 100.0, None])
    p = pd.Series([1, 3, 1000])
    assert c.media_ponderada(v, p) == pytest.approx(75.0)
    assert pd.isna(c.media_ponderada(pd.Series([None, None], dtype=float), pd.Series([1, 1])))


def test_resumo_indicador_vazio_e_basico():
    assert c.resumo_indicador(pd.Series([], dtype=float), pd.Series([], dtype=float))["N"] == 0
    # valores e pesos escolhidos para que média simples, ponderada, %0 e %100 sejam todos diferentes
    r = c.resumo_indicador(pd.Series([0.0, 0.0, 100.0, 40.0]), pd.Series([1, 1, 6, 2]))
    assert r["N"] == 4 and r["Média"] == pytest.approx(35.0)
    assert r["Mediana"] == pytest.approx(20.0) and r["Mínimo"] == 0 and r["Máximo"] == 100
    assert r["% = 0"] == pytest.approx(50.0) and r["% = 100"] == pytest.approx(25.0)
    assert r["Média ponderada"] == pytest.approx(68.0)     # (0*1 + 0*1 + 100*6 + 40*2) / 10
    assert r["Desvio-padrão"] == pytest.approx(pd.Series([0.0, 0.0, 100.0, 40.0]).std(ddof=1))


def test_montar_tabela_forma_e_exclusao(conn):
    longo = pd.read_sql_query(c.CONSULTA_RESULTADOS, conn)
    cheia = c.montar_tabela(longo)
    assert len(cheia) == 4854 and list(cheia["cod_ibge"]) == sorted(cheia["cod_ibge"])
    assert cheia[c.INDICADORES].notna().all().all()
    limpa = c.montar_tabela(longo, excluir_sinalizados=True)
    assert len(limpa) == 4854                      # município continua, o valor suspeito vira ausente
    assert limpa["IRS1004"].isna().sum() == 59
    assert limpa["IRS3001"].isna().sum() == 4
    assert limpa["IRS1004"].max() <= 3.0 and limpa["IRS3001"].max() <= 100.0
    assert limpa["IRS3002"].mean() == pytest.approx(cheia["IRS3002"].mean())   # outros indicadores intactos


def test_exclusao_muda_a_media_so_dos_indicadores_afetados(conn):
    longo = pd.read_sql_query(c.CONSULTA_RESULTADOS, conn)
    cheia, limpa = c.montar_tabela(longo), c.montar_tabela(longo, True)
    assert limpa["IRS1004"].mean() < cheia["IRS1004"].mean()
    assert limpa["IRS3001"].mean() < cheia["IRS3001"].mean()


def test_analise_e_app_usam_o_mesmo_ranking(tabela):
    assert an.ranking_uf is c.ranking_uf
    r = c.ranking_uf(tabela)
    assert list(r.columns) == ["uf", "n_municipios", "media_simples", "media_ponderada",
                               "posicao_simples", "posicao_ponderada"]
    assert r["n_municipios"].sum() == 4854


def test_ranking_com_exclusao_de_suspeitos(conn):
    longo = pd.read_sql_query(c.CONSULTA_RESULTADOS, conn)
    r = c.ranking_uf(c.montar_tabela(longo, True), "IRS1004").set_index("uf")
    assert r["n_municipios"].sum() == 4854 - 59


def test_resumo_por_faixa_cobre_todos(tabela):
    f = c.resumo_por_faixa(tabela)
    assert f["municipios"].sum() == 4854
    assert list(f["faixa"].astype(str)) == c.ROTULOS_FAIXA
    # recálculo independente da faixa "até 10 mil"
    pequenos = tabela[tabela["populacao_total"] <= 10_000]
    linha = f.set_index("faixa").loc["até 10 mil"]
    assert linha["municipios"] == len(pequenos)
    assert linha["disposicao"] == pytest.approx(pequenos["IRS3002"].mean())
    assert f["disposicao"].between(0, 100).all()


def test_ranking_ordenado_por_posicao_e_uf(tabela):
    r = c.ranking_uf(tabela)
    assert list(r["uf"][:3]) == ["RR", "AM", "PA"]
    chave = list(zip(r["posicao_simples"], r["uf"]))
    assert chave == sorted(chave)
    assert list(r["uf"][-2:]) == ["AL", "DF"]       # empatados em 0%, desempate alfabético


def test_formatar_padrao_brasileiro():
    assert c.formatar(1234567.891, 2) == "1.234.567,89"
    assert c.formatar(33.8669, 1, "%") == "33,9%"
    assert c.formatar(None) == "sem dados"
    assert c.formatar(float("nan")) == "sem dados"


def test_mapa_prepara_27_ufs():
    import os
    from conftest import RAIZ
    from mapa import preparar_mapa
    feicoes, siglas = preparar_mapa(os.path.join(RAIZ, "dados_tratados", "br_ufs.geojson"),
                                    {"SP": 6.7}, "SP", c.formatar)
    assert len(feicoes) == len(siglas) == 27
    sp = next(f for f in feicoes if f["properties"]["uf"] == "SP")
    assert sp["properties"]["sel"] and sp["properties"]["rotulo"] == "6,7%"
    assert next(f for f in feicoes if f["properties"]["uf"] == "RJ")["properties"]["rotulo"] == "sem dados"
