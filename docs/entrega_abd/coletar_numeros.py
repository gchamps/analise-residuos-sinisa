"""Coleta, direto do PostgreSQL e do SQLite, todos os números citados no artigo.
Saída: numeros.json (o artigo é gerado a partir dele; nada é digitado à mão)."""
import json, sqlite3, sys, os
import psycopg2
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "numeros.json")
pg = psycopg2.connect(host="localhost", port=5433, user="postgres", dbname="residuos_sinisa")
cur = pg.cursor()
def q(sql, *a):
    cur.execute(sql, a or None); return cur.fetchall()
def one(sql): return q(sql)[0][0]
N = {}
N["staging"] = one("select count(*) from staging.stg_planilha")
N["municipios"] = one("select count(*) from sinisa.municipio")
N["respondentes"] = one("select count(*) from sinisa.municipio where respondeu")
N["nao_respondentes"] = N["municipios"] - N["respondentes"]
N["fato"] = one("select count(*) from sinisa.resultado_indicador")
N["pop_total"] = one("select sum(populacao_total) from sinisa.municipio")
N["pop_resp"] = one("select sum(populacao_total) from sinisa.municipio where respondeu")
N["indicadores"] = one("select count(*) from sinisa.indicador")
N["n_por_indicador"] = dict(q("select codigo_indicador, count(*) from sinisa.resultado_indicador group by 1 order by 1"))
N["flags"] = [list(r) for r in q("select codigo_indicador, flag_qualidade, count(*) from sinisa.resultado_indicador where flag_qualidade is not null group by 1,2 order by 1")]
N["flags_total"] = one("select count(*) from sinisa.resultado_indicador where flag_qualidade is not null")
N["irs3002_faixas"] = [list(r) for r in q("""select case when valor=0 then '0%' when valor>=100 then '100%' else '1% a 99%' end s, count(*)
   from sinisa.resultado_indicador where codigo_indicador='IRS3002' group by 1 order by 1""")]
N["media_simples_ponderada"] = [[a, float(b), float(c)] for a,b,c in q("""select r.codigo_indicador, round(avg(r.valor)::numeric,2),
   round((sum(r.valor*m.populacao_total)/sum(m.populacao_total))::numeric,2)
   from sinisa.resultado_indicador r join sinisa.municipio m on m.cod_ibge=r.cod_ibge group by 1 order by 1""")]
N["regiao"] = [[a,b,float(c),float(d)] for a,b,c,d in q("select regiao, municipios_respondentes, disposicao_inadequada_media, coleta_seletiva_media from sinisa.vw_resumo_regiao order by 3 desc")]
N["uf_sp"] = [float(x) for x in q("select media_simples, media_ponderada from sinisa.vw_resumo_uf where uf='SP'")[0]]
N["uf_rank_top5"] = [[a,float(b),float(c)] for a,b,c in q("select uf, media_simples, media_ponderada from sinisa.vw_resumo_uf order by media_simples desc limit 5")]
N["uf_rank_bottom2"] = [[a,float(b)] for a,b in q("select uf, media_simples from sinisa.vw_resumo_uf order by media_simples asc, uf limit 2")]
N["n_ufs"] = one("select count(*) from sinisa.vw_resumo_uf")
N["uf_sp_posicao"] = one("select posicao from (select uf, rank() over (order by media_simples desc) posicao from sinisa.vw_resumo_uf) t where uf='SP'")
N["tamanho_banco"] = one("select pg_size_pretty(pg_database_size('residuos_sinisa'))")
N["indices"] = [r[0] for r in q("select indexname from pg_indexes where schemaname='sinisa' order by 1")]
N["restricoes"] = {t: dict(q("select contype::text, count(*) from pg_constraint c join pg_class k on k.oid=c.conrelid join pg_namespace n on n.oid=k.relnamespace where n.nspname='sinisa' and k.relname=%s group by 1", t)) for t in ("municipio","indicador","resultado_indicador")}
N["views"] = [r[0] for r in q("select viewname from pg_views where schemaname='sinisa' order by 1")]
N["versao_pg"] = one("show server_version")
N["staging_cod_com_decimal"] = one("select count(*) from staging.stg_planilha where cod_ibge like '%.%'")
N["staging_nao_numericos_respondentes"] = one(r"""select count(*) from staging.stg_planilha where respondeu='Sim' and (
   irs0001 !~ '^[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' or irs0001 is null or irs0005 !~ '^[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' or irs0005 is null
   or irs1004 !~ '^[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' or irs1004 is null or irs3001 !~ '^[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' or irs3001 is null
   or irs3002 !~ '^[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' or irs3002 is null or irs3010 !~ '^[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$' or irs3010 is null)""")
