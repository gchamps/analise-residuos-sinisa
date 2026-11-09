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


def test_uf_selecionada_sem_excecoes():
    app = novo_app()
    app.sidebar.selectbox[0].select("SP").run()
    assert not app.exception
    texto = " ".join(m.value for m in app.markdown)
    assert "Em SP" in texto and "6,7%" in texto and "20ª pior" in texto


def test_filtro_de_suspeitos_sem_excecoes():
    app = novo_app()
    app.sidebar.expander[0].checkbox[0].check().run()
    assert not app.exception


@pytest.mark.parametrize("uf", ["DF", "RR", "AL"])
def test_ufs_extremas_sem_excecoes(uf):
    app = novo_app()
    app.sidebar.selectbox[0].select(uf).run()
    assert not app.exception
