"""Configuração comum dos testes: deixa scripts/ importável e abre o banco versionado."""

import os
import sqlite3
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

CAMINHO_BANCO = os.path.join(RAIZ, "dados_tratados", "projeto_residuos.db")


@pytest.fixture(scope="session")
def conn():
    c = sqlite3.connect(CAMINHO_BANCO)
    yield c
    c.close()


@pytest.fixture(scope="session")
def tabela(conn):
    """Uma linha por município respondente, uma coluna por indicador."""
    import analise_estatistica as an
    return an.carregar_dados(conn)
