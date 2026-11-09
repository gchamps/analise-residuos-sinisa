"""
Análise estatística dos indicadores de resíduos sólidos urbanos.

Fonte: Ministério das Cidades - SINISA 2025 (ano de referência 2024).
Pré-requisito: banco gerado por scripts/etl_sqlite.py.

O módulo oferece funções reutilizadas por scripts/gerar_planilha.py e, quando
executado diretamente, imprime um resumo da análise no console:

    python scripts/analise_estatistica.py

Dependências: pandas, numpy, scipy.

Convenções:
  * Só entram municípios que responderam ao módulo de resíduos.
  * "Média ponderada" usa a população total do município como peso.
  * Os valores sinalizados no ETL (coluna flag_qualidade) são mantidos.
"""

import os
import sqlite3

import numpy as np
import pandas as pd
from scipy import stats

from calculos import (CONSULTA_RESULTADOS, INDICADORES, media_ponderada, montar_tabela, ranking_uf,  # noqa: F401
                      resumo_regioes)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_BANCO = os.path.join(BASE_DIR, "dados_tratados", "projeto_residuos.db")

UF_RECORTE = "SP"


# -----------------------------------------------------------------------------
# Carga dos dados
# -----------------------------------------------------------------------------
def carregar_dados(conn, excluir_sinalizados=False):
    """Devolve uma linha por município respondente e uma coluna por indicador.

    Com `excluir_sinalizados=True` os valores marcados no ETL ficam de fora (mesma regra do app).
    """
    return montar_tabela(pd.read_sql_query(CONSULTA_RESULTADOS, conn), excluir_sinalizados)


def carregar_catalogo(conn):
    return pd.read_sql_query("SELECT codigo, nome, unidade FROM indicador ORDER BY codigo", conn)


def carregar_totais_por_uf(conn):
    """Total de municípios por UF no SINISA e quantos responderam."""
    return pd.read_sql_query(
        "SELECT uf, COUNT(*) AS municipios_total, SUM(respondeu) AS respondentes "
        "FROM municipio GROUP BY uf",
        conn,
    )


# -----------------------------------------------------------------------------
# Estatística descritiva
# -----------------------------------------------------------------------------
def estatistica_descritiva(df):
    linhas = []
    for codigo in INDICADORES:
        s = df[codigo]
        linhas.append({
            "indicador": codigo,
            "n": int(s.count()),
            "media": s.mean(),
            "mediana": s.median(),
            "desvio_padrao": s.std(ddof=1),
            "minimo": s.min(),
            "q1": s.quantile(0.25),
            "q3": s.quantile(0.75),
            "maximo": s.max(),
            "pct_zero": (s == 0).mean() * 100,
            "pct_cem": (s == 100).mean() * 100,
            "media_ponderada": media_ponderada(s, df["populacao_total"]),
        })
    return pd.DataFrame(linhas)


# -----------------------------------------------------------------------------
# Rankings por UF e por região (IRS3002 - disposição final inadequada)
# -----------------------------------------------------------------------------
# ranking_uf e resumo_regioes vêm de calculos.py (importados no topo): mesma regra do dashboard.


# -----------------------------------------------------------------------------
# Associações e testes
# -----------------------------------------------------------------------------
def matriz_correlacao(df, metodo="pearson"):
    return df[INDICADORES].corr(method=metodo)


def regressao_simples(df, y, x):
    r = stats.linregress(df[x], df[y])
    return {
        "y": y, "x": x, "n": len(df),
        "inclinacao": r.slope, "intercepto": r.intercept,
        "r2": r.rvalue ** 2, "p_valor": r.pvalue,
    }


def probabilidades_condicionais(df):
    """Probabilidade empírica de não haver recuperação (IRS3010 = 0)."""
    sem_coleta = df[df["IRS0005"] == 0]
    com_coleta = df[df["IRS0005"] > 0]
    return {
        "p_rec_zero": (df["IRS3010"] == 0).mean(),
        "p_rec_zero_dado_sem_coleta": (sem_coleta["IRS3010"] == 0).mean(),
        "p_rec_zero_dado_com_coleta": (com_coleta["IRS3010"] == 0).mean(),
        "n_sem_coleta": len(sem_coleta),
        "n_com_coleta": len(com_coleta),
    }


