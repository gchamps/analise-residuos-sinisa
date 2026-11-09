"""
Cálculos compartilhados pelo dashboard (app.py), pela análise (analise_estatistica.py)
e pela planilha (gerar_planilha.py). Não depende de Streamlit.

Convenções:
  * "Média ponderada" usa a população total do município como peso.
  * `excluir_sinalizados` remove os valores marcados no ETL (coluna flag_qualidade);
    por padrão eles são mantidos.
"""

import pandas as pd

INDICADORES = ["IRS0001", "IRS0005", "IRS1004", "IRS3001", "IRS3002", "IRS3010"]
CHAVE_MUNICIPIO = ["cod_ibge", "nome_municipio", "uf", "regiao", "populacao_total"]
FAIXAS_POP = [0, 10_000, 50_000, 200_000, 1_000_000, float("inf")]
ROTULOS_FAIXA = ["até 10 mil", "10 a 50 mil", "50 a 200 mil", "200 mil a 1 mi", "mais de 1 mi"]

CONSULTA_RESULTADOS = """
    SELECT m.cod_ibge, m.nome_municipio, m.uf, m.regiao, m.populacao_total,
           r.codigo_indicador, r.valor, r.flag_qualidade
    FROM resultado_indicador r
    JOIN municipio m ON m.cod_ibge = r.cod_ibge
"""


def montar_tabela(resultados, excluir_sinalizados=False):
    """Uma linha por município e uma coluna por indicador (formato largo)."""
    base = resultados
    if excluir_sinalizados:
        base = base[base["flag_qualidade"].isna()]
    tabela = base.pivot_table(index=CHAVE_MUNICIPIO, columns="codigo_indicador", values="valor").reset_index()
    tabela.columns.name = None
    return tabela.sort_values("cod_ibge").reset_index(drop=True)


def media_ponderada(valores, pesos):
    """Média de `valores` ponderada por `pesos`, ignorando linhas sem valor."""
    validos = valores.notna()
    pesos_validos = pesos[validos]
    if pesos_validos.sum() == 0:
        return float("nan")
    return float((valores[validos] * pesos_validos).sum() / pesos_validos.sum())


def resumo_indicador(serie, pesos):
    """Estatísticas de um indicador (média ponderada usa a população como peso)."""
    s = serie[serie.notna()]
    if s.empty:
        return {"N": 0, "Média": None, "Mediana": None, "Desvio-padrão": None, "Mínimo": None,
                "Máximo": None, "% = 0": None, "% = 100": None, "Média ponderada": None}
    return {
        "N": int(s.count()),
        "Média": s.mean(),
        "Mediana": s.median(),
        "Desvio-padrão": s.std(ddof=1),
        "Mínimo": s.min(),
        "Máximo": s.max(),
        "% = 0": (s == 0).mean() * 100,
        "% = 100": (s == 100).mean() * 100,
        "Média ponderada": media_ponderada(serie, pesos),
    }


def _posicoes(serie):
    """1 = pior (maior valor); empates ficam com a menor posição."""
    return serie.rank(method="min", ascending=False).astype("Int64")


def ranking_uf(tabela, indicador="IRS3002"):
    """Média simples e ponderada do indicador por UF, com posições (1 = pior).

    Municípios sem valor no indicador (por exemplo, após excluir valores suspeitos) ficam fora de
    `n_municipios` e das médias. Ordenado por posição simples e, no empate, por UF.
    """
    base = tabela.dropna(subset=[indicador])
    linhas = []
    for uf, grupo in base.groupby("uf"):
        linhas.append({
            "uf": uf,
            "n_municipios": len(grupo),
            "media_simples": grupo[indicador].mean(),
            "media_ponderada": media_ponderada(grupo[indicador], grupo["populacao_total"]),
        })
    ranking = pd.DataFrame(linhas, columns=["uf", "n_municipios", "media_simples", "media_ponderada"])
    ranking["n_municipios"] = ranking["n_municipios"].astype(int)
    ranking["posicao_simples"] = _posicoes(ranking["media_simples"])
    ranking["posicao_ponderada"] = _posicoes(ranking["media_ponderada"])
    return ranking.sort_values(["posicao_simples", "uf"]).reset_index(drop=True)


def resumo_regioes(tabela, indicador="IRS3002"):
    """Média simples, ponderada e proporção de 0% e 100% por macrorregião."""
    base = tabela.dropna(subset=[indicador])
    linhas = []
    for regiao, grupo in base.groupby("regiao"):
        linhas.append({
            "regiao": regiao,
            "n_municipios": len(grupo),
            "media_simples": grupo[indicador].mean(),
            "media_ponderada": media_ponderada(grupo[indicador], grupo["populacao_total"]),
            "prob_cem": (grupo[indicador] == 100).mean(),
            "prob_zero": (grupo[indicador] == 0).mean(),
        })
    return pd.DataFrame(linhas).sort_values("regiao").reset_index(drop=True)


def resumo_por_faixa(tabela, indicador="IRS3002"):
    """Média do indicador por faixa de população do município."""
    faixa = pd.cut(tabela["populacao_total"], FAIXAS_POP, labels=ROTULOS_FAIXA, right=True)
    return (tabela.assign(faixa=faixa).groupby("faixa", observed=True)
            .agg(municipios=(indicador, "size"), disposicao=(indicador, "mean")).reset_index())


CONSULTA_DESTINACAO = "SELECT * FROM destinacao_municipio"
EVIDENCIA_CONFIRMADO = "0% confirmado"
EVIDENCIA_NAO_VERIFICADO = "0% não verificado"
EVIDENCIA_CONTRADICAO = "0% contraditório"
ROTULOS_EVIDENCIA = [EVIDENCIA_CONFIRMADO, EVIDENCIA_NAO_VERIFICADO, EVIDENCIA_CONTRADICAO]


def classificar_zeros(tabela, destinacao, indicador="IRS3002"):
    """Classifica os municípios com `indicador` = 0 pela evidência de infraestrutura.

    * confirmado: sedia aterro sanitário em operação e nenhuma unidade inadequada (destinação adequada comprovada);
    * contraditório: sedia lixão, vazadouro ou aterro controlado em operação (o 0% contradiz a infraestrutura);
    * não verificado: não sedia unidade nenhuma ou só aterro de inertes. Pode enviar os resíduos a outro município
      ou não ter informado: os dados do SINISA não permitem confirmar.

    Devolve uma Series alinhada a `tabela`, com NaN onde o valor não é zero.
    """
    info = tabela[["cod_ibge"]].merge(destinacao, on="cod_ibge", how="left")
    inadequadas = info["unidades_inadequadas_operacao"].fillna(0).to_numpy() > 0
    sanitarios = info["aterros_sanitarios_operacao"].fillna(0).to_numpy() > 0
    classe = pd.Series(EVIDENCIA_NAO_VERIFICADO, index=tabela.index, dtype="object")
    classe[sanitarios] = EVIDENCIA_CONFIRMADO
    classe[inadequadas] = EVIDENCIA_CONTRADICAO
    return classe.where(tabela[indicador] == 0)


def resumo_evidencia_zeros(tabela, destinacao, indicador="IRS3002"):
    """Contagem de zeros por classe de evidência, na ordem de ROTULOS_EVIDENCIA."""
    classes = classificar_zeros(tabela, destinacao, indicador).dropna()
    return classes.value_counts().reindex(ROTULOS_EVIDENCIA, fill_value=0)


def formatar(valor, casas=2, sufixo=""):
    """Número no padrão brasileiro (vírgula decimal, ponto de milhar)."""
    if valor is None or pd.isna(valor):
        return "sem dados"
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto + sufixo
