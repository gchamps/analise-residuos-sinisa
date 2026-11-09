"""
MPV - Análise e Diagnóstico da Gestão de Resíduos Sólidos Urbanos (Streamlit).

Fonte: Ministério das Cidades - SINISA 2025 (ano de referência 2024).
Pré-requisito: banco gerado por scripts/etl_sqlite.py (dados_tratados/projeto_residuos.db).

Execução, a partir da raiz do projeto:
    streamlit run scripts/app.py
"""

import os
import sqlite3
import sys

import altair as alt
import pandas as pd
import streamlit as st
from scipy.stats import spearmanr

_PASTA_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if _PASTA_SCRIPTS not in sys.path:  # o Streamlit já costuma incluir a pasta; garante sem duplicar a cada interação
    sys.path.append(_PASTA_SCRIPTS)
from calculos import (CONSULTA_DESTINACAO, CONSULTA_RESULTADOS, EVIDENCIA_CONFIRMADO, INDICADORES,  # noqa: E402
                      ROTULOS_EVIDENCIA, classificar_zeros, formatar, montar_tabela, ranking_uf,
                      resumo_evidencia_zeros, resumo_indicador, resumo_por_faixa)
from mapa import preparar_mapa  # noqa: E402

st.set_page_config(page_title="MPV - Resíduos Sólidos", layout="wide")
alt.data_transformers.disable_max_rows()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_BANCO = os.path.normpath(os.path.join(BASE_DIR, "..", "dados_tratados", "projeto_residuos.db"))
CAMINHO_MAPA = os.path.normpath(os.path.join(BASE_DIR, "..", "dados_tratados", "br_ufs.geojson"))  # malha das UFs, IBGE
# (código, rótulo curto, sufixo da unidade)
KPIS = [
    ("IRS3002", "Disposição inadequada", "%"),
    ("IRS0001", "Cobertura da coleta", "%"),
    ("IRS1004", "Massa per capita", ""),
]
UNIDADE_KPI = {"IRS3002": "% dos resíduos coletados", "IRS0001": "% da população atendida", "IRS1004": "kg por habitante por dia"}
# Nomes curtos para tabelas (o nome oficial completo fica na dica e na aba Método)
CURTOS = {"IRS0001": "Cobertura da coleta (%)", "IRS0005": "Coleta seletiva (%)", "IRS1004": "Massa per capita (kg/hab.dia)",
          "IRS3001": "Desempenho da coleta seletiva (%)", "IRS3002": "Disposição inadequada (%)",
          "IRS3010": "Recuperação de recicláveis (%)"}
TODO_BRASIL = "Brasil (todas as UFs)"


# -----------------------------------------------------------------------------
# Dados
# -----------------------------------------------------------------------------
@st.cache_data
def carregar_dados(caminho, modificado_em):
    """`modificado_em` entra na chave do cache: se o ETL regerar o banco, o app recarrega os dados."""
    conn = sqlite3.connect(caminho)
    try:
        resultados = pd.read_sql_query(CONSULTA_RESULTADOS, conn)
        municipios = pd.read_sql_query("SELECT uf, respondeu FROM municipio", conn)
        catalogo = pd.read_sql_query("SELECT codigo, nome, unidade, definicao FROM indicador ORDER BY codigo", conn)
        destinacao = pd.read_sql_query(CONSULTA_DESTINACAO, conn)
    finally:
        conn.close()
    return resultados, municipios, catalogo, destinacao


# -----------------------------------------------------------------------------
# Carga com mensagens de erro claras
# -----------------------------------------------------------------------------
if not os.path.exists(CAMINHO_BANCO):
    st.error("Banco de dados não encontrado. Execute primeiro: python scripts/etl_sqlite.py")
    st.stop()

try:
    df_resultados, df_municipios, df_catalogo, df_destinacao = carregar_dados(CAMINHO_BANCO, os.path.getmtime(CAMINHO_BANCO))
except (sqlite3.OperationalError, pd.errors.DatabaseError):
    st.error("O banco de dados está desatualizado. Execute novamente: python scripts/etl_sqlite.py")
    st.stop()

nomes = dict(zip(df_catalogo["codigo"], df_catalogo["nome"]))

# -----------------------------------------------------------------------------
# Estilo
# -----------------------------------------------------------------------------
# Regra de cor: verde = identidade e coisas "boas" (coleta seletiva); ferrugem = só para "pior"
# (disposição inadequada); cinza = referência; azul/roxo/etc. = apenas distinguir grupos.
COR_PRINCIPAL = "#1F5E4B"
COR_DESTAQUE = "#B5451B"
COR_NEUTRA = "#B9B4A6"
COR_TEXTO = "#1F2A24"
RAMPA_PIOR = ["#F1EADB", "#E6C7A3", "#D79A68", "#BF6638", "#8C2F10"]   # sequencial: claro = menos, escuro = mais disposição inadequada
ESCALA_PIOR = alt.Scale(domain=[0, 25, 50, 75, 100], range=RAMPA_PIOR)
CORES_GRUPOS = ["#1F5E4B", "#4C6A92", "#7A5C8A", "#2E8B8B", "#8C6A3F"]

