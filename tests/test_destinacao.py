"""Etapa 3: zeros do IRS3002 explicados pelos fluxos de destinação que cada município declarou."""

import pandas as pd
import pytest

import calculos as c
import etl_sqlite as etl


def fluxos_sinteticos():
    # (município de origem, tipo de unidade destino, massa enviada)
    linhas = [
        (1, "Aterro sanitário", 80.0), (1, "Aterro de inertes", 20.0),
        (2, "Lixão ou vazadouro", 10.0), (2, "Aterro sanitário", 90.0),
        (3, "Aterro controlado", 5.0),
        (4, "Aterro sanitário", 50.0),
        (5, "Aterro sanitário", "n/d"),                    # massa não numérica é descartada
    ]
    return pd.DataFrame({"Cod_ibge_mun_orig": [l[0] for l in linhas],
                         etl.COLUNA_TIPO_UNIDADE: [l[1] for l in linhas],
                         etl.COLUNA_MASSA_ENVIADA: [l[2] for l in linhas]})


def massas_sinteticas():
    return pd.DataFrame({"Cod_IBGE": [1, 2, 3, 4, 6], "GTR1028": [100.0, 100.0, 5.0, 100.0, 10.0],
                         "GTR1029": [0, 0, 0, 0, None]})


def test_classificar_unidade():
    assert etl.classificar_unidade("Lixão ou vazadouro") == "inadequada"
    assert etl.classificar_unidade(" Aterro controlado ") == "inadequada"
    assert etl.classificar_unidade("Aterro sanitário") == "sanitario"
    assert etl.classificar_unidade("Aterro de inertes") == "inertes"


def test_tipo_de_unidade_desconhecido_interrompe_o_etl():
    with pytest.raises(SystemExit):
        etl.classificar_unidade("Incinerador")


def test_preparar_destinacao_soma_fluxos_por_origem():
    d = etl.preparar_destinacao(fluxos_sinteticos(), massas_sinteticas(), ["1", "2", "3", "4", "5", "6", "7"])
    d = d.set_index("cod_ibge")
    assert len(d) == 7
    assert d.loc["1", ["massa_enviada_inadequada", "massa_enviada_sanitario", "massa_enviada_inertes"]].tolist() == [0, 80, 20]
    assert d.loc["2", "massa_enviada_inadequada"] == 10 and d.loc["2", "massa_enviada_sanitario"] == 90
    assert d.loc["3", "massa_enviada_inadequada"] == 5
    assert d.loc["5", ["massa_enviada_inadequada", "massa_enviada_sanitario", "massa_enviada_inertes"]].sum() == 0
    assert d.loc["7", "massa_enviada_sanitario"] == 0                     # sem fluxo: zero, não ausente
    assert d.loc["1", "massa_coletada"] == 100 and d.loc["6", "massa_recuperada"] != d.loc["6", "massa_recuperada"]
    assert pd.isna(d.loc["5", "massa_coletada"])                            # município sem linha no Manejo


def _tabela_zeros(codigos, valores=None):
    return pd.DataFrame({"cod_ibge": codigos, "IRS3002": valores or [0] * len(codigos)})


def _destino(**linhas):
    """linhas: cod -> (inadequada, sanitario, inertes, coletada, recuperada)."""
    return pd.DataFrame([{"cod_ibge": k, "massa_enviada_inadequada": v[0], "massa_enviada_sanitario": v[1],
                          "massa_enviada_inertes": v[2], "massa_coletada": v[3], "massa_recuperada": v[4]}
                         for k, v in linhas.items()])