def comparar_uf_com_demais(df, uf=UF_RECORTE, indicador="IRS3002"):
    """Teste de Mann-Whitney: municípios da UF x municípios das demais UFs.

    O teste não supõe distribuição normal, adequado a indicadores concentrados
    em 0 e 100. A probabilidade de superioridade é a chance de um município da
    UF ter valor menor que o de um município sorteado entre os demais
    (empates contam metade).
    """
    grupo = df.loc[df["uf"] == uf, indicador]
    demais = df.loc[df["uf"] != uf, indicador]
    teste = stats.mannwhitneyu(grupo, demais, alternative="two-sided")
    return {
        "uf": uf, "indicador": indicador,
        "n_uf": len(grupo), "n_demais": len(demais),
        "media_uf": grupo.mean(), "media_demais": demais.mean(),
        "mediana_uf": grupo.median(), "mediana_demais": demais.median(),
        "u": float(teste.statistic), "p_valor": float(teste.pvalue),
        "prob_uf_menor": 1 - float(teste.statistic) / (len(grupo) * len(demais)),
    }


# -----------------------------------------------------------------------------
# Execução no console
# -----------------------------------------------------------------------------
def titulo(texto):
    print("\n" + "=" * 70)
    print(texto)
    print("=" * 70)


def executar():
    conn = sqlite3.connect(CAMINHO_BANCO)
    try:
        df = carregar_dados(conn)
        totais = carregar_totais_por_uf(conn)
    finally:
        conn.close()

    n_total = int(totais["municipios_total"].sum())
    n_resp = len(df)
    print(f"Municípios respondentes: {n_resp} de {n_total} ({n_resp / n_total * 100:.1f}%)")

    titulo("1. ESTATÍSTICA DESCRITIVA (média simples e ponderada por população)")
    print(estatistica_descritiva(df).round(2).to_string(index=False))

    ranking = ranking_uf(df)
    titulo("2. RANKING DE UFs - DISPOSIÇÃO FINAL INADEQUADA (IRS3002; 1 = pior)")
    print(ranking.round(2).to_string(index=False))
    linha = ranking[ranking["uf"] == UF_RECORTE].iloc[0]
    print(f"\nRecorte {UF_RECORTE}: {int(linha['posicao_simples'])}º de {len(ranking)} pela média simples "
          f"({linha['media_simples']:.2f}%) e {int(linha['posicao_ponderada'])}º pela média ponderada "
          f"({linha['media_ponderada']:.2f}%).")

    titulo("3. REGIÕES - IRS3002")
    print(resumo_regioes(df).round(3).to_string(index=False))

    titulo("4. CORRELAÇÃO (Pearson e Spearman)")
    print("Pearson:\n", matriz_correlacao(df).round(2))
    print("\nSpearman:\n", matriz_correlacao(df, "spearman").round(2))

    titulo("5. REGRESSÃO LINEAR SIMPLES")
    for y, x in [("IRS3010", "IRS0005"), ("IRS3001", "IRS0005")]:
        r = regressao_simples(df, y, x)
        print(f"{y} = {r['intercepto']:.3f} + {r['inclinacao']:.4f} x {x}   "
              f"R2 = {r['r2']:.3f}   p = {r['p_valor']:.2e}   n = {r['n']}")

    titulo("6. PROBABILIDADES EMPÍRICAS CONDICIONAIS")
    p = probabilidades_condicionais(df)
    print(f"P(IRS3010 = 0)                        = {p['p_rec_zero']:.1%}")
    print(f"P(IRS3010 = 0 | IRS0005 = 0)          = {p['p_rec_zero_dado_sem_coleta']:.1%}  (n = {p['n_sem_coleta']})")
    print(f"P(IRS3010 = 0 | IRS0005 > 0)          = {p['p_rec_zero_dado_com_coleta']:.1%}  (n = {p['n_com_coleta']})")

    titulo(f"7. TESTE DE MANN-WHITNEY: {UF_RECORTE} x DEMAIS UFs (IRS3002)")
    t = comparar_uf_com_demais(df)
    print(f"Média {t['uf']}: {t['media_uf']:.2f}% | demais: {t['media_demais']:.2f}%")
    print(f"Mediana {t['uf']}: {t['mediana_uf']:.2f}% | demais: {t['mediana_demais']:.2f}%")
    print(f"U = {t['u']:.1f}   p-valor = {t['p_valor']:.2e}")
    print(f"Probabilidade de um município de {t['uf']} ter valor menor que o de um município das demais UFs: "
          f"{t['prob_uf_menor']:.1%}")

    print("\nObservação: correlação, regressão e probabilidade condicional indicam associação, "
          "não causalidade. O IRS3002 mede resíduos sólidos urbanos municipais.")


if __name__ == "__main__":
    executar()