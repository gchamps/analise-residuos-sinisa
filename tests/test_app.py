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
    # etapa 3: evidência de infraestrutura para os zeros
    assert "Dos 3.057 municípios com 0%" in texto
    assert "Dos 3.057 municípios com 0%" in texto
    assert "2.880 (94%) declararam rotas a aterro sanitário ou de inertes" in texto
    assert "174 (6%) declararam, em boa parte, unidades intermediárias" in texto
    assert "3 (0%) declararam rotas que cobrem menos de 90% da massa" in texto
    assert "Nenhum zero declara rota a lixão, vazadouro ou aterro controlado" in texto
    assert "Os dados são autodeclarados" in texto                         # limite da evidência sempre explícito
    legendas_mapa = " ".join(c.value for c in app.caption)
    assert "AL, SC, ES, PE, RS, PB, SE, SP, mais de 90% dos municípios registram exatamente 0%, e 94%" in legendas_mapa
    assert "Atenção em" not in legendas_mapa                              # o alerta por UF era artefato da fonte errada


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
