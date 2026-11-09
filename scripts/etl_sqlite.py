"""
ETL do SINISA - Resíduos Sólidos Urbanos

Lê a planilha de indicadores municipais do SINISA, trata o cabeçalho dividido
em duas linhas e carrega os dados em um banco SQLite. O esquema do banco está
documentado em sql/01_schema.sql, que é executado por este script.

Fonte: Ministério das Cidades - SINISA 2025 (ano de referência 2024).
Arquivo de entrada: dados_originais/SINISA_RESIDUOS_Indicadores_2024.xlsx

Saídas (pasta dados_tratados/):
    projeto_residuos.db              banco SQLite
    municipios.csv                   dimensão município
    resultados_indicadores_mpv.csv   tabela fato (resultados por município)

Uso, a partir da raiz do projeto:
    python scripts/etl_sqlite.py
"""

import os
import sqlite3
import sys

import pandas as pd

# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_EXCEL = os.path.join(BASE_DIR, "dados_originais", "SINISA_RESIDUOS_Indicadores_2024.xlsx")
CAMINHO_SCHEMA = os.path.join(BASE_DIR, "sql", "01_schema.sql")
CAMINHO_BANCO = os.path.join(BASE_DIR, "dados_tratados", "projeto_residuos.db")
CAMINHO_CSV_MUNICIPIOS = os.path.join(BASE_DIR, "dados_tratados", "municipios.csv")
CAMINHO_CSV_RESULTADOS = os.path.join(BASE_DIR, "dados_tratados", "resultados_indicadores_mpv.csv")

# O nome do arquivo e o título da planilha trazem "2024", que é o ano de
# referência dos dados. A edição é a SINISA 2025 (planilha gerada em 18/12/2025).
ANO_REFERENCIA = 2024

# Posições (base 0) das linhas do cabeçalho na planilha original:
#   linha 11 do Excel: códigos dos indicadores (IRS..., IFR...)
#   linha 13 do Excel: códigos das demais colunas (Cod_IBGE, DFE0001...) e unidades
#   linha 14 do Excel: primeira linha de dados
LINHA_CODIGOS_INDICADORES = 10
LINHA_CODIGOS_DEMAIS = 12
PRIMEIRA_LINHA_DADOS = 13

# Planilha de Manejo: 1ª aba = massas por município; 2ª aba = rotas de coleta com o tipo de unidade de destino.
# O IRS3002 sai das rotas (massa das rotas a lixão ou aterro controlado / massa coletada líquida).
CAMINHO_EXCEL_MANEJO = os.path.join(
    BASE_DIR, "dados_originais", "SINISA_RESIDUOS_Informacoes_Formulario_Manejo_2024.xlsx")
ABA_MANEJO = 0
ABA_ROTAS = "Manejo_Coleta_e_Destinação"
COLUNA_MASSA_ROTA = "GTR1008"           # massa coletada na rota (t/ano)
COLUNA_TIPO_DESTINO = "GTR1011*"        # tipo de unidade de destino da rota
TOLERANCIA_IRS3002_PP = 0.05            # diferença máxima aceita entre o IRS3002 e o recalculado pelas rotas

# Regras de sinalização de qualidade (os valores NÃO são apagados, só marcados)
LIMITE_PERCENTUAL = 100.0          # indicador percentual não deveria passar de 100
LIMITE_MASSA_PER_CAPITA = 3.0      # kg/hab.dia; critério do grupo, ajuste se necessário
FLAG_PERCENTUAL = "PERCENTUAL_ACIMA_100"
FLAG_MASSA = "MASSA_PER_CAPITA_ALTA"

# Catálogo dos indicadores utilizados.
# Nomes, unidades e grupos conforme o Glossário de Indicadores SINISA 2025.
# (codigo, nome, unidade, grupo, definicao)
INDICADORES = [
    ("IRS0001",
     "Cobertura da população total com coleta de resíduos sólidos domiciliares",
     "Percentual", "Cobertura",
     "População total coberta pela coleta indiferenciada (direta ou indireta) / "
     "população total residente x 100 (GTR0201 / DFE0001)."),
    ("IRS0005",
     "Cobertura da população total com coleta seletiva de resíduos sólidos domiciliares",
     "Percentual", "Cobertura",
     "População total coberta pela coleta seletiva (direta e indireta) / "
     "população total residente x 100 (GTR0205 / DFE0001)."),
    ("IRS1004",
     "Massa média per capita de resíduos sólidos urbanos coletados",
     "Kg/hab.dia", "Operacional",
     "Massa anual de resíduos sólidos urbanos coletados / população total residente, "
     "convertida para kg/hab.dia (GTR1028 e DFE0001)."),
    ("IRS3001",
     "Desempenho da coleta seletiva",
     "Percentual", "Qualidade",
     "Massa da coleta seletiva domiciliar / massa total da coleta domiciliar x 100 "
     "(GTR1026 / GTR1025)."),
    ("IRS3002",
     "Disposição final inadequada de resíduos sólidos urbanos",
     "Percentual", "Qualidade",
     "Massa enviada a lixão, vazadouro ou aterro controlado / (massa total coletada - "
     "massa recuperada) x 100 (soma de GTR1008 / (GTR1028 - GTR1029)). "
     "Vale 0% quando nada é enviado a essas unidades."),
    ("IRS3010",
     "Recuperação de resíduos recicláveis secos e orgânicos em relação à quantidade total coletada",
     "Percentual", "Qualidade",
     "Massa recuperada de resíduos domiciliares secos e orgânicos / massa total de "
     "resíduos urbanos coletados x 100 (GTR1029 / GTR1028)."),
]
CODIGOS_INDICADORES = [i[0] for i in INDICADORES]
UNIDADE_POR_INDICADOR = {i[0]: i[2] for i in INDICADORES}


# -----------------------------------------------------------------------------
# Extração
# -----------------------------------------------------------------------------
def ler_planilha(caminho):
    """Lê a planilha e monta o cabeçalho final.

    O cabeçalho do SINISA é dividido: nas colunas de indicadores o código
    (IRS/IFR) está na linha 11 e a unidade na linha 13; nas demais colunas o
    código (Cod_IBGE, DFE0001...) está na linha 13.
    """
    if not os.path.exists(caminho):
        sys.exit(f"Arquivo não encontrado: {caminho}")

    bruto = pd.read_excel(caminho, header=None)
    linha_indicadores = bruto.iloc[LINHA_CODIGOS_INDICADORES].fillna("")
    linha_demais = bruto.iloc[LINHA_CODIGOS_DEMAIS].fillna("")

    colunas = []
    for i in range(bruto.shape[1]):
        codigo = str(linha_indicadores.iloc[i]).strip()
        outro = str(linha_demais.iloc[i]).strip()
        if codigo.startswith(("IRS", "IFR")):
            colunas.append(codigo)
        elif outro != "":
            colunas.append(outro)
        else:
            colunas.append(f"coluna_{i}")

    dados = bruto.iloc[PRIMEIRA_LINHA_DADOS:].copy()
    dados.columns = colunas
    return dados


def ler_rotas_destino(caminho):
    """Lê a aba de rotas da planilha de Manejo: uma linha por rota de coleta declarada pelo município.

    Cada rota tem a massa coletada (GTR1008) e o tipo de unidade de destino (GTR1011). A soma das massas das
    rotas que vão a lixão, vazadouro ou aterro controlado, dividida pela massa coletada líquida, é exatamente
    o IRS3002 (o ETL confere isso em validar_carga).
    """
    if not os.path.exists(caminho):
        sys.exit(f"Arquivo não encontrado: {caminho}")
    bruto = pd.read_excel(caminho, sheet_name=ABA_ROTAS, header=None)
    dados = bruto.iloc[PRIMEIRA_LINHA_DADOS:].copy()
    dados.columns = [str(c).strip() for c in bruto.iloc[LINHA_CODIGOS_DEMAIS].tolist()]
    return dados