st.markdown(
    """
    <style>
    .block-container {padding-top: 4rem; max-width: 1180px;}
    .kicker {font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: #6B6F66; margin-bottom: 0.2rem;}
    .lede {font-family: serif; font-size: 1.35rem; line-height: 1.45; margin: 0.4rem 0 1.4rem 0; max-width: 62rem;}
    div[data-testid="stMetricValue"] {font-family: serif;}
    div[data-testid="stMetricLabel"] p {font-size: 0.85rem;}
    div[data-testid="stHorizontalBlock"] {align-items: stretch !important;}
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {height: 100%;}
    div[data-testid="stColumn"] > div > div[data-testid="stVerticalBlockBorderWrapper"] {height: 100%;}
    div[data-testid="stVerticalBlockBorderWrapper"] {background: #FFFFFF; border: 1px solid #D6D1C4; border-radius: 6px;}
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"] {border: none; background: transparent;}
    .passo {font-size: 0.74rem; letter-spacing: 0.1em; text-transform: uppercase; color: #B5451B; font-weight: 600; margin: 0 0 -0.4rem 0;}
    hr {border-color: #D6D1C4 !important;}
    @media (max-width: 640px) {
        .block-container {padding-top: 3rem;}
        h1 {font-size: 2rem !important; line-height: 1.15 !important;}
        .lede {font-size: 1.1rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def estilizar(grafico):
    """Área de plotagem emoldurada, eixos com linha e marcas, grade vertical leve (barras horizontais)."""
    return (
        grafico.configure_view(fill="#FCFBF8", stroke="#CFC9BA", strokeWidth=1)
        .configure_axis(grid=False, domain=True, domainColor="#6B6F66", domainWidth=1.2,
                        ticks=True, tickColor="#6B6F66", tickSize=5,
                        labelColor=COR_TEXTO, titleColor="#4A4F47", labelFontSize=12, titleFontSize=12,
                        titleFontWeight="normal", titlePadding=10)
        .configure_axisX(grid=True, gridColor="#E6E1D4", gridDash=[2, 3])
        .configure_legend(labelColor=COR_TEXTO, titleColor="#4A4F47", labelFontSize=12, titleFontSize=12)
    )


# -----------------------------------------------------------------------------
# Filtros
# -----------------------------------------------------------------------------
st.sidebar.header("Recorte")
ufs_disponiveis = sorted(df_resultados["uf"].unique().tolist())
uf_selecionada = st.sidebar.selectbox("Estado (UF)", [TODO_BRASIL] + ufs_disponiveis)
with st.sidebar.expander("Opções avançadas"):
    excluir = st.checkbox(
        "Excluir valores suspeitos",
        value=False,
        help="Remove dos cálculos os valores marcados no ETL (percentual acima de 100 e massa per capita acima de 3 kg/hab.dia). "
             "Afeta poucos registros (59 de massa per capita e 4 de desempenho da coleta seletiva).",
    )
st.sidebar.caption("Fonte: Ministério das Cidades, SINISA 2025 (ano de referência 2024). Só entram municípios que responderam ao módulo de resíduos.")

tabela_brasil = montar_tabela(df_resultados, excluir)
if uf_selecionada == TODO_BRASIL:
    tabela = tabela_brasil
    municipios_escopo = df_municipios
else:
    tabela = tabela_brasil[tabela_brasil["uf"] == uf_selecionada]
    municipios_escopo = df_municipios[df_municipios["uf"] == uf_selecionada]

n_resp = int(municipios_escopo["respondeu"].sum())
n_total = len(municipios_escopo)
resumo_br = {c: resumo_indicador(tabela_brasil[c], tabela_brasil["populacao_total"]) for c in INDICADORES}
resumo_uf = {c: resumo_indicador(tabela[c], tabela["populacao_total"]) for c in INDICADORES}
ranking = ranking_uf(tabela_brasil)

# Recortes que sustentam a narrativa (sempre sobre o Brasil todo, para comparar)
por_regiao = tabela_brasil.groupby("regiao").agg(
    municipios=("IRS3002", "size"), disposicao=("IRS3002", "mean"), coleta_seletiva=("IRS0005", "mean")).reset_index()
por_faixa = resumo_por_faixa(tabela_brasil)
zeros_uf = tabela_brasil.dropna(subset=["IRS3002"]).groupby("uf")["IRS3002"].agg(
    n="size", pct_zero=lambda v: (v == 0).mean() * 100)
suspeitas = zeros_uf[(zeros_uf["n"] >= 10) & (zeros_uf["pct_zero"] > 90)].sort_values("pct_zero", ascending=False)
suspeitas_txt = ", ".join(suspeitas.index) if len(suspeitas) else ""
# Classificação dos zeros do IRS3002 pelo destino das rotas de coleta declaradas (planilha de Manejo)
tabela_brasil = tabela_brasil.assign(evidencia_zero=classificar_zeros(tabela_brasil, df_destinacao))
zeros_classificados = tabela_brasil[tabela_brasil["evidencia_zero"].notna()]
pct_confirmado_suspeitas = None
zeros_das_suspeitas = zeros_classificados[zeros_classificados["uf"].isin(suspeitas.index)]
if len(zeros_das_suspeitas):
    pct_confirmado_suspeitas = float((zeros_das_suspeitas["evidencia_zero"] == EVIDENCIA_CONFIRMADO).mean() * 100)
pior_regiao = por_regiao.sort_values("disposicao").iloc[-1]
melhor_regiao = por_regiao.sort_values("disposicao").iloc[0]
regiao_da_uf = None
if uf_selecionada != TODO_BRASIL:
    regiao_da_uf = tabela_brasil.loc[tabela_brasil["uf"] == uf_selecionada, "regiao"].iloc[0]

# -----------------------------------------------------------------------------
# Cabeçalho
# -----------------------------------------------------------------------------
st.markdown('<div class="kicker">Projeto de extensão · FATEC São Bernardo do Campo · SINISA 2025 (dados de 2024)</div>',
            unsafe_allow_html=True)
st.title("Para onde vão os resíduos dos municípios brasileiros?")

m3002 = resumo_uf["IRS3002"]
if uf_selecionada == TODO_BRASIL:
    lede = (f"Nos {formatar(n_resp, 0)} municípios que responderam, a destinação para lixão, vazadouro ou aterro controlado é, "
            f"em média, de {formatar(m3002['Média'], 1, '%')} dos resíduos coletados por município. Mas a média esconde uma "
            f"desigualdade regional: {formatar(pior_regiao['disposicao'], 0, '%')} na região {pior_regiao['regiao']} contra "
            f"{formatar(melhor_regiao['disposicao'], 0, '%')} na região {melhor_regiao['regiao']} (média dos municípios de cada região).")
else:
    linha = ranking[ranking["uf"] == uf_selecionada]
    pos = f" ({int(linha.iloc[0]['posicao_simples'])}ª pior entre {len(ranking)} UFs)" if not linha.empty else ""
    lede = (f"Em {uf_selecionada}, a destinação para lixão, vazadouro ou aterro controlado é, em média, de "
            f"{formatar(m3002['Média'], 1, '%')} dos resíduos coletados por município{pos}, "
            f"contra {formatar(resumo_br['IRS3002']['Média'], 1, '%')} no Brasil. "
            f"Ponderando pela população, {formatar(m3002['Média ponderada'], 1, '%')}.")
st.markdown(f'<p class="lede">{lede}</p>', unsafe_allow_html=True)
st.caption(f"{formatar(n_resp, 0)} de {formatar(n_total, 0)} municípios do recorte responderam ao módulo de resíduos ({formatar(n_resp / n_total * 100, 1)}%).")

colunas = st.columns(len(KPIS))
for coluna, (codigo, rotulo, sufixo) in zip(colunas, KPIS):
    r = resumo_uf[codigo]
    base = resumo_br[codigo]["Média"]
    delta = None
    if uf_selecionada != TODO_BRASIL and r["Média"] is not None and not pd.isna(r["Média"]):
        diferenca = r["Média"] - base
        unidade_delta = "p.p." if sufixo == "%" else "kg/hab.dia"
        delta = f"{'+' if diferenca >= 0 else '-'}{formatar(abs(diferenca), 2)} {unidade_delta} vs. Brasil"
    with coluna.container(border=True):
        st.metric(rotulo, formatar(r["Média"], 2, sufixo), delta,
                  delta_color="inverse" if codigo == "IRS3002" else ("off" if codigo == "IRS1004" else "normal"),
                  help=f"{codigo} - {nomes[codigo]}. Média simples dos municípios.")
        st.caption(f"{UNIDADE_KPI[codigo]}  \nMediana {formatar(r['Mediana'], 2, sufixo)}  \nMédia ponderada {formatar(r['Média ponderada'], 2, sufixo)}")

st.divider()
aba_panorama, aba_estados, aba_municipios, aba_metodo = st.tabs(["Panorama", "Estados", "Municípios", "Método e limitações"])

# -----------------------------------------------------------------------------
# Panorama: a história em quatro passos (onde, quanto, quem, por que a média engana)
# -----------------------------------------------------------------------------
@st.cache_data
def mapa_das_ufs(caminho, valores_uf, uf_selecionada):
    """Feições (valor e rótulo por UF) e siglas do mapa; só é refeito quando o recorte muda."""
    return preparar_mapa(caminho, dict(valores_uf), uf_selecionada, formatar)


with aba_panorama:
    with st.container(border=True):
        st.markdown('<div class="passo">Regiões</div>', unsafe_allow_html=True)
        # 1) Onde: regiões ---------------------------------------------------------
        st.subheader(f"Onde é pior: os municípios da região {pior_regiao['regiao']} destinam, em média, "
                     f"{formatar(pior_regiao['disposicao'], 0, '%')} dos resíduos de forma inadequada; os da {melhor_regiao['regiao']}, "
                     f"{formatar(melhor_regiao['disposicao'], 0, '%')}")
        ordem_reg = por_regiao.sort_values("disposicao", ascending=False)["regiao"].tolist()

        def painel_regiao(coluna, titulo, cor, mostrar_rotulos_y):
            d = por_regiao.assign(rotulo=por_regiao[coluna].map(lambda v: formatar(v, 1, "%")))
            opacidade = (alt.condition(alt.datum.regiao == regiao_da_uf, alt.value(1.0), alt.value(0.5))
                         if regiao_da_uf else alt.value(1.0))
            eixo_y = alt.Axis(labelPadding=6) if mostrar_rotulos_y else alt.Axis(labels=False, ticks=False, domain=False)
            base = alt.Chart(d).encode(
                y=alt.Y("regiao:N", sort=ordem_reg, title=None, axis=eixo_y),
                x=alt.X(f"{coluna}:Q", title=titulo, scale=alt.Scale(domain=[0, 100])))
            barras = base.mark_bar(color=cor).encode(opacity=opacidade, tooltip=["regiao", alt.Tooltip("rotulo:N", title="média")])
            textos = base.mark_text(align="left", dx=4, fontSize=12, color=COR_TEXTO).encode(text="rotulo:N")
            return (barras + textos).properties(height=210)

        col_a, col_b = st.columns(2)
        col_a.altair_chart(estilizar(painel_regiao("disposicao", "Disposição inadequada (%)", COR_DESTAQUE, True)), width="stretch")
        col_b.altair_chart(estilizar(painel_regiao("coleta_seletiva", "Cobertura da coleta seletiva (%)", COR_PRINCIPAL, True)), width="stretch")
        st.caption("Média simples dos municípios respondentes de cada região. Onde a disposição inadequada é maior, "
                   "a coleta seletiva tende a ser menor."
                   + (f" A região de {uf_selecionada} ({regiao_da_uf}) está em destaque." if regiao_da_uf else ""))

    with st.container(border=True):
        st.markdown('<div class="passo">Mapa</div>', unsafe_allow_html=True)
        # 2) Mapa --------------------------------------------------------------------
        ordenado = ranking.sort_values("media_simples", ascending=False)
        piores = ", ".join(ordenado["uf"].head(3))
        st.subheader(f"No mapa: os maiores percentuais de disposição inadequada estão em {piores}")
        valores_uf = tuple(sorted(ranking.set_index("uf")["media_simples"].items()))
        feicoes, siglas = mapa_das_ufs(CAMINHO_MAPA, valores_uf, uf_selecionada)
        mapa = alt.Chart(alt.Data(values=feicoes)).mark_geoshape().encode(
            color=alt.Color("properties.valor:Q", scale=ESCALA_PIOR,
                            legend=alt.Legend(title="% disposição inadequada", orient="right", gradientLength=180)),
            stroke=alt.condition("datum.properties.sel", alt.value(COR_TEXTO), alt.value("#FFFFFF")),
            strokeWidth=alt.condition("datum.properties.sel", alt.value(2.5), alt.value(0.8)),
            tooltip=[alt.Tooltip("properties.uf:N", title="UF"), alt.Tooltip("properties.rotulo:N", title="disposição inadequada")])
        rotulos_mapa = alt.Chart(pd.DataFrame(siglas)).mark_text(fontSize=10, color=COR_TEXTO, fontWeight="bold").encode(
            longitude="lon:Q", latitude="lat:Q", text="uf:N")
        st.altair_chart(estilizar((mapa + rotulos_mapa).project(type="mercator").properties(height=480)))
        st.caption("Média simples do IRS3002 (disposição final inadequada) dos municípios de cada UF. Quanto mais escuro, pior."
                   + (f" Em {suspeitas_txt}, mais de 90% dos municípios registram exatamente 0%, e "
                      f"{formatar(pct_confirmado_suspeitas, 0, '%')} desses zeros declaram rotas para aterro sanitário "
                      "ou de inertes que cobrem ao menos 90% da massa coletada líquida. O valor vem da declaração de cada município; veja o quadro \"O que significa um 0%?\", "
                      "em Distribuição." if suspeitas_txt and pct_confirmado_suspeitas is not None else ""))

    with st.container(border=True):
        st.markdown('<div class="passo">Porte dos municípios</div>', unsafe_allow_html=True)
        # 3) Porte -------------------------------------------------------------------
        pior_faixa = por_faixa.sort_values("disposicao").iloc[-1]
        melhor_faixa = por_faixa.sort_values("disposicao").iloc[0]
        st.subheader(f"Por porte: a maior disposição inadequada está nos municípios de {pior_faixa['faixa']} habitantes "
                     f"({formatar(pior_faixa['disposicao'], 0, '%')}); a menor, nos de {melhor_faixa['faixa']} "
                     f"({formatar(melhor_faixa['disposicao'], 0, '%')})")
        pf = por_faixa.assign(
            rotulo=por_faixa["disposicao"].map(lambda v: formatar(v, 1, "%")),
            eixo=[f"{fx} hab. ({formatar(n, 0)})" for fx, n in zip(por_faixa["faixa"], por_faixa["municipios"])])
        ordem_faixa = pf["eixo"].tolist()
        base_pf = alt.Chart(pf).encode(
            y=alt.Y("eixo:N", sort=ordem_faixa, title=None, axis=alt.Axis(labelPadding=6, labelLimit=260)),
            x=alt.X("disposicao:Q", title="Disposição inadequada (%)", scale=alt.Scale(domain=[0, 100])))
        barras_pf = base_pf.mark_bar(color=COR_DESTAQUE).encode(
            opacity=alt.condition(alt.datum.disposicao == float(pior_faixa["disposicao"]), alt.value(1.0), alt.value(0.5)),
            tooltip=["eixo", alt.Tooltip("rotulo:N", title="média")])
        textos_pf = base_pf.mark_text(align="left", dx=4, fontSize=12, color=COR_TEXTO).encode(text="rotulo:N")
        st.altair_chart(estilizar((barras_pf + textos_pf).properties(height=210)))
        base_pop = tabela_brasil.dropna(subset=["IRS3002"])
        pct_pop = base_pop.loc[base_pop["IRS3002"] > 50, "populacao_total"].sum() / base_pop["populacao_total"].sum() * 100
        st.caption(f"Média simples por faixa de população; entre parênteses, o número de municípios. "
                   f"{formatar(pct_pop, 0)}% da população dos municípios respondentes vive onde mais da metade dos resíduos "
                   "vai para disposição inadequada.")

    with st.container(border=True):
        st.markdown('<div class="passo">Distribuição</div>', unsafe_allow_html=True)
        # 4) Por que a média engana -----------------------------------------------------
        pct_indic = [c for c in INDICADORES if c != "IRS1004"]
        rotulos_sit4 = ["0%", "1% a 99%", "100%"]
        linhas_d = []
        for c in pct_indic:
            v = tabela[c].dropna()
            if len(v) == 0:
                continue
            z, cem = (v == 0).mean() * 100, (v >= 100).mean() * 100
            for ordem_s, (sit, val) in enumerate(zip(rotulos_sit4, [z, 100 - z - cem, cem])):
                linhas_d.append({"indicador": CURTOS[c].replace(" (%)", ""), "situacao": sit, "pct": val, "ordem": ordem_s,
                                 "rotulo": formatar(val, 0, "%") if val >= 4 else ""})
        s3002 = tabela["IRS3002"].dropna()
        if len(s3002) and linhas_d:
            z3, c3 = (s3002 == 0).mean() * 100, (s3002 >= 100).mean() * 100
            if z3 == 100 or c3 == 100:
                st.subheader(f"Neste recorte, todos os municípios registram {'0%' if z3 == 100 else '100%'} de disposição inadequada")
                st.markdown("Não há variação entre os municípios deste recorte; o gráfico abaixo mostra como eles se dividem "
                            "nos demais indicadores.")
            else:
                st.subheader(f"Por que a média engana: {formatar(z3 + c3, 0, '%')} dos municípios registram 0% ou 100% de disposição inadequada")
                st.markdown(
                    f"A média ({formatar(s3002.mean(), 1, '%')}) não descreve um município típico. {formatar(z3, 0, '%')} registram 0%, "
                    f"{formatar(c3, 0, '%')} registram 100% e só {formatar(100 - z3 - c3, 0, '%')} ficam no meio. Por isso, em vez de só a média, "
                    "o gráfico abaixo mostra como os municípios se dividem em cada indicador.")
            df_d = pd.DataFrame(linhas_d).assign(pct_txt=lambda d: d["pct"].map(lambda v: formatar(v, 1, "%")))
            ordem_ind = list(dict.fromkeys(df_d["indicador"]))
            base_d = alt.Chart(df_d).encode(
                y=alt.Y("indicador:N", sort=ordem_ind, title=None, axis=alt.Axis(labelLimit=260, labelPadding=6, labelOverlap=False)),
                x=alt.X("pct:Q", title="% dos municípios", scale=alt.Scale(domain=[0, 100])))
            barras_d = base_d.mark_bar(size=26).encode(
                color=alt.Color("situacao:N", sort=rotulos_sit4,
                                scale=alt.Scale(domain=rotulos_sit4, range=["#C9CED6", "#E2D4B0", "#4C6A92"]),
                                legend=alt.Legend(title="Valor registrado", orient="top")),
                order=alt.Order("ordem:Q"),
                tooltip=["indicador", "situacao", alt.Tooltip("pct_txt:N", title="% dos municípios")])
            textos_d = base_d.mark_text(fontSize=12).encode(
                text="rotulo:N", order=alt.Order("ordem:Q"), x=alt.X("pct:Q", stack="zero", bandPosition=0.5),
                color=alt.condition(alt.datum.situacao == "100%", alt.value("#FFFFFF"), alt.value(COR_TEXTO)))
            st.altair_chart(estilizar((barras_d + textos_d).properties(height=44 * len(ordem_ind) + 90)))
            st.caption("Cada barra soma 100% dos municípios. Cinza: registraram 0%. Azul: registraram 100%. Areia: ficaram entre 1% e 99%. "
                       "No IRS3002, 0 significa que o município não declarou nenhuma rota de coleta para lixão, vazadouro ou aterro "
                       "controlado; nos demais indicadores, 0 pode indicar ausência do serviço ou da informação.")
            # Destino declarado dos municípios com 0% (rotas de coleta da planilha de Manejo)
            evid = resumo_evidencia_zeros(tabela, df_destinacao)
            total_z = int(evid.sum())
            if total_z:
                n_conf, n_inter, n_inc, n_contra = (int(evid[r]) for r in ROTULOS_EVIDENCIA)
                pct = lambda n: ("menos de 1%" if 0 < n / total_z < 0.005 else formatar(n / total_z * 100, 0, "%"))  # noqa: E731
                sujeito = "o único município com 0%" if total_z == 1 else f"os {formatar(total_z, 0)} municípios com 0%"
                st.markdown(
                    "**O que significa um 0%?** O IRS3002 é calculado a partir das rotas de coleta que cada município declara, "
                    "cada uma com o tipo de unidade de destino: 0% quer dizer que nenhuma rota vai a lixão, vazadouro ou aterro "
                    f"controlado. Entre {sujeito} neste recorte, {formatar(n_conf, 0)} ({pct(n_conf)}) "
                    "declararam rotas a aterro sanitário ou de inertes que cobrem ao menos 90% da massa coletada líquida; "
                    f"{formatar(n_inter, 0)} ({pct(n_inter)}) cobrem a massa só ao somar unidades intermediárias (transbordo, "
                    "triagem, compostagem), sem informar o destino final dos rejeitos; "
                    f"{formatar(n_inc, 0)} ({pct(n_inc)}) declararam rotas que cobrem menos de 90% da massa. "
                    + (f"{formatar(n_contra, 0)} declaram rota a lixão ou aterro controlado e ainda assim registram 0% (contradição). "
                       if n_contra else "Nenhum zero declara rota a lixão, vazadouro ou aterro controlado. ")
                    + "Os dados são autodeclarados: o SINISA mostra o que cada município informou, mas não comprova que o "
                      "destino informado é o real.")
                por_reg = (tabela_brasil.dropna(subset=["evidencia_zero"]).groupby(["regiao", "evidencia_zero"]).size()
                           .rename("n").reset_index())
                por_reg["pct"] = por_reg["n"] / por_reg.groupby("regiao")["n"].transform("sum") * 100
                por_reg["rotulo"] = por_reg["pct"].map(lambda v: formatar(v, 0, "%") if v >= 6 else "")
                por_reg["pct_txt"] = por_reg["pct"].map(lambda v: formatar(v, 1, "%"))
                por_reg["ordem"] = por_reg["evidencia_zero"].map({r: i for i, r in enumerate(ROTULOS_EVIDENCIA)})
                ordem_r = por_reg.groupby("regiao")["n"].sum().sort_values(ascending=False).index.tolist()
                ordem_e = ROTULOS_EVIDENCIA
                base_e = alt.Chart(por_reg).encode(
                    y=alt.Y("regiao:N", sort=ordem_r, title=None, axis=alt.Axis(labelPadding=6)),
                    x=alt.X("pct:Q", title="% dos municípios com 0% na região (Brasil)", scale=alt.Scale(domain=[0, 100])))
                barras_e = base_e.mark_bar(size=24).encode(
                    color=alt.Color("evidencia_zero:N", sort=ordem_e,
                                    scale=alt.Scale(domain=ordem_e, range=["#1F5E4B", "#D9A441", "#8A8F98", "#B5451B"]),
                                    legend=alt.Legend(title="Destino declarado", orient="top", columns=2, labelLimit=0, symbolLimit=0)),
                    order=alt.Order("ordem:Q"),
                    tooltip=["regiao", "evidencia_zero", alt.Tooltip("n:Q", title="municípios"),
                             alt.Tooltip("pct_txt:N", title="%")])
                textos_e = base_e.mark_text(fontSize=12, color="#FFFFFF").encode(
                    text="rotulo:N", order=alt.Order("ordem:Q"),
                    x=alt.X("pct:Q", stack="zero", bandPosition=0.5))
                st.altair_chart(estilizar((barras_e + textos_e).properties(height=36 * len(ordem_r) + 130)))
                st.caption("Fonte: rotas de coleta e tipo de unidade de destino da planilha de Manejo do SINISA, comparadas com a massa "
                           "coletada líquida (coletada menos recuperada). Aterro de inertes não é destino inadequado, como no IRS3002. "
                           "Transbordo, triagem e compostagem são etapas intermediárias: a rota não informa para onde vão os rejeitos.")
        with st.expander("Ver tabela estatística completa"):
            unidade_de = dict(zip(df_catalogo["codigo"], df_catalogo["unidade"]))
            linhas = []
            for c in INDICADORES:
                r = dict(resumo_uf[c])
                if unidade_de.get(c) != "Percentual":
                    r["% = 100"] = None  # "% = 100" só faz sentido para indicadores em percentual
                linhas.append({"Indicador": CURTOS[c], **r})
            st.dataframe(pd.DataFrame(linhas).round(2), hide_index=True,
                         column_config={col: st.column_config.NumberColumn(col, format="localized")
                                        for col in resumo_uf[INDICADORES[0]]})
        if uf_selecionada == "DF":
            st.caption("O DF tem apenas 1 município; interprete os resultados com cautela.")
        if uf_selecionada == "SP":
            st.caption("SP é o estado da empresa analisada no diagnóstico de qualidade do relatório. Os indicadores do SINISA "
                       "descrevem resíduos urbanos municipais e não avaliam a gestão de resíduos de empresas.")

# -----------------------------------------------------------------------------
# Estados: ranking e comparação
# -----------------------------------------------------------------------------
with aba_estados:
    with st.container(border=True):
        st.markdown('<div class="passo">Ranking</div>', unsafe_allow_html=True)
        st.subheader("Ranking das UFs: disposição final inadequada")
        medida = st.radio("Medida", ["Média simples", "Média ponderada por população"], horizontal=True,
                          help="A simples dá o mesmo peso a cada município; a ponderada usa a população.", key="medida_rank")
        coluna_medida = "media_simples" if medida == "Média simples" else "media_ponderada"
        dados_rank = ranking[["uf", coluna_medida]].rename(columns={coluna_medida: "valor"}).sort_values("valor", ascending=False)
        dados_rank["rotulo"] = dados_rank["valor"].map(lambda v: formatar(v, 1, "%"))
        destaque = uf_selecionada if uf_selecionada != TODO_BRASIL else ""
        base_rank = alt.Chart(dados_rank).encode(
            y=alt.Y("uf:N", sort="-x", title=None, axis=alt.Axis(labelOverlap=False, labelPadding=6)),
            x=alt.X("valor:Q", title="% em disposição inadequada", scale=alt.Scale(domain=[0, 100])))
        barras_rank = base_rank.mark_bar().encode(
            color=alt.Color("valor:Q", scale=ESCALA_PIOR, legend=None),
            stroke=alt.condition(alt.datum.uf == destaque, alt.value(COR_TEXTO), alt.value("transparent")),
            strokeWidth=alt.condition(alt.datum.uf == destaque, alt.value(2.5), alt.value(0)),
            tooltip=["uf", alt.Tooltip("rotulo:N", title="valor")])
        textos = base_rank.mark_text(align="left", dx=4, fontSize=11, color=COR_TEXTO).encode(text="rotulo:N")
        st.altair_chart(estilizar((barras_rank + textos).properties(height=27 * 20)))
        st.caption("Do pior para o melhor, com a mesma escala de cor do mapa. A UF selecionada tem contorno escuro. "
                   "As duas medidas podem divergir bastante porque o IRS3002 se concentra em 0% e 100%. "
                   "UFs com 0,0% ou 100% pedem leitura cuidadosa: 0 significa que nenhum município declarou rota para lixão, "
                   "vazadouro ou aterro controlado, e 100%, que toda a massa coletada vai a esses destinos."
                   + (f" Em {suspeitas_txt}, mais de 90% dos municípios registram exatamente 0%." if suspeitas_txt else ""))

    with st.container(border=True):
        st.markdown('<div class="passo">Comparação</div>', unsafe_allow_html=True)
        st.subheader("Comparar estados lado a lado")
        padrao = [u for u in ["SP", "PI", "DF"] if u in ufs_disponiveis]
        escolhidas = st.multiselect("Estados (até 5)", ufs_disponiveis, default=padrao, max_selections=5)
        medida_cmp = st.radio("Medida", ["Média simples", "Média ponderada por população"], horizontal=True, key="medida_cmp")
        chave = "Média" if medida_cmp == "Média simples" else "Média ponderada"
        curtos_cmp = {"IRS0001": "Cobertura da coleta", "IRS0005": "Coleta seletiva", "IRS3001": "Desempenho da coleta seletiva",
                      "IRS3002": "Disposição inadequada", "IRS3010": "Recuperação de recicláveis"}
        linhas_cmp = []
        for nome_grupo, parte in [("Brasil", tabela_brasil)] + [(u, tabela_brasil[tabela_brasil["uf"] == u]) for u in escolhidas]:
            for c in curtos_cmp:
                valor = resumo_indicador(parte[c], parte["populacao_total"])[chave]
                if valor is not None and not pd.isna(valor):
                    linhas_cmp.append({"grupo": nome_grupo, "indicador": curtos_cmp[c], "valor": valor,
                                       "rotulo": formatar(valor, 1, "%")})
        if len(escolhidas) == 0:
            st.info("Escolha ao menos um estado para comparar com o Brasil.")
        else:
            df_cmp = pd.DataFrame(linhas_cmp)
            ordem = ["Brasil"] + escolhidas
            cores = alt.Scale(domain=ordem, range=[COR_NEUTRA] + CORES_GRUPOS[:len(escolhidas)])
            base_cmp = alt.Chart(df_cmp).encode(
                x=alt.X("indicador:N", sort=list(curtos_cmp.values()), title=None,
                        axis=alt.Axis(grid=False, labelAngle=0, labelLimit=0, labelOverlap=False, labelPadding=8,
                                       labelExpr="split(datum.label, ' ')")),
                y=alt.Y("valor:Q", title="%", scale=alt.Scale(domain=[0, 108]),
                        axis=alt.Axis(grid=True, gridColor="#E6E1D4", gridDash=[2, 3], values=[0, 20, 40, 60, 80, 100])),
                xOffset=alt.XOffset("grupo:N", sort=ordem))
            barras_cmp = base_cmp.mark_bar().encode(
                color=alt.Color("grupo:N", scale=cores, sort=ordem, legend=alt.Legend(title=None, orient="top", direction="horizontal")),
                tooltip=["grupo", "indicador", alt.Tooltip("rotulo:N", title="valor")])
            texto_cmp = base_cmp.mark_text(dy=-7, fontSize=10, color=COR_TEXTO).encode(text="rotulo:N")
            st.altair_chart(estilizar((barras_cmp + texto_cmp).properties(height=420)))
            st.caption("Cinza é o Brasil, como referência. Na disposição inadequada, menor é melhor; nos demais indicadores, "
                       "maior é melhor. As cores dos estados só os distinguem.")

# -----------------------------------------------------------------------------
# Municípios
# -----------------------------------------------------------------------------
with aba_municipios:
    with st.container(border=True):
        st.markdown('<div class="passo">Cobertura e destinação</div>', unsafe_allow_html=True)
        st.subheader("Cobertura da coleta e disposição inadequada: como os municípios se distribuem")
        dispersao = tabela.dropna(subset=["IRS0001", "IRS3002"]).copy()
        if len(dispersao) > 10:
            tem_variacao = dispersao["IRS0001"].nunique() > 1 and dispersao["IRS3002"].nunique() > 1
            rho = float(spearmanr(dispersao["IRS0001"], dispersao["IRS3002"])[0]) if tem_variacao else float("nan")
            rotulos_cob = ["até 50%", "50 a 80%", "80 a 95%", "mais de 95%"]
            rotulos_sit = ["0%", "1% a 99%", "100%"]
            dispersao["faixa_cob"] = pd.cut(dispersao["IRS0001"], [-0.01, 50, 80, 95, 100.01], labels=rotulos_cob)
            dispersao["situacao"] = pd.cut(dispersao["IRS3002"], [-0.01, 0, 99.999, 100.01], labels=rotulos_sit)
            cont = dispersao.groupby(["faixa_cob", "situacao"], observed=False).size().reset_index(name="n")
            cont["total"] = cont.groupby("faixa_cob", observed=False)["n"].transform("sum")
            cont = cont[cont["total"] > 0].copy()
            cont["pct"] = cont["n"] / cont["total"] * 100
            cont["ordem"] = cont["situacao"].map({s: i for i, s in enumerate(rotulos_sit)}).astype(int)
            cont["rotulo"] = cont["pct"].map(lambda v: formatar(v, 0, "%") if v >= 3 else "")
            cont["pct_txt"] = cont["pct"].map(lambda v: formatar(v, 1, "%"))
            cont["eixo"] = [f"{f} ({formatar(t, 0)})" for f, t in zip(cont["faixa_cob"], cont["total"])]
            cont["faixa_cob"] = cont["faixa_cob"].astype(str)
            cont["situacao"] = cont["situacao"].astype(str)
            ordem_eixo = [f"{f} ({formatar(cont.loc[cont['faixa_cob'] == f, 'total'].iloc[0], 0)})"
                          for f in rotulos_cob if f in set(cont["faixa_cob"])]
            escala_sit = alt.Scale(domain=rotulos_sit, range=["#E6C7A3", "#D79A68", "#8C2F10"])
            base_c = alt.Chart(cont).encode(
                y=alt.Y("eixo:N", sort=ordem_eixo, title="Cobertura da coleta (municípios)", axis=alt.Axis(labelLimit=260, labelPadding=6, labelOverlap=False)),
                x=alt.X("pct:Q", title="% dos municípios da faixa", scale=alt.Scale(domain=[0, 100])))
            barras_c = base_c.mark_bar().encode(
                color=alt.Color("situacao:N", scale=escala_sit, sort=rotulos_sit,
                                legend=alt.Legend(title="Disposição inadequada", orient="top")),
                order=alt.Order("ordem:Q"),
                tooltip=["eixo", "situacao", alt.Tooltip("n:Q", title="municípios"), alt.Tooltip("pct_txt:N", title="%")])
            textos_c = base_c.mark_text(fontSize=12).encode(
                color=alt.condition(alt.datum.situacao == "100%", alt.value("#FFFFFF"), alt.value(COR_TEXTO)),
                text="rotulo:N", order=alt.Order("ordem:Q"), x=alt.X("pct:Q", stack="zero", bandPosition=0.5))
            st.altair_chart(estilizar((barras_c + textos_c).properties(height=52 * len(ordem_eixo) + 90)))
            frases = []
            p100 = cont[cont["situacao"] == "100%"].set_index("faixa_cob")["pct"]
            if "até 50%" in p100.index and "mais de 95%" in p100.index:
                frases.append(f"Entre os municípios com cobertura de até 50%, {formatar(p100['até 50%'], 0, '%')} destinam 100% de forma inadequada; "
                              f"com cobertura acima de 95%, {formatar(p100['mais de 95%'], 0, '%')}.")
            if not pd.isna(rho):
                frases.append(f"Correlação de Spearman = {formatar(rho, 2)} (associação, não causalidade).")
            st.caption(" ".join(frases) + " Um 0% de disposição inadequada com cobertura baixa é possível: o indicador "
                       "usa a massa efetivamente coletada, e um 0% significa apenas que nenhuma rota declarada vai a lixão ou aterro controlado.")
    with st.container(border=True):
        st.markdown('<div class="passo">Dados por município</div>', unsafe_allow_html=True)
        st.subheader("Tabela de municípios")
        df_municipios_tabela = tabela.drop(columns=["cod_ibge", "regiao"]).rename(
            columns={"nome_municipio": "município", "populacao_total": "população"})
        unidades = {"IRS1004": "kg/hab.dia"}
        config_colunas = {
            "município": st.column_config.TextColumn("Município", pinned=True),
            "uf": st.column_config.TextColumn("UF", width="small"),
            "população": st.column_config.NumberColumn("População", format="localized"),
        }
        for c in INDICADORES:
            config_colunas[c] = st.column_config.NumberColumn(
                CURTOS[c], help=f"{c}: {nomes[c]} ({unidades.get(c, '%')})", format="localized", width="medium")
        st.caption("Passe o mouse sobre o título da coluna para ver o código e a definição do indicador. Clique no título para ordenar.")
        tabela_exibida = df_municipios_tabela.copy()
        tabela_exibida[INDICADORES] = tabela_exibida[INDICADORES].round(2)
        st.dataframe(tabela_exibida, hide_index=True, column_config=config_colunas)
        st.download_button(
            "Baixar tabela (CSV)",
            data=df_municipios_tabela.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"municipios_{'brasil' if uf_selecionada == TODO_BRASIL else uf_selecionada}.csv",
            mime="text/csv",
        )

# -----------------------------------------------------------------------------
# Metodologia e limitações
# -----------------------------------------------------------------------------
with aba_metodo:
    st.markdown(
        "- **Fonte:** Ministério das Cidades, SINISA 2025 (ano de referência 2024), planilha de indicadores de "
        "resíduos sólidos urbanos.\n"
        f"- **Cobertura:** {formatar(int(df_municipios['respondeu'].sum()), 0)} de {formatar(len(df_municipios), 0)} municípios do país "
        f"responderam ao módulo ({formatar(df_municipios['respondeu'].mean() * 100, 1)}%). Os demais ficam fora da análise.\n"
        "- **Média ponderada:** usa a população total do município como peso.\n"
        "- **Valores suspeitos:** percentuais acima de 100 e massa per capita acima de 3 kg/hab.dia são "
        "marcados no ETL e mantidos por padrão; use o filtro lateral para excluí-los.\n"
        "- **Zeros:** no IRS3002, 0% significa que o município não declarou nenhuma rota de coleta para lixão, vazadouro ou "
        "aterro controlado; no Brasil, a grande maioria dos zeros vem de rotas a aterro sanitário ou de inertes (quadro "
        "\"O que significa um 0%?\", na aba Panorama). Nos demais "
        "indicadores, 0 pode indicar ausência do serviço ou do envio da informação. Os dados são autodeclarados.\n"
        "- **Escopo:** os indicadores tratam de resíduos sólidos urbanos municipais, não de resíduos industriais "
        "nem da gestão ambiental de empresas.\n"
        "- **Associação não é causalidade:** os resultados descrevem os dados e não explicam suas causas."
    )
    st.markdown("**Definição dos indicadores**")
    st.dataframe(
        df_catalogo.rename(columns={"codigo": "Código", "nome": "Nome", "unidade": "Unidade", "definicao": "Definição"}),
        hide_index=True,
    )

st.markdown(
    '<hr style="margin-top:3rem;border:none;border-top:1px solid #D6D1C4">'
    '<p style="font-size:0.85rem;color:#6B6F66">Projeto de extensão do 4º semestre, Faculdade de Tecnologia de São Bernardo do Campo '
    '"Adib Moisés Dib". Autores: Gabriel Champin, Gabriel Kenji, Luana Monteiro, Pedro Genaro e Walter Augusto. '
    'Dados: Ministério das Cidades, SINISA 2025 (ano de referência 2024). '
    '<a href="https://github.com/gchamps/analise-residuos-sinisa">Código no GitHub</a>.</p>',
    unsafe_allow_html=True,
)