N["pares_possiveis"] = N["municipios"] * N["indicadores"]
N["indices_tamanho"] = [list(r) for r in q("select indexname, pg_relation_size(('sinisa.'||indexname)::regclass)/1024 from pg_indexes where schemaname='sinisa' order by 1")]
# --- comparação linha a linha com o SQLite do dashboard
lite = sqlite3.connect(os.path.join(RAIZ, "dados_tratados", "projeto_residuos.db"))
def lt(sql): return lite.execute(sql).fetchall()
cmp = {}
pm = {r[0]: r[1:] for r in q("select cod_ibge, nome_municipio, uf, regiao, populacao_total, respondeu from sinisa.municipio")}
cols = [c[1] for c in lt("pragma table_info(municipio)")]
cmp["municipio_colunas_sqlite"] = cols
sm = {str(r[0]): r for r in lt("select * from municipio")}
cmp["municipios_sqlite"] = len(sm)
cmp["municipios_so_em_um"] = len(set(pm) ^ set(sm))
cmp["municipios_campos_diferentes"] = sum(1 for k in set(pm) & set(sm) if (pm[k][0], pm[k][1], pm[k][2], pm[k][3], bool(pm[k][4])) != (sm[k][1], sm[k][2], sm[k][3], sm[k][4], bool(sm[k][5])))
pr = {(r[0], r[1], r[2]): (r[3], r[4]) for r in q("select cod_ibge, codigo_indicador, ano_referencia, valor, flag_qualidade from sinisa.resultado_indicador")}
cols_r = [c[1] for c in lt("pragma table_info(resultado_indicador)")]
cmp["resultado_colunas_sqlite"] = cols_r
sr = {}
for r in lt("select cod_ibge, codigo_indicador, ano_referencia, valor, flag_qualidade from resultado_indicador"):
    sr[(str(r[0]), r[1], r[2])] = (r[3], r[4])
cmp["resultados_sqlite"] = len(sr)
cmp["resultados_so_em_um"] = len(set(pr) ^ set(sr))
comuns = set(pr) & set(sr)
cmp["valores_diferentes"] = sum(1 for k in comuns if abs(pr[k][0]-sr[k][0]) > 1e-9)
cmp["flags_diferentes"] = sum(1 for k in comuns if (pr[k][1] or None) != (sr[k][1] or None))
cmp["maior_diferenca_absoluta"] = max((abs(pr[k][0]-sr[k][0]) for k in comuns), default=None)
cmp["flags_sqlite"] = sum(1 for v in sr.values() if v[1])
N["comparacao_sqlite"] = cmp

# --- conferência INDEPENDENTE contra a planilha original (leitura direta com openpyxl, sem usar o ETL do projeto)
import openpyxl
wb = openpyxl.load_workbook(os.path.join(RAIZ, "dados_originais", "SINISA_RESIDUOS_Indicadores_2024.xlsx"), read_only=True, data_only=True)
linhas = list(wb.active.iter_rows(values_only=True))
codigos = ["IRS0001", "IRS0005", "IRS1004", "IRS3001", "IRS3002", "IRS3010"]
pos = {str(c).strip(): j for j, c in enumerate(linhas[10]) if c and str(c).strip() in codigos}   # códigos dos indicadores: linha 11
assert linhas[12][1].strip() == "Cod_IBGE" and linhas[12][9].strip() == "DFE0001"                 # demais códigos: linha 13
dados = [r for r in linhas[13:] if r[1] not in (None, "")]
bruto, nao_num, campos_dif = {}, 0, 0
pop_resp = 0
for r in dados:
    cod = str(r[1]).strip().split(".")[0]
    resp = str(r[0]).strip() == "Sim"
    m = pm.get(cod)
    if m is None or (m[0], m[1], m[2], int(m[3] or 0), bool(m[4])) != (str(r[2]).strip(), str(r[3]).strip().upper(), str(r[4]).strip(), int(float(r[9] or 0)), resp):
        campos_dif += 1
    if resp:
        pop_resp += float(r[9] or 0)
        for c in codigos:
            try:
                bruto[(cod, c)] = float(r[pos[c]])
            except (TypeError, ValueError):
                nao_num += 1
prp = {(a, b): v[0] for (a, b, _ano), v in pr.items()}   # (município, indicador) -> valor no PostgreSQL
pl = {}
pl["linhas_planilha"] = len(dados)
pl["respondentes_planilha"] = sum(1 for r in dados if str(r[0]).strip() == "Sim")
pl["valores_nao_numericos_respondentes"] = nao_num
pl["codigos_com_decimal_planilha"] = sum(1 for r in dados if "." in str(r[1]))
pl["codigos_nao_7_digitos_planilha"] = sum(1 for r in dados if not (str(r[1]).strip().isdigit() and len(str(r[1]).strip()) == 7))
pl["municipios_campos_diferentes"] = campos_dif
pl["resultados_planilha"] = len(bruto)
pl["resultados_so_em_um"] = len(set(bruto) ^ set(prp))
pl["valores_diferentes"] = sum(1 for k in set(bruto) & set(prp) if abs(bruto[k] - prp[k]) > 1e-9)
pl["maior_diferenca_absoluta"] = max((abs(bruto[k] - prp[k]) for k in set(bruto) & set(prp)), default=None)
pl["pop_resp_planilha"] = int(pop_resp)
pl["flags_acima_100_irs3001"] = sum(1 for k, v in bruto.items() if k[1] == "IRS3001" and v > 100)
pl["flags_irs1004_acima_3"] = sum(1 for k, v in bruto.items() if k[1] == "IRS1004" and v > 3)
N["comparacao_planilha"] = pl
json.dump(N, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(N, ensure_ascii=False, indent=1, default=str))
