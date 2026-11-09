"""Etapa 3: o IRS3002 sai das rotas de coleta declaradas pelo município; os zeros são explicados por elas."""

import pandas as pd
import pytest

import calculos as c
import etl_sqlite as etl


def rotas_sinteticas():
    # (município, tipo de unidade de destino, massa da rota)
    linhas = [
        (1, "Aterro sanitário", 80.0), (1, "Aterro de inertes", 20.0),
        (2, "Lixão ou vazadouro", 10.0), (2, "Aterro sanitário", 90.0),
        (3, "Aterro controlado", 5.0),
        (4, "Unidade de triagem (galpão ou usina)", 30.0), (4, "Unidade de Transbordo", 20.0),
        (5, "Aterro sanitário", "n/d"),                     # massa não numérica é descartada
        (6, None, None),                                    # município que não respondeu
    ]
    return pd.DataFrame({"Cod_IBGE": [l[0] for l in linhas], etl.COLUNA_TIPO_DESTINO: [l[1] for l in linhas],
                         etl.COLUNA_MASSA_ROTA: [l[2] for l in linhas]})


def massas_sinteticas():
    return pd.DataFrame({"Cod_IBGE": [1, 2, 3, 4, 6], "GTR1028": [100.0, 100.0, 5.0, 100.0, 10.0],
                         "GTR1029": [0, 0, 0, 0, None]})


@pytest.mark.parametrize("tipo, classe", [
    ("Lixão ou vazadouro", "inadequada"), (" Aterro controlado ", "inadequada"),
    ("Aterro sanitário", "aterro_adequado"), ("Aterro de inertes", "aterro_adequado"),
    ("Unidade de Transbordo", "intermediaria"), ("Unidade de triagem (galpão ou usina)", "intermediaria"),
    ("Unidade de compostagem", "intermediaria"), ("Unidade de coprocessamento", "intermediaria"),
    ("Unidade de manejo de resíduos de áreas verdes (galhadas e podas)", "intermediaria"),
    ("Área de Transbordo e Triagem de resíduos da construção civil e volumosos (ATT)", "intermediaria"),
])
def test_classificar_destino(tipo, classe):
    assert etl.classificar_destino(tipo) == classe


def test_tipo_de_destino_desconhecido_interrompe_o_etl():
    with pytest.raises(SystemExit):
        etl.classificar_destino("Incinerador")


def test_preparar_destinacao_soma_rotas_por_municipio():
    d = etl.preparar_destinacao(rotas_sinteticas(), massas_sinteticas(), ["1", "2", "3", "4", "5", "6", "7"])
    d = d.set_index("cod_ibge")
    assert len(d) == 7
    colunas = ["massa_rota_inadequada", "massa_rota_aterro_adequado", "massa_rota_intermediaria"]
    assert d.loc["1", colunas].tolist() == [0, 100, 0]
    assert d.loc["2", colunas].tolist() == [10, 90, 0]
    assert d.loc["3", colunas].tolist() == [5, 0, 0]
    assert d.loc["4", colunas].tolist() == [0, 0, 50]
    assert d.loc["5", colunas].sum() == 0 and d.loc["6", colunas].sum() == 0 and d.loc["7", colunas].sum() == 0
    assert d.loc["1", "massa_coletada"] == 100
    assert pd.isna(d.loc["5", "massa_coletada"])                          # município sem linha na aba de massas


def _tabela(codigos, valores=None):
    return pd.DataFrame({"cod_ibge": codigos, "IRS3002": valores or [0] * len(codigos)})


def _destino(**linhas):
    """linhas: cod -> (inadequada, aterro_adequado, intermediaria, coletada, recuperada)."""
    return pd.DataFrame([{"cod_ibge": k, "massa_rota_inadequada": v[0], "massa_rota_aterro_adequado": v[1],
                          "massa_rota_intermediaria": v[2], "massa_coletada": v[3], "massa_recuperada": v[4]}
                         for k, v in linhas.items()])