def ler_massas_manejo(caminho):
    """Massa coletada (GTR1028) e recuperada (GTR1029) por município, da 1ª aba da planilha de Manejo."""
    if not os.path.exists(caminho):
        sys.exit(f"Arquivo não encontrado: {caminho}")
    bruto = pd.read_excel(caminho, sheet_name=ABA_MANEJO, header=None)
    dados = bruto.iloc[PRIMEIRA_LINHA_DADOS:].copy()
    dados.columns = [str(c).strip() for c in bruto.iloc[LINHA_CODIGOS_DEMAIS].tolist()]
    exigir_colunas(dados, ["Cod_IBGE", "GTR1028", "GTR1029"])
    return dados[["Cod_IBGE", "GTR1028", "GTR1029"]]


TERMOS_INTERMEDIARIOS = ("transbordo", "triagem", "compostagem", "coprocessamento", "áreas verdes", "areas verdes")


def classificar_destino(tipo):
    """Classe do tipo de unidade de destino de uma rota.

    * inadequada: lixão, vazadouro ou aterro controlado (a definição do IRS3002);
    * aterro_adequado: aterro sanitário ou de inertes (destinos finais que o IRS3002 não considera inadequados);
    * intermediaria: transbordo, triagem, compostagem, coprocessamento, manejo de áreas verdes (o destino final
      dos rejeitos não é informado na rota).

    Interrompe o ETL diante de um tipo desconhecido, em vez de classificá-lo em silêncio.
    """
    texto = str(tipo).strip().lower()
    if "lix" in texto or "controlado" in texto:
        return "inadequada"
    if "aterro sanit" in texto or "aterro de inertes" in texto:
        return "aterro_adequado"
    if any(termo in texto for termo in TERMOS_INTERMEDIARIOS):
        return "intermediaria"
    sys.exit(f"Tipo de unidade de destino desconhecido: {tipo!r}. Atualize classificar_destino().")


def preparar_destinacao(rotas, massas, codigos_municipios):
    """Massa das rotas de cada município por classe de destino, mais a massa coletada e a recuperada.

    Todo município da dimensão aparece (zeros quando não há rota declarada). Massas em toneladas por ano,
    como no SINISA. Rotas sem tipo de destino ou sem massa (municípios que não responderam) são ignoradas.
    """
    exigir_colunas(rotas, ["Cod_IBGE", COLUNA_TIPO_DESTINO, COLUNA_MASSA_ROTA])
    base = rotas[rotas[COLUNA_TIPO_DESTINO].notna()].copy()
    base["cod_ibge"] = codigo_ibge_como_texto(base["Cod_IBGE"])
    base["massa"] = pd.to_numeric(base[COLUNA_MASSA_ROTA], errors="coerce")
    descartadas = int(base[["cod_ibge", "massa"]].isna().any(axis=1).sum())
    if descartadas:
        print(f"AVISO: {descartadas} rotas com tipo de destino foram descartadas por falta de código IBGE ou massa numérica.")
    base = base.dropna(subset=["cod_ibge", "massa"])
    base["classe"] = base[COLUNA_TIPO_DESTINO].map(classificar_destino)
    soma = base.pivot_table(index="cod_ibge", columns="classe", values="massa", aggfunc="sum")

    saida = pd.DataFrame({"cod_ibge": list(codigos_municipios)}).set_index("cod_ibge")
    for classe in ("inadequada", "aterro_adequado", "intermediaria"):
        serie = soma[classe] if classe in soma.columns else pd.Series(dtype="float64")
        saida[f"massa_rota_{classe}"] = serie.reindex(saida.index).fillna(0.0)

    massas = massas.assign(cod_ibge=codigo_ibge_como_texto(massas["Cod_IBGE"]),
                           massa_coletada=pd.to_numeric(massas["GTR1028"], errors="coerce"),
                           massa_recuperada=pd.to_numeric(massas["GTR1029"], errors="coerce"))
    massas = massas.dropna(subset=["cod_ibge"]).drop_duplicates("cod_ibge").set_index("cod_ibge")
    saida["massa_coletada"] = massas["massa_coletada"].reindex(saida.index)
    saida["massa_recuperada"] = massas["massa_recuperada"].reindex(saida.index)
    return saida.reset_index()


