"""Executa o dashboard inteiro (sem navegador) e confere que não há exceção nos principais recortes."""

import os

import pytest
from streamlit.testing.v1 import AppTest

from conftest import RAIZ

APP = os.path.join(RAIZ, "scripts", "app.py")


def novo_app():
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    return app


def test_brasil_sem_excecoes():
    app = novo_app()
    assert not app.exception
    texto = " ".join(m.value for m in app.markdown)
    assert "4.854 municípios que responderam" in texto
    assert "33,9%" in texto                      # média nacional de disposição inadequada
    legendas = " ".join(c.value for c in app.caption)
    assert "Média ponderada 20,79%" in legendas and "Média ponderada 92,63%" in legendas
    # etapa 3: destino declarado pelas rotas de coleta dos municípios com 0%
    assert "Entre os 3.057 municípios com 0% neste recorte" in texto
    assert "2.880 (94%) declararam rotas a aterro sanitário ou de inertes" in texto
    assert "174 (6%) cobrem a massa só ao somar unidades intermediárias" in texto
    assert "3 (menos de 1%) declararam rotas que cobrem menos de 90% da massa" in texto
    assert "Nenhum zero declara rota a lixão, vazadouro ou aterro controlado" in texto
    assert "Os dados são autodeclarados" in texto                         # limite da evidência sempre explícito
    legendas_mapa = " ".join(c.value for c in app.caption)
    assert "AL, SC, ES, PE, RS, PB, SE, SP, mais de 90% dos municípios registram exatamente 0%, e 94%" in legendas_mapa
    assert "No IRS3002, 0 significa" in legendas and "nos demais indicadores, 0 pode indicar ausência do serviço" in legendas   # sem generalizar o zero
    assert "dos resíduos coletados por município" in texto and "média dos municípios de cada região" in texto
    assert "Atenção em" not in legendas_mapa                              # o alerta por UF era artefato da fonte errada
    assert "que cobrem ao menos 90% da massa coletada líquida" in legendas_mapa
    # frases de versões anteriores, que a análise das rotas desmentiu, não podem voltar
    tudo = texto + " " + legendas + " " + " ".join(c.value for c in app.caption)
    assert "isso não foi verificado" not in tudo and "informação não preenchida" not in tudo


def test_uf_selecionada_sem_excecoes():
    app = novo_app()
    app.sidebar.selectbox[0].select("SP").run()
    assert not app.exception
    texto = " ".join(m.value for m in app.markdown)
    assert "Em SP" in texto and "6,7%" in texto and "20ª pior" in texto
    assert "Ponderando pela população, 7,9%" in texto
    legendas = " ".join(c.value for c in app.caption)
    assert "Média ponderada 7,89%" in legendas       # KPI de disposição inadequada em SP


def test_filtro_de_suspeitos_sem_excecoes():
    app = novo_app()
    app.sidebar.expander[0].checkbox[0].check().run()
    assert not app.exception
    legendas = " ".join(c.value for c in app.caption)
    assert "Média ponderada 20,79%" in legendas       # IRS3002 não tem valores suspeitos: não muda
    metricas = {m.label: m.value for m in app.metric}
    assert metricas["Massa per capita"] != "0,87"      # sem os 59 suspeitos a média cai


@pytest.mark.parametrize("uf", ["DF", "RR", "AL"])
def test_ufs_extremas_sem_excecoes(uf):
    app = novo_app()
    app.sidebar.selectbox[0].select(uf).run()
    assert not app.exception


def test_delta_dos_kpis_tem_unidade_e_virgula_no_lugar_certo():
    app = novo_app()
    app.sidebar.selectbox[0].select("SP").run()
    deltas = {m.label: m.delta for m in app.metric}
    assert deltas["Disposição inadequada"] == "-27,16 p.p. vs. Brasil"
    assert deltas["Massa per capita"].endswith("kg/hab.dia vs. Brasil")
    assert all("vs," not in d and d.count("vs.") == 1 for d in deltas.values())


@pytest.mark.parametrize("uf, esperado", [
    ("RR", "todos os municípios registram 100%"),
    ("AL", "todos os municípios registram 0%"),
    ("DF", "todos os municípios registram 0%"),
])
def test_recorte_sem_variacao_nao_diz_que_a_media_engana(uf, esperado):
    app = novo_app()
    app.sidebar.selectbox[0].select(uf).run()
    assert not app.exception
    subtitulos = " ".join(s.value for s in app.subheader)
    assert esperado in subtitulos and "a média engana" not in subtitulos


def test_df_tem_um_unico_municipio_sem_plural_errado():
    app = novo_app()
    app.sidebar.selectbox[0].select("DF").run()
    texto = " ".join(m.value for m in app.markdown)
    assert "o único município com 0%" in texto and "1 municípios" not in texto
