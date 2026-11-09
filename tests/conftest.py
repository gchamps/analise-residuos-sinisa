"""Configuração comum dos testes: deixa scripts/ importável e abre o banco versionado (somente leitura)."""

import os
import sqlite3
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

CAMINHO_BANCO = os.path.join(RAIZ, "dados_tratados", "projeto_residuos.db")


@pytest.fixture(scope="session")
def conn():
    if not os.path.exists(CAMINHO_BANCO):
        pytest.fail(f"Banco ausente: {CAMINHO_BANCO}. Rode scripts/etl_sqlite.py.")
    from pathlib import Path
    c = sqlite3.connect(Path(CAMINHO_BANCO).resolve().as_uri() + "?mode=ro", uri=True)
    yield c
    c.close()


@pytest.fixture(scope="session")
def tabela(conn):
    """Uma linha por município respondente, uma coluna por indicador."""
    import analise_estatistica as an
    return an.carregar_dados(conn)