def exigir_colunas(df, colunas):
    """Interrompe o ETL com mensagem clara se faltar alguma coluna esperada."""
    faltando = [c for c in colunas if c not in df.columns]
    if faltando:
        sys.exit(f"Colunas esperadas não encontradas na planilha: {faltando}")


# -----------------------------------------------------------------------------
# Transformação
# -----------------------------------------------------------------------------
def codigo_ibge_como_texto(serie):
    """Converte o código IBGE para texto de inteiro (ex.: '3548708')."""
    numerico = pd.to_numeric(serie, errors="coerce")
    return numerico.astype("Int64").astype(str).where(numerico.notna())


def preparar_municipios(dados):
    colunas = ["Cod_IBGE", "Nom_Mun", "UF", "Nom_Região", "DFE0001", "Sim/Não"]
    exigir_colunas(dados, colunas)

    municipios = dados[colunas].copy()
    municipios.columns = ["cod_ibge", "nome_municipio", "uf", "regiao", "populacao_total", "respondeu"]

    municipios["cod_ibge"] = codigo_ibge_como_texto(municipios["cod_ibge"])
    municipios = municipios.dropna(subset=["cod_ibge"]).drop_duplicates(subset=["cod_ibge"])

    municipios["populacao_total"] = pd.to_numeric(municipios["populacao_total"], errors="coerce").astype("Int64")
    municipios["respondeu"] = (municipios["respondeu"].astype(str).str.strip().str.lower() == "sim").astype(int)
    return municipios.reset_index(drop=True)


def preparar_resultados(dados):
    exigir_colunas(dados, ["Cod_IBGE"] + CODIGOS_INDICADORES)

    base = dados[["Cod_IBGE"] + CODIGOS_INDICADORES].copy()
    base["cod_ibge"] = codigo_ibge_como_texto(base["Cod_IBGE"])
    base = base.drop(columns=["Cod_IBGE"]).dropna(subset=["cod_ibge"])

    # Formato longo: uma linha por município x indicador.
    # Valores não numéricos (municípios não respondentes, "null") são descartados.
    resultados = base.melt(id_vars=["cod_ibge"], var_name="codigo_indicador", value_name="valor")
    resultados["valor"] = pd.to_numeric(resultados["valor"], errors="coerce")
    resultados = resultados.dropna(subset=["valor"]).copy()
    resultados["ano_referencia"] = ANO_REFERENCIA

    # Sinalização de qualidade (não remove nenhum valor)
    flag = pd.Series([None] * len(resultados), index=resultados.index, dtype="object")
    eh_percentual = resultados["codigo_indicador"].map(UNIDADE_POR_INDICADOR).eq("Percentual")
    flag[eh_percentual & (resultados["valor"] > LIMITE_PERCENTUAL)] = FLAG_PERCENTUAL
    flag[(resultados["codigo_indicador"] == "IRS1004") & (resultados["valor"] > LIMITE_MASSA_PER_CAPITA)] = FLAG_MASSA
    resultados["flag_qualidade"] = flag

    return resultados.reset_index(drop=True)


# -----------------------------------------------------------------------------
# Carga
# -----------------------------------------------------------------------------
def criar_esquema(conn):
    """Executa o script sql/01_schema.sql (recria as tabelas do zero)."""
    if not os.path.exists(CAMINHO_SCHEMA):
        sys.exit(f"Script de esquema não encontrado: {CAMINHO_SCHEMA}")
    with open(CAMINHO_SCHEMA, encoding="utf-8") as arquivo:
        conn.executescript(arquivo.read())
    conn.execute("PRAGMA foreign_keys = ON;")


