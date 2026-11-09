"""Etapa 3: evidência de infraestrutura para os zeros do IRS3002."""

import pandas as pd
import pytest

import calculos as c
import etl_sqlite as etl


def unidades_sinteticas():
    return pd.DataFrame({
        "Cod_IBGE": [1, 1, 2, 3, 4, 5, 6],
        etl.COLUNA_TIPO_UNIDADE: ["Aterro sanitário", "Aterro de inertes", "Lixão ou vazadouro", "Aterro controlado",
                                  "Aterro sanitário", "Aterro sanitário", None],
        etl.COLUNA_EM_OPERACAO: ["Sim", "Sim", "Sim", "Sim", "Não", " sim ", "Sim"],
    })


def test_classificar_unidade():
    assert etl.classificar_unidade("Lixão ou vazadouro") == "inadequada"
    assert etl.classificar_unidade("Aterro controlado") == "inadequada"
    assert etl.classificar_unidade("Aterro sanitário") == "sanitario"
    assert etl.classificar_unidade("Aterro de inertes") == "inertes"


def test_preparar_destinacao_conta_so_unidades_em_operacao():
    d = etl.preparar_destinacao(unidades_sinteticas(), ["1", "2", "3", "4", "5", "6", "7"]).set_index("cod_ibge")
    assert list(d.columns) == ["unidades_inadequadas_operacao", "aterros_sanitarios_operacao", "aterros_inertes_operacao"]
    assert d.loc["1"].tolist() == [0, 1, 1]
    assert d.loc["2", "unidades_inadequadas_operacao"] == 1
    assert d.loc["3", "unidades_inadequadas_operacao"] == 1
    assert d.loc["4"].sum() == 0                       # aterro inoperante não conta
    assert d.loc["5", "aterros_sanitarios_operacao"] == 1   # "sim" com espaços/caixa
    assert d.loc["6"].sum() == 0 and d.loc["7"].sum() == 0   # linha sem tipo e município sem unidade
    assert len(d) == 7


def test_classificar_zeros_regras():
    tabela = pd.DataFrame({"cod_ibge": ["1", "2", "3", "4", "5"], "IRS3002": [0, 0, 0, 50, 0]}, index=[10, 11, 12, 13, 14])
    dest = pd.DataFrame({"cod_ibge": ["1", "2", "3", "4"],
                         "unidades_inadequadas_operacao": [0, 0, 1, 0],
                         "aterros_sanitarios_operacao": [1, 0, 1, 1],
                         "aterros_inertes_operacao": [0, 1, 0, 0]})
    r = c.classificar_zeros(tabela, dest)
    assert r[10] == c.EVIDENCIA_CONFIRMADO
    assert r[11] == c.EVIDENCIA_NAO_VERIFICADO           # só inertes
    assert r[12] == c.EVIDENCIA_CONTRADICAO              # sedia inadequada, mesmo com sanitário
    assert pd.isna(r[13])                                # não é zero
    assert r[14] == c.EVIDENCIA_NAO_VERIFICADO           # município ausente da tabela de destinação
    assert c.resumo_evidencia_zeros(tabela, dest).to_dict() == {
        c.EVIDENCIA_CONFIRMADO: 1, c.EVIDENCIA_NAO_VERIFICADO: 2, c.EVIDENCIA_CONTRADICAO: 1}


def test_banco_tem_destinacao_para_todos_os_municipios(conn):
    assert conn.execute("SELECT COUNT(*) FROM destinacao_municipio").fetchone()[0] == 5570


def test_numeros_dos_zeros_do_irs3002(tabela, conn):
    dest = pd.read_sql_query(c.CONSULTA_DESTINACAO, conn)
    evid = c.resumo_evidencia_zeros(tabela, dest)
    assert evid.sum() == 3057
    assert evid[c.EVIDENCIA_CONFIRMADO] == 665
    assert evid[c.EVIDENCIA_NAO_VERIFICADO] == 3057 - 665
    assert evid[c.EVIDENCIA_CONTRADICAO] == 0            # nenhum zero sedia lixão em operação


def test_municipios_com_valor_positivo_sediam_lixao_com_frequencia(tabela, conn):
    """Sanidade da evidência: onde há disposição inadequada, a infraestrutura costuma estar no município."""
    dest = pd.read_sql_query(c.CONSULTA_DESTINACAO, conn)
    m = tabela.merge(dest, on="cod_ibge")
    sedia = m["unidades_inadequadas_operacao"] > 0
    assert sedia[m["IRS3002"] > 0].mean() > 0.9
    assert sedia[m["IRS3002"] == 0].mean() == 0