def test_classificar_zeros_regras():
    dest = _destino(a=(0, 95, 0, 100, 0),      # cobre 95%
                    b=(0, 50, 0, 100, 0),      # cobre só 50%
                    c=(0, 0, 0, 100, 0),       # nenhum fluxo
                    d=(7, 90, 0, 100, 0),      # envia a lixão
                    e=(0, 0, 30, 100, 10),     # só inertes: 30/90 = 33%
                    f=(0, 45, 45, 100, 10),    # 90/90: coletada líquida usa a recuperada
                    g=(0, 10, 0, None, None))  # massa coletada não informada: basta haver fluxo adequado
    tabela = _tabela_zeros(list("abcdefgh") , [0, 0, 0, 0, 0, 0, 0, 0])
    tabela.index = [10, 11, 12, 13, 14, 15, 16, 17]
    r = c.classificar_zeros(tabela, dest)
    assert r[10] == c.EVIDENCIA_CONFIRMADO
    assert r[11] == c.EVIDENCIA_PARCIAL
    assert r[12] == c.EVIDENCIA_SEM_DESTINO
    assert r[13] == c.EVIDENCIA_CONTRADICAO
    assert r[14] == c.EVIDENCIA_PARCIAL
    assert r[15] == c.EVIDENCIA_CONFIRMADO
    assert r[16] == c.EVIDENCIA_CONFIRMADO
    assert r[17] == c.EVIDENCIA_SEM_DESTINO           # município ausente da tabela de destinação


def test_classificar_zeros_ignora_nao_zeros_e_preserva_indice():
    dest = _destino(a=(0, 95, 0, 100, 0), b=(0, 95, 0, 100, 0))
    tabela = pd.DataFrame({"cod_ibge": ["a", "b"], "IRS3002": [0, 50]}, index=[5, 3])
    r = c.classificar_zeros(tabela, dest)
    assert r[5] == c.EVIDENCIA_CONFIRMADO and pd.isna(r[3])


def test_limite_de_cobertura_e_inclusivo():
    dest = _destino(a=(0, 90, 0, 100, 0))
    assert c.classificar_zeros(_tabela_zeros(["a"]), dest).iloc[0] == c.EVIDENCIA_CONFIRMADO
    assert c.classificar_zeros(_tabela_zeros(["a"]), dest, limite_cobertura=0.91).iloc[0] == c.EVIDENCIA_PARCIAL


def test_banco_tem_destinacao_para_todos_os_municipios(conn):
    assert conn.execute("SELECT COUNT(*) FROM destinacao_municipio").fetchone()[0] == 5570


def test_numeros_dos_zeros_do_irs3002(tabela, conn):
    dest = pd.read_sql_query(c.CONSULTA_DESTINACAO, conn)
    evid = c.resumo_evidencia_zeros(tabela, dest)
    assert evid.sum() == 3057
    assert evid[c.EVIDENCIA_CONFIRMADO] == 2788
    assert evid[c.EVIDENCIA_PARCIAL] == 188
    assert evid[c.EVIDENCIA_SEM_DESTINO] == 81
    assert evid[c.EVIDENCIA_CONTRADICAO] == 0            # nenhum zero declara envio a lixão


def test_irs3002_e_reproduzido_pelos_fluxos(tabela, conn):
    """Sanidade da tese: o indicador vem dos fluxos, então recalculá-lo dos fluxos dá quase o mesmo valor."""
    m = tabela.merge(pd.read_sql_query(c.CONSULTA_DESTINACAO, conn), on="cod_ibge")
    total = m["massa_enviada_inadequada"] + m["massa_enviada_sanitario"] + m["massa_enviada_inertes"]
    base = m[(m["IRS3002"] > 0) & (total > 0)]
    calculado = base["massa_enviada_inadequada"] / (base["massa_enviada_inadequada"] + base["massa_enviada_sanitario"]
                                                    + base["massa_enviada_inertes"]) * 100
    assert (calculado - base["IRS3002"]).abs().lt(5).mean() > 0.95
    assert calculado.corr(base["IRS3002"]) > 0.9
    assert (m.loc[m["IRS3002"] == 0, "massa_enviada_inadequada"] == 0).all()
    assert (m.loc[m["IRS3002"] > 0, "massa_enviada_inadequada"] > 0).mean() > 0.95