def carregar(conn, municipios, resultados, destinacao):
    catalogo = pd.DataFrame(INDICADORES, columns=["codigo", "nome", "unidade", "grupo", "definicao"])
    catalogo.to_sql("indicador", conn, if_exists="append", index=False)
    municipios.to_sql("municipio", conn, if_exists="append", index=False)
    resultados.to_sql("resultado_indicador", conn, if_exists="append", index=False)
    destinacao.to_sql("destinacao_municipio", conn, if_exists="append", index=False)
    conn.commit()


def exportar_csvs(conn):
    """Gera os CSVs a partir do próprio banco (garante que são idênticos a ele)."""
    municipios = pd.read_sql_query("SELECT * FROM municipio ORDER BY cod_ibge", conn)
    resultados = pd.read_sql_query(
        "SELECT cod_ibge, codigo_indicador, valor, ano_referencia, flag_qualidade "
        "FROM resultado_indicador ORDER BY codigo_indicador, cod_ibge",
        conn,
    )
    # utf-8-sig para o Excel abrir os acentos corretamente
    municipios.to_csv(CAMINHO_CSV_MUNICIPIOS, index=False, encoding="utf-8-sig")
    resultados.to_csv(CAMINHO_CSV_RESULTADOS, index=False, encoding="utf-8-sig")
    return len(municipios), len(resultados)