def test_classificar_zeros_regras():
    dest = _destino(a=(0, 95, 0, 100, 0),         # aterro cobre 95%
                    b=(0, 50, 0, 100, 0),         # só 50% declarado
                    c=(0, 0, 0, 100, 0),          # nenhuma rota
                    d=(7, 90, 0, 100, 0),         # rota a lixão
                    e=(0, 0, 80, 100, 0),         # só intermediárias: destino final não informado
                    f=(0, 45, 45, 100, 10),       # 45 de 90 em aterro; 90/90 com intermediárias
                    g=(0, 10, 0, None, None),     # massa coletada não informada: basta haver rota a aterro
                    i=(0, 90, 0, 100, 0))         # exatamente no limite de 90%
    tabela = _tabela(list("abcdefghi"), [0] * 9)
    tabela.index = list(range(10, 19))
    r = c.classificar_zeros(tabela, dest)
    assert r[10] == c.EVIDENCIA_CONFIRMADO
    assert r[11] == c.EVIDENCIA_INCOMPLETA
    assert r[12] == c.EVIDENCIA_INCOMPLETA
    assert r[13] == c.EVIDENCIA_CONTRADICAO
    assert r[14] == c.EVIDENCIA_INCOMPLETA            # 80/100 < 90%
    assert r[15] == c.EVIDENCIA_INTERMEDIARIA
    assert r[16] == c.EVIDENCIA_CONFIRMADO
    assert r[17] == c.EVIDENCIA_INCOMPLETA            # município ausente da tabela de destinação
    assert r[18] == c.EVIDENCIA_CONFIRMADO            # limite inclusivo


def test_classificar_zeros_ignora_nao_zeros_e_preserva_indice():
    dest = _destino(a=(0, 95, 0, 100, 0), b=(0, 95, 0, 100, 0))
    tabela = pd.DataFrame({"cod_ibge": ["a", "b"], "IRS3002": [0, 50]}, index=[5, 3])
    r = c.classificar_zeros(tabela, dest)
    assert r[5] == c.EVIDENCIA_CONFIRMADO and pd.isna(r[3])


def test_limite_de_cobertura_e_parametrizavel():
    dest = _destino(a=(0, 90, 0, 100, 0))
    assert c.classificar_zeros(_tabela(["a"]), dest).iloc[0] == c.EVIDENCIA_CONFIRMADO
    assert c.classificar_zeros(_tabela(["a"]), dest, limite_cobertura=0.91).iloc[0] == c.EVIDENCIA_INCOMPLETA


def test_banco_tem_destinacao_para_todos_os_municipios(conn):
    assert conn.execute("SELECT COUNT(*) FROM destinacao_municipio").fetchone()[0] == 5570


def test_irs3002_e_exatamente_reproduzido_pelas_rotas(tabela, conn):
    """O indicador é massa das rotas a lixão/aterro controlado / massa coletada líquida x 100."""
    m = tabela.merge(pd.read_sql_query(c.CONSULTA_DESTINACAO, conn), on="cod_ibge")
    liquida = m["massa_coletada"] - m["massa_recuperada"].fillna(0)
    assert (liquida > 0).all()
    calculado = m["massa_rota_inadequada"] / liquida * 100
    assert (calculado - m["IRS3002"]).abs().max() < 0.05
    assert len(m) == 4854


def test_numeros_dos_zeros_do_irs3002(tabela, conn):
    dest = pd.read_sql_query(c.CONSULTA_DESTINACAO, conn)
    evid = c.resumo_evidencia_zeros(tabela, dest)
    assert evid.sum() == 3057
    assert evid[c.EVIDENCIA_CONFIRMADO] == 2880
    assert evid[c.EVIDENCIA_INTERMEDIARIA] == 174
    assert evid[c.EVIDENCIA_INCOMPLETA] == 3
    assert evid[c.EVIDENCIA_CONTRADICAO] == 0            # nenhum zero declara rota a lixão


def test_nenhuma_uf_tem_fracao_relevante_de_zeros_sem_aterro(tabela, conn):
    """Evita reintroduzir um alerta por UF: com as rotas, nenhuma UF passa de 15% de zeros sem rota a aterro."""
    dest = pd.read_sql_query(c.CONSULTA_DESTINACAO, conn)
    classe = c.classificar_zeros(tabela, dest)
    z = tabela.assign(classe=classe).dropna(subset=["classe"])
    por_uf = z.groupby("uf")["classe"].apply(lambda s: (s != c.EVIDENCIA_CONFIRMADO).mean())
    assert por_uf.max() < 0.15