# -----------------------------------------------------------------------------
# Validação
# -----------------------------------------------------------------------------
def validar_carga(conn):
    """Confere a consistência da carga e devolve a lista de problemas."""
    def escalar(sql):
        return conn.execute(sql).fetchone()[0]

    problemas = []
    n_municipios = escalar("SELECT COUNT(*) FROM municipio")
    n_respondentes = escalar("SELECT COUNT(*) FROM municipio WHERE respondeu = 1")
    n_resultados = escalar("SELECT COUNT(*) FROM resultado_indicador")

    print(f"Municípios carregados:       {n_municipios}")
    print(f"  respondentes:              {n_respondentes}")
    print(f"  não respondentes:          {n_municipios - n_respondentes}")
    print(f"Resultados carregados:       {n_resultados}")

    sem_resposta = escalar(
        "SELECT COUNT(*) FROM resultado_indicador r JOIN municipio m ON m.cod_ibge = r.cod_ibge "
        "WHERE m.respondeu = 0"
    )
    if sem_resposta:
        problemas.append(f"{sem_resposta} resultados pertencem a municípios que não responderam.")

    sem_nenhum_resultado = escalar(
        "SELECT COUNT(*) FROM municipio m WHERE m.respondeu = 1 AND NOT EXISTS "
        "(SELECT 1 FROM resultado_indicador r WHERE r.cod_ibge = m.cod_ibge)"
    )
    if sem_nenhum_resultado:
        problemas.append(f"{sem_nenhum_resultado} municípios respondentes não têm nenhum resultado.")

    print("Municípios com valor, por indicador:")
    for codigo in CODIGOS_INDICADORES:
        n = escalar(
            f"SELECT COUNT(DISTINCT cod_ibge) FROM resultado_indicador WHERE codigo_indicador = '{codigo}'"
        )
        print(f"  {codigo}: {n}")
        if n != n_respondentes:
            problemas.append(f"{codigo} tem {n} municípios com valor, mas há {n_respondentes} respondentes.")

    sinalizados = conn.execute(
        "SELECT codigo_indicador, flag_qualidade, COUNT(*) FROM resultado_indicador "
        "WHERE flag_qualidade IS NOT NULL GROUP BY 1, 2 ORDER BY 1"
    ).fetchall()
    print("Valores sinalizados (mantidos no banco):")
    if sinalizados:
        for codigo, flag, n in sinalizados:
            print(f"  {codigo} - {flag}: {n}")
    else:
        print("  nenhum")

    n_destinacao = escalar("SELECT COUNT(*) FROM destinacao_municipio")
    if n_destinacao != n_municipios:
        problemas.append(f"destinacao_municipio tem {n_destinacao} linhas, mas há {n_municipios} municípios.")
    # O IRS3002 deve ser reproduzido pelas rotas: massa a lixão/aterro controlado / (coletada - recuperada) x 100
    n_conferidos, maior_diferenca, divergentes = conn.execute(
        "SELECT COUNT(*), MAX(ABS(r.valor - 100.0 * d.massa_rota_inadequada / (d.massa_coletada - COALESCE(d.massa_recuperada, 0)))), "
        "SUM(ABS(r.valor - 100.0 * d.massa_rota_inadequada / (d.massa_coletada - COALESCE(d.massa_recuperada, 0))) > ?) "
        "FROM resultado_indicador r JOIN destinacao_municipio d USING (cod_ibge) "
        "WHERE r.codigo_indicador = 'IRS3002' AND d.massa_coletada - COALESCE(d.massa_recuperada, 0) > 0",
        (TOLERANCIA_IRS3002_PP,)).fetchone()
    print(f"IRS3002 recalculado pelas rotas de coleta: {n_conferidos} municípios conferidos, "
          f"maior diferença {maior_diferenca:.4f} p.p.")
    if divergentes:
        problemas.append(f"{divergentes} municípios têm IRS3002 diferente do recalculado pelas rotas "
                         f"(tolerância {TOLERANCIA_IRS3002_PP} p.p.).")
    zeros = conn.execute(
        "SELECT COUNT(*), SUM(d.massa_rota_inadequada > 0) "
        "FROM resultado_indicador r JOIN destinacao_municipio d USING (cod_ibge) "
        "WHERE r.codigo_indicador = 'IRS3002' AND r.valor = 0"
    ).fetchone()
    print(f"IRS3002 = 0: {zeros[0]} municípios; com rota declarada a lixão/aterro controlado: {zeros[1]}")
    if zeros[1]:
        problemas.append(f"{zeros[1]} municípios com IRS3002 = 0 declaram rota a lixão ou aterro controlado.")

    violacoes_fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violacoes_fk:
        problemas.append(f"{len(violacoes_fk)} violações de chave estrangeira.")

    return problemas


# -----------------------------------------------------------------------------
# Execução
# -----------------------------------------------------------------------------
def executar_etl():
    print(f"Lendo a planilha do SINISA (ano de referência {ANO_REFERENCIA})...")
    dados = ler_planilha(CAMINHO_EXCEL)

    municipios = preparar_municipios(dados)
    resultados = preparar_resultados(dados)
    print("Lendo rotas de coleta e destino e massas coletadas (planilha de Manejo)...")
    destinacao = preparar_destinacao(ler_rotas_destino(CAMINHO_EXCEL_MANEJO),
                                     ler_massas_manejo(CAMINHO_EXCEL_MANEJO), municipios["cod_ibge"])

    os.makedirs(os.path.dirname(CAMINHO_BANCO), exist_ok=True)
    conn = sqlite3.connect(CAMINHO_BANCO)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        criar_esquema(conn)
        carregar(conn, municipios, resultados, destinacao)
        print("Carga concluída. Validando...")
        problemas = validar_carga(conn)
        n_mun, n_res = exportar_csvs(conn)
        print(f"CSVs gerados: municipios.csv ({n_mun} linhas) e resultados_indicadores_mpv.csv ({n_res} linhas).")
    finally:
        conn.close()

    if problemas:
        print("\nPROBLEMAS ENCONTRADOS:")
        for problema in problemas:
            print(f"  - {problema}")
        sys.exit(1)

    print("ETL finalizado sem problemas.")


if __name__ == "__main__":
    executar_etl()