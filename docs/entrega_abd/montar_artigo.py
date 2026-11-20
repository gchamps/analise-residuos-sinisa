"""Monta o artigo de Administração de Banco de Dados (HTML) no padrão visual da FATEC usado no artigo de Estatística.

Todos os números do texto vêm de numeros.json (coletar_numeros.py) e das saídas reais dos comandos
(ev/*.txt); nada é digitado à mão. As figuras são as imagens de renderizar_prints.py e as capturas do painel.

Uso: python docs/entrega_abd/montar_artigo.py <pasta_de_trabalho> <saida.html>
  <pasta_de_trabalho> contém numeros.json, ev/*.txt, png/*.png e dash_*_crop.png
O cabeçalho (logos) e o número de página são aplicados na impressão: imprimir_pdf.py.
"""
import base64
import html
import json
import pathlib
import re
import sys

from PIL import Image

RAIZ = pathlib.Path(__file__).resolve().parents[2]
W = pathlib.Path(sys.argv[1])
SAIDA = pathlib.Path(sys.argv[2])
N = json.loads((W / "numeros.json").read_text(encoding="utf-8"))
EV = {p.stem: p.read_text(encoding="utf-8") for p in (W / "ev").glob("*.txt")}
IMG = W / "png"
LARGURA_UTIL_CM = 15.0      # A4 com margens laterais de 3 cm


def br(x, casas=0):
    """Número no formato brasileiro (milhar com ponto, decimal com vírgula)."""
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def e(t):
    return html.escape(str(t))


def b64(caminho):
    return base64.b64encode(pathlib.Path(caminho).read_bytes()).decode()


# ------------------------------------------------------------------ numeração (fixa, conferida no fim)
ORDEM_FIG = ["fluxo", "er", "estrutura", "fato", "carga", "validacao", "integridade", "views", "explain",
             "seguranca", "armazenamento", "backup", "pan", "est", "mun"]
ORDEM_TAB = ["media", "regiao", "faixa"]
ORDEM_QUA = ["ind", "restr", "cmp"]
F = {k: i for i, k in enumerate(ORDEM_FIG, 1)}
T = {k: i for i, k in enumerate(ORDEM_TAB, 1)}
Q = {k: i for i, k in enumerate(ORDEM_QUA, 1)}
CRIADAS = {"fig": [], "tab": [], "qua": []}


def legenda(rotulo, chave, titulo):
    numero = {"Figura": F, "Tabela": T, "Quadro": Q}[rotulo][chave]
    return f'<div class="leg"><b>{rotulo} {numero}</b> – {titulo}</div>'


def figura(chave, arquivo, titulo, fonte, largura_cm=None, fonte_max_pt=8.5):
    """Imagem de terminal: largura escolhida para a letra sair entre ~7 e 9 pt no papel."""
    CRIADAS["fig"].append(chave)
    w_px = Image.open(arquivo).width / 2          # as imagens são geradas com escala 2
    if largura_cm is None:
        largura_cm = min(LARGURA_UTIL_CM, w_px * (fonte_max_pt / 10.5) * 0.75 * 2.54 / 72)   # 14 px = 10,5 pt
    return (f'<figure>{legenda("Figura", chave, titulo)}'
            f'<img src="data:image/png;base64,{b64(arquivo)}" style="width:{largura_cm:.2f}cm" alt="Figura {F[chave]}">'
            f'<div class="fonte">Fonte: {fonte}</div></figure>')


def figura_svg(chave, svg, titulo, fonte):
    CRIADAS["fig"].append(chave)
    return f'<figure>{legenda("Figura", chave, titulo)}{svg}<div class="fonte">Fonte: {fonte}</div></figure>'


def _tabela(rotulo, chave, titulo, cab, linhas, fonte, nota, alinhar):
    CRIADAS["tab" if rotulo == "Tabela" else "qua"].append(chave)
    alinhar = alinhar or "l" * len(cab)
    cls = {"l": "", "r": ' class="d"', "c": ' class="c"'}
    th = "".join(f"<th{cls[a]}>{c}</th>" for c, a in zip(cab, alinhar))
    tr = ""
    for l in linhas:
        if len(l) == 1:       # linha de subtítulo que ocupa a tabela inteira
            tr += f'<tr class="sub"><td colspan="{len(cab)}">{l[0]}</td></tr>'
        else:
            tr += "<tr>" + "".join(f"<td{cls[a]}>{c}</td>" for c, a in zip(l, alinhar)) + "</tr>"
    nt = f'<div class="nota">Nota: {nota}</div>' if nota else ""
    return (f'<figure class="tab">{legenda(rotulo, chave, titulo)}'
            f'<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>{nt}'
            f'<div class="fonte">Fonte: {fonte}</div></figure>')


def tabela(chave, titulo, cab, linhas, fonte, nota=None, alinhar=None):
    return _tabela("Tabela", chave, titulo, cab, linhas, fonte, nota, alinhar)


def quadro(chave, titulo, cab, linhas, fonte, nota=None, alinhar=None):
    return _tabela("Quadro", chave, titulo, cab, linhas, fonte, nota, alinhar)


# ------------------------------------------------------------------ números derivados (tudo conferido por cálculo)
n_mun, n_resp, n_nresp = N["municipios"], N["respondentes"], N["nao_respondentes"]
n_fato, n_stg, n_ind = N["fato"], N["staging"], N["indicadores"]
assert n_mun == n_stg == 5570 and n_resp + n_nresp == n_mun
assert n_fato == n_resp * n_ind == sum(N["n_por_indicador"].values())
pares, ausentes = N["pares_possiveis"], N["pares_possiveis"] - n_fato
assert pares == n_mun * n_ind and ausentes == n_nresp * n_ind
pct_resp = 100 * n_resp / n_mun
pct_pop = 100 * N["pop_resp"] / N["pop_total"]
cmpq = N["comparacao_sqlite"]
cpl = N["comparacao_planilha"]
assert cmpq["municipios_so_em_um"] == cmpq["resultados_so_em_um"] == cmpq["valores_diferentes"] == 0
assert cmpq["flags_diferentes"] == cmpq["municipios_campos_diferentes"] == 0
assert cpl["resultados_so_em_um"] == cpl["valores_diferentes"] == cpl["municipios_campos_diferentes"] == 0
assert cpl["resultados_planilha"] == n_fato and cpl["respondentes_planilha"] == n_resp and cpl["pop_resp_planilha"] == N["pop_resp"]
assert cpl["codigos_com_decimal_planilha"] == cpl["codigos_nao_7_digitos_planilha"] == cpl["valores_nao_numericos_respondentes"] == 0
flags = {(a, b): c for a, b, c in N["flags"]}
f1004, f3001 = flags[("IRS1004", "MASSA_PER_CAPITA_ALTA")], flags[("IRS3001", "PERCENTUAL_ACIMA_100")]
assert f1004 + f3001 == N["flags_total"] == cmpq["flags_sqlite"]
assert (cpl["flags_acima_100_irs3001"], cpl["flags_irs1004_acima_3"]) == (f3001, f1004)
faixas = dict(N["irs3002_faixas"])
assert sum(faixas.values()) == n_resp
msp = {c: (a, b) for c, a, b in N["media_simples_ponderada"]}
reg = N["regiao"]
sp_s, sp_p = N["uf_sp"]
rst = N["restricoes"]
n_check = sum(rst[t].get("c", 0) for t in rst)

tempos = re.findall(r"Execution Time: ([0-9.]+) ms", EV["08_explain"])
t_idx, t_seq = float(tempos[0]), float(tempos[1])
paginas_heap = re.search(r"Heap Blocks: exact=(\d+)", EV["08_explain"]).group(1)
tam = re.search(r"\n\s*(\d+ \w+)\s*\|\s*(\d+ \w+)\s*\|\s*(\d+ \w+)\s*\|\s*(\d+ \w+)\s*\n", EV["10_armazenamento"])
t_banco, t_fato, t_ind, t_stg = tam.groups()
assert "29125" in EV["06_integridade"] and EV["06_integridade"].count("ERROR:") == 3 and "29124" in EV["06_integridade"]
assert "ERROR" in EV["09_seguranca"] and "permission denied" in EV["09_seguranca"]
assert "29124" in EV["11_backup_restore"] and "5570" in EV["11_backup_restore"]
assert EV["05_validacao"].count("|         0") == 4
bytes_dump = re.search(r"([\d.]+) bytes", EV["11_backup_restore"]).group(1)

# ------------------------------------------------------------------ diagramas (paleta do painel)
VERDE, VERDE_CL, AREIA, AREIA_BD, TEXTO = "#1f5f4a", "#e4efe9", "#f4efe6", "#b9ae98", "#23262b"
SVG_FLUXO = f"""
<svg viewBox="0 0 640 190" xmlns="http://www.w3.org/2000/svg" font-family="Arial, sans-serif" fill="{TEXTO}">
 <defs><marker id="a" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#555"/></marker></defs>
 <g stroke-width="1.2">
  <rect x="0"   y="8" width="116" height="62" rx="7" fill="{AREIA}" stroke="{AREIA_BD}"/>
  <rect x="131" y="8" width="116" height="62" rx="7" fill="{AREIA}" stroke="{AREIA_BD}"/>
  <rect x="262" y="8" width="116" height="62" rx="7" fill="{AREIA}" stroke="{AREIA_BD}"/>
  <rect x="393" y="8" width="116" height="62" rx="7" fill="{VERDE_CL}" stroke="{VERDE}"/>
  <rect x="524" y="8" width="116" height="62" rx="7" fill="{VERDE_CL}" stroke="{VERDE}"/>
  <rect x="492" y="116" width="148" height="62" rx="7" fill="{VERDE_CL}" stroke="{VERDE}"/>
  <rect x="262" y="116" width="178" height="62" rx="7" fill="#f8e9e4" stroke="#b5451b"/>
 </g>
 <g font-size="12.5" font-weight="bold" text-anchor="middle">
  <text x="58" y="30">Planilha SINISA</text><text x="189" y="30">1. Extração</text><text x="320" y="30">2. Staging</text>
  <text x="451" y="30">3. Transformação</text><text x="582" y="30">Esquema estrela</text>
  <text x="566" y="138">Views e leitura</text><text x="351" y="138">Validação</text>
 </g>
 <g font-size="10.6" text-anchor="middle">
  <text x="58" y="48">Excel · 5.570 linhas</text><text x="58" y="61">cabeçalho multilinha</text>
  <text x="189" y="48">Python · pandas</text><text x="189" y="61">remonta o cabeçalho</text>
  <text x="320" y="48">COPY · tudo em texto</text><text x="320" y="61">schema staging</text>
  <text x="451" y="48">SQL · limpeza, tipos</text><text x="451" y="61">e sinalização</text>
  <text x="582" y="48">schema sinisa</text><text x="582" y="61">fato + 2 dimensões</text>
  <text x="566" y="156">3 views · papel</text><text x="566" y="169">somente leitura</text>
  <text x="351" y="156">4 verificações + conferência</text><text x="351" y="169">com planilha e SQLite</text>
 </g>
 <g stroke="#555" stroke-width="1.4" fill="none" marker-end="url(#a)">
  <path d="M116,39 L129,39"/><path d="M247,39 L260,39"/><path d="M378,39 L391,39"/><path d="M509,39 L522,39"/>
  <path d="M582,70 L582,114"/><path d="M492,147 L442,147"/>
 </g>
</svg>"""


def _y(i):
    return 49 + 17 * i


def _tabela_er(x, w, titulo, cor, cor_cl, linhas):
    h = 24 + 17 * len(linhas) + 8
    out = (f'<rect x="{x}" y="10" width="{w}" height="{h}" rx="5" fill="#fff" stroke="{cor}" stroke-width="1.3"/>'
           f'<path d="M{x},34 L{x},15 Q{x},10 {x+5},10 L{x+w-5},10 Q{x+w},10 {x+w},15 L{x+w},34 Z" fill="{cor_cl}" stroke="{cor}" stroke-width="1.3"/>'
           f'<text x="{x+w/2}" y="26" text-anchor="middle" font-size="11" font-weight="bold">{titulo}</text>')
    for i, (marca, nome, tipo) in enumerate(linhas):
        out += (f'<text x="{x+6}" y="{_y(i)}" font-size="9" font-weight="bold" fill="{VERDE}">{marca}</text>'
                f'<text x="{x+26}" y="{_y(i)}" font-family="Consolas, monospace" font-size="10">{nome}</text>'
                f'<text x="{x+w-6}" y="{_y(i)}" font-family="Consolas, monospace" font-size="9" fill="#666" text-anchor="end">{tipo}</text>')
    return out


SVG_ER = f"""
<svg viewBox="-2 0 566 205" xmlns="http://www.w3.org/2000/svg" font-family="Arial, sans-serif" fill="{TEXTO}">
 <defs><marker id="b" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#555"/></marker></defs>
 {_tabela_er(0, 166, "MUNICIPIO (dimensão)", "#47627a", "#dfe9f2", [("PK", "cod_ibge", "CHAR(7)"), ("", "nome_municipio", "VARCHAR"), ("", "uf", "CHAR(2)"), ("", "regiao", "VARCHAR"), ("", "populacao_total", "INTEGER"), ("", "respondeu", "BOOLEAN")])}
 {_tabela_er(188, 190, "RESULTADO_INDICADOR (fato)", VERDE, VERDE_CL, [("PK", "id_resultado", "BIGINT"), ("FK", "cod_ibge", "CHAR(7)"), ("FK", "codigo_indicador", "VARCHAR"), ("", "ano_referencia", "SMALLINT"), ("", "valor", "DOUBLE"), ("", "flag_qualidade", "VARCHAR")])}
 {_tabela_er(400, 160, "INDICADOR (dimensão)", "#47627a", "#dfe9f2", [("PK", "codigo", "VARCHAR"), ("", "nome", "VARCHAR"), ("", "unidade", "VARCHAR"), ("", "grupo", "VARCHAR"), ("", "definicao", "TEXT")])}
 <g stroke="#555" stroke-width="1.3" fill="none" marker-end="url(#b)">
  <path d="M166,{_y(0)-4} L177,{_y(0)-4} L177,{_y(1)-4} L186,{_y(1)-4}"/>
  <path d="M400,{_y(0)-4} L389,{_y(0)-4} L389,{_y(2)-4} L380,{_y(2)-4}"/>
 </g>
 <g font-size="9.5" font-weight="bold" fill="{VERDE}">
  <text x="168" y="{_y(0)-8}">1</text><text x="170" y="{_y(1)+8}">N</text>
  <text x="391" y="{_y(0)-8}">1</text><text x="379" y="{_y(2)+8}">N</text>
 </g>
 <g font-size="9.5">
  <text x="0" y="176"><tspan font-weight="bold">Restrições do fato:</tspan> UNIQUE (cod_ibge, codigo_indicador, ano_referencia); CHECK valor &gt;= 0; ano 2000 a 2100;</text>
  <text x="0" y="190">CHECK flag_qualidade nula ou em (PERCENTUAL_ACIMA_100, MASSA_PER_CAPITA_ALTA). Tipos abreviados (Apêndice B).</text>
 </g>
</svg>"""

# ------------------------------------------------------------------ texto
participantes = [
    ("Walter Augusto Quintino Fonseca", "1260922513033"),
    ("Gabriel Champin", "1260922513021"),
    ("Gabriel Kenji Uehara", "1260922421020"),
    ("Luana Monteiro Cunha Rodrigues", "1260922513015"),
    ("Pedro Luis Avila de Genaro", "1260922513019"),
]
lista_part = "".join(
    f"<li>{e(n)} – RA {ra} – Informática para Negócios – Fatec São Bernardo do Campo “Adib Moisés Dib”</li>"
    for n, ra in participantes)

TITULO = "Do dado bruto ao indicador confiável: banco de dados relacional para os resíduos sólidos urbanos do Brasil (SINISA 2025)"

resumo = (
    f"Este artigo documenta a camada de banco de dados de um projeto que analisa a gestão de resíduos sólidos urbanos "
    f"nos municípios brasileiros com dados do Sistema Nacional de Informações em Saneamento Básico (SINISA 2025, ano de "
    f"referência 2024). A planilha oficial de indicadores, com {br(n_mun)} linhas e cabeçalho distribuído em várias linhas, "
    f"foi lida com Python, gravada sem tratamento em uma área de staging no PostgreSQL {N['versao_pg']} e transformada em SQL "
    f"em um esquema estrela com duas dimensões (município e indicador) e uma tabela fato de {br(n_fato)} registros. O modelo "
    f"usa chaves primárias e estrangeiras, restrições UNIQUE e CHECK, índices de apoio e três views analíticas. Um papel "
    f"somente leitura, um backup lógico com pg_dump restaurado em um banco de teste e verificações de integridade compõem a "
    f"administração do banco. A carga foi conferida contra a planilha original, lida de novo por um caminho independente do "
    f"ETL, e contra uma segunda base, em SQLite, usada pelo painel interativo: os {br(n_fato)} resultados e os {br(n_mun)} "
    f"municípios coincidem registro a registro nas duas conferências, sem nenhuma diferença. Valores suspeitos "
    f"({N['flags_total']}) foram sinalizados em vez de apagados. O artigo reúne os comandos executados, as telas dos dados e "
    f"do painel e as limitações: o painel não lê o PostgreSQL, a camada PostgreSQL não tem uma tabela de apoio que existe no "
    f"SQLite e o servidor usado é local, com autenticação sem senha."
)

intro = f"""
<p>Medir como os municípios coletam, recuperam e destinam seus resíduos é condição para acompanhar a Política Nacional de
Resíduos Sólidos, que exige a disposição final ambientalmente adequada dos rejeitos (BRASIL, 2010). Os dados abertos do
SINISA, do Ministério das Cidades, são divulgados em planilhas eletrônicas (BRASIL, 2025a).</p>
<p>A planilha de indicadores traz uma linha por município ({br(n_mun)} linhas), com código IBGE, nome, UF, macrorregião,
população, indicação de resposta ao módulo de resíduos e uma coluna por indicador. Usada diretamente, ela não impede
um código repetido, um percentual negativo ou um município inexistente; não registra de onde veio cada linha, não separa
quem pode ler de quem pode alterar e não tem cópia de segurança controlada.</p>
<p>Este trabalho trata esse problema como uma questão de administração de banco de dados: modelar os dados, carregá-los com
rastreabilidade, fazer o próprio banco recusar dados inválidos, validar a carga, controlar o acesso, proteger com cópia de
segurança e documentar tudo de forma reproduzível. É o componente de Administração de Banco de Dados de um projeto de
extensão do curso de Informática para Negócios da Fatec São Bernardo do Campo; a análise estatística dos mesmos dados é
entregue em artigo próprio, na disciplina de Estatística.</p>
"""

objetivos = """
<p><b>Objetivo geral:</b> projetar, implantar e validar um banco de dados relacional no PostgreSQL com os indicadores de
resíduos sólidos urbanos do SINISA 2025, de modo que as análises e o painel do projeto partam de dados íntegros,
rastreáveis e conferidos.</p>
<p><b>Objetivos específicos:</b> (a) extrair a planilha e preservá-la sem alterações em uma área de staging; (b) modelar um
esquema estrela com restrições de integridade e índices; (c) transformar e carregar os dados em SQL, sinalizando
valores suspeitos sem apagá-los; (d) validar a carga por verificações de integridade e por comparação com a planilha
original e com uma segunda base; (e) aplicar práticas de administração: controle de acesso por papel, backup e
restauração, inspeção do armazenamento físico; (f) documentar evidências (comandos e telas) e limitações.</p>
"""

fund = """
<p>No modelo relacional, os dados ficam em tabelas ligadas por chaves, e o sistema gerenciador de banco de dados (SGBD)
pode impor regras de integridade: de domínio (tipos e restrições CHECK), de chave (unicidade) e referencial (chave
estrangeira) (ELMASRI; NAVATHE, 2018). Impor essas regras no banco, e não apenas nos programas que o usam, evita que uma
carga ou uma consulta mal escrita produza dados inconsistentes.</p>
<p>Para análise, é comum organizar os dados em um esquema estrela: uma tabela fato guarda as medidas (aqui, o valor de
cada indicador por município e ano) e tabelas de dimensão guardam os descritores pelos quais as medidas são agrupadas
(município e indicador) (KIMBALL; ROSS, 2013). A desnormalização moderada das dimensões é uma escolha consciente desse
modelo, em troca de consultas mais simples.</p>
<p>No processo ELT (extrair, carregar e transformar), os dados são carregados primeiro em uma área de pouso (staging),
quase sem alteração, e transformados dentro do próprio banco. Isso permite auditar a carga e refazer a limpeza sem
voltar à origem. Completam a administração do banco o controle de acesso por papéis (GRANT), os índices e a leitura do
plano de execução das consultas, a cópia de segurança (aqui, lógica, com pg_dump) e o conhecimento de como o SGBD
guarda os dados em disco (ELMASRI; NAVATHE, 2018).</p>
"""

quadro_ind = quadro(
    "ind", "Indicadores do SINISA carregados no banco",
    ["Código", "Indicador", "Unidade", "Grupo"],
    [["IRS0001", "Cobertura da população total com coleta de resíduos sólidos domiciliares", "Percentual", "Cobertura"],
     ["IRS0005", "Cobertura da população total com coleta seletiva de resíduos sólidos domiciliares", "Percentual", "Cobertura"],
     ["IRS1004", "Massa média per capita de resíduos sólidos urbanos coletados", "Kg/hab.dia", "Operacional"],
     ["IRS3001", "Desempenho da coleta seletiva", "Percentual", "Qualidade"],
     ["IRS3002", "Disposição final inadequada de resíduos sólidos urbanos", "Percentual", "Qualidade"],
     ["IRS3010", "Recuperação de resíduos recicláveis secos e orgânicos em relação à quantidade total coletada", "Percentual", "Qualidade"]],
    "tabela sinisa.indicador do banco; nomes e unidades conforme o glossário do SINISA (BRASIL, 2025b).",
)

met_dados = f"""
<h3>4.1 Dados de origem</h3>
<p>A origem é a planilha “SINISA_RESIDUOS_Indicadores_2024.xlsx” (BRASIL, 2025a), com {br(n_mun)} municípios, dos quais
{br(n_resp)} ({br(pct_resp, 1)}%) responderam ao módulo de resíduos; esses reúnem {br(N['pop_resp'])} habitantes, ou
{br(pct_pop, 1)}% dos {br(N['pop_total'])} da população total da planilha. Os {br(n_nresp)} municípios que não responderam
permanecem no banco, marcados como não respondentes, mas não têm valores de indicador. O projeto usa seis indicadores
(Quadro {Q['ind']}) em corte transversal: um valor por município, ano de referência 2024.</p>
{quadro_ind}
<h3>4.2 Ambiente</h3>
<p>O servidor é o PostgreSQL {N['versao_pg']} em sua distribuição portátil para Windows, que dispensa instalador e
privilégios de administrador, executado no próprio computador (localhost, porta 5433). A extração e a carga usam Python
com as bibliotecas pandas (McKINNEY, 2010) e psycopg; o cliente de linha de comando é o psql. Os scripts, o banco de
dados e o dump estão no repositório do projeto (Apêndice A).</p>
"""

met_arq = f"""
<h3>4.3 Arquitetura em camadas</h3>
<p>O banco tem dois schemas (Figura {F['fluxo']}). O schema <i>staging</i> recebe uma cópia fiel da planilha, com todas as
colunas em texto e a posição da linha de origem (<i>linha_origem</i>), o que permite auditar a carga. O schema
<i>sinisa</i> guarda o modelo final, com tipos, chaves e restrições. A extração reconstrói o cabeçalho, que na planilha
ocupa várias linhas, e grava o resultado com o comando COPY; a limpeza e a conversão de tipos são feitas em SQL, dentro
do banco, sem alterar a origem.</p>
{figura_svg("fluxo", SVG_FLUXO, "Fluxo de dados, da planilha ao esquema estrela", "elaborado pelos autores.")}
"""

met_modelo = f"""
<h3>4.4 Modelo de dados</h3>
<p>O esquema estrela (Figura {F['er']}) tem duas dimensões, <i>municipio</i> ({br(n_mun)} linhas) e <i>indicador</i>
({n_ind} linhas), e a tabela fato <i>resultado_indicador</i>, em formato longo: uma linha por município, indicador e ano.
O formato longo permite acrescentar um indicador novo sem alterar a estrutura da tabela. Três decisões merecem registro:
(i) a coluna <i>regiao</i> fica em <i>municipio</i>, embora dependa da UF, o que é uma desnormalização deliberada do
esquema estrela; (ii) municípios que não responderam continuam em <i>municipio</i> (<i>respondeu = false</i>) e não têm
linhas na fato; (iii) valores suspeitos recebem uma marca em <i>flag_qualidade</i> e não são removidos.</p>
{figura_svg("er", SVG_ER, "Modelo entidade-relacionamento do schema sinisa", "elaborado pelos autores, a partir de sql/postgres/01_schema.sql.")}
{quadro(
    "restr", "Restrições de integridade impostas pelo banco",
    ["Tabela", "Restrições"],
    [["<i>municipio</i>", "chave primária em <i>cod_ibge</i>; CHECK: código com 7 dígitos, UF com 2 letras maiúsculas, região entre as cinco macrorregiões, população maior ou igual a zero"],
     ["<i>indicador</i>", "chave primária em <i>codigo</i>; CHECK: unidade em (Percentual, Kg/hab.dia) e grupo em (Cobertura, Operacional, Qualidade)"],
     ["<i>resultado_indicador</i>", "chave primária (identidade); chaves estrangeiras para <i>municipio</i> e <i>indicador</i>; UNIQUE (<i>cod_ibge</i>, <i>codigo_indicador</i>, <i>ano_referencia</i>); CHECK: valor maior ou igual a zero, ano entre 2000 e 2100, <i>flag_qualidade</i> nula ou em dois valores"]],
    "sql/postgres/01_schema.sql; contagem conferida no catálogo do banco "
    f"(CHECK: {rst['municipio']['c']}, {rst['indicador']['c']} e {rst['resultado_indicador']['c']}; chaves estrangeiras: {rst['resultado_indicador']['f']}; UNIQUE: {rst['resultado_indicador']['u']}).",
)}
<p>Além das chaves, o banco tem {len([i for i in N['indices'] if i.startswith('idx_')])} índices de apoio às consultas
(por UF, por indicador e por município); as chaves primárias e a restrição UNIQUE criam, cada uma, seu próprio índice.
O script completo está no Apêndice B.</p>
"""

met_etl = f"""
<h3>4.5 Transformação e carga em SQL</h3>
<p>A transformação (Apêndice C) aplica cinco regras: (1) normaliza o código IBGE (remove espaços e a parte decimal,
descarta o que não tem 7 dígitos e, em caso de duplicata, mantém a primeira linha); (2) remove espaços dos textos, põe a UF
em maiúsculas e converte a resposta ao módulo em valor lógico; (3) converte a população em inteiro; (4) carrega apenas
valores numéricos, descartando “null”, vazio e traço; (5) sinaliza, sem apagar, percentuais acima de 100
(<i>PERCENTUAL_ACIMA_100</i>) e massa per capita acima de 3 kg/hab.dia (<i>MASSA_PER_CAPITA_ALTA</i>). Os seis indicadores,
que na planilha ocupam seis colunas, são transformados em linhas da tabela fato.</p>
<p><b>O que as regras de fato alteraram nesta carga.</b> As regras 1, 3 e 4 são preventivas. Conferindo o staging e a
própria planilha, nenhum dos {br(n_stg)} códigos IBGE tinha parte decimal ou fugia dos 7 dígitos
({N['staging_cod_com_decimal']} e {cpl['codigos_nao_7_digitos_planilha']} ocorrências) e nenhum dos seis valores dos
{br(n_resp)} municípios respondentes era vazio ou não numérico ({N['staging_nao_numericos_respondentes']} no staging e
{cpl['valores_nao_numericos_respondentes']} na planilha): nesta edição do SINISA os dados já vinham limpos nesses pontos, e as
regras ficam como proteção para edições futuras. As intervenções efetivas foram duas: a exclusão dos pares sem valor, que
correspondem exatamente aos {br(n_nresp)} municípios não respondentes (pares possíveis: {br(n_mun)} × {n_ind} =
{br(pares)}; carregados: {br(n_fato)}; ausentes: {br(ausentes)} = {br(n_nresp)} × {n_ind}), e a sinalização de
{N['flags_total']} valores suspeitos: {f3001} percentuais acima de 100 no IRS3001 e {f1004} massas per capita acima de
3 kg/hab.dia no IRS1004.</p>
"""

met_views = """
<h3>4.6 Views e consultas</h3>
<p>Três views encapsulam as junções e agregações mais usadas (Apêndice D): <i>vw_municipio_indicadores</i> (um município por
linha, com os seis indicadores em colunas, só respondentes), <i>vw_resumo_uf</i> (média simples, média ponderada pela população
e mediana da disposição inadequada por UF) e <i>vw_resumo_regiao</i> (disposição inadequada e coleta seletiva médias por
macrorregião). A média ponderada usa a população do município como peso e representa o habitante, e não o município
típico.</p>
<h3>4.7 Administração do banco</h3>
<p><b>Acesso.</b> O papel <i>leitor_sinisa</i> recebe apenas USAGE no schema e SELECT nas tabelas. <b>Cópia de
segurança.</b> O backup é lógico, feito com pg_dump e restaurado em um banco de teste descartável, cujo conteúdo é comparado com
o original. <b>Armazenamento.</b> Consulta-se o catálogo para identificar o tablespace de cada objeto e o espaço ocupado.
<b>Validação.</b> Quatro verificações de integridade pós-carga (Apêndice D) devem devolver zero, e a carga é
comparada, registro a registro, com a planilha original e com a base SQLite que alimenta o painel.</p>
"""

r_intro = f"""
<p>Esta seção reúne as saídas reais dos comandos executados no banco e as telas do painel. Cada figura traz a fonte e a
interpretação no texto. Toda a saída de terminal foi produzida pelos autores no PostgreSQL {N['versao_pg']} local e pode ser
regerada com o script indicado no Apêndice E.</p>
"""

r_estr = f"""
<h3>5.1 Estrutura criada</h3>
<p>A Figura {F['estrutura']} mostra os dois schemas, as três tabelas do esquema estrela e as três views. A Figura {F['fato']}
detalha a tabela fato: tipos, chave primária, índices, restrições CHECK e chaves estrangeiras, como declarados no banco.</p>
{figura("estrutura", IMG/'01_estrutura.png', 'Schemas, tabelas e views do banco (psql)', 'saída do psql no banco residuos_sinisa, executada pelos autores.')}
{figura("fato", IMG/'02_tabela_fato.png', 'Estrutura da tabela fato resultado_indicador (psql, comando \\d)', 'saída do psql; linhas longas de CHECK e de chave estrangeira quebradas apenas para caber na página.')}
"""

r_carga = f"""
<h3>5.2 Carga e validação</h3>
<p>A Figura {F['carga']} mostra municípios não respondentes no staging, com os campos de indicador vazios, e a conferência de
contagens: {br(n_stg)} linhas no staging, {br(n_mun)} municípios, {br(n_resp)} respondentes e {br(n_fato)} linhas na fato,
que é igual a {br(n_resp)} respondentes × {n_ind} indicadores. A Figura {F['validacao']} reproduz as quatro verificações de
integridade pós-carga (Apêndice D), todas com zero problema.</p>
{figura("carga", IMG/'04_carga.png', 'Do staging ao modelo final: contagens da carga (psql)', 'saída do psql, executada pelos autores.')}
{figura("validacao", IMG/'05_validacao.png', 'Verificações de integridade pós-carga (04_validacao.sql)', 'saída do psql, executada pelos autores.')}
"""

r_integ = f"""
<h3>5.3 Integridade imposta pelo banco</h3>
<p>Para provar que as restrições funcionam, três inserções inválidas foram tentadas dentro de transações desfeitas por
ROLLBACK (Figura {F['integridade']}): um valor negativo é recusado pelo CHECK <i>ck_resultado_valor</i>; um município
inexistente, pela chave estrangeira <i>fk_resultado_mun</i>; um resultado repetido, pela restrição UNIQUE
<i>uq_resultado</i>. Ao final, a tabela continua com {br(n_fato)} linhas. O número que aparece na linha rejeitada
(id 29125) é o próximo valor da coluna de identidade; esse contador não retrocede quando uma transação é desfeita, de modo
que a numeração pode ter “buracos” sem que haja dado perdido.</p>
{figura("integridade", IMG/'06_integridade.png', 'O banco recusa dados inválidos (CHECK, chave estrangeira e UNIQUE)', 'saída do psql, executada pelos autores; transações desfeitas por ROLLBACK.')}
"""

tab_media = tabela(
    "media", "Média simples e média ponderada pela população, por indicador (consulta Q05)",
    ["Indicador", "Média simples", "Média ponderada"],
    [[c, br(msp[c][0], 2), br(msp[c][1], 2)] for c in sorted(msp)],
    "consulta SQL sobre sinisa.resultado_indicador e sinisa.municipio, executada pelos autores.",
    nota=f"valores em %, exceto IRS1004 (kg/hab.dia); n = {br(n_resp)} municípios em cada indicador.",
    alinhar="lrr",
)
tab_reg = tabela(
    "regiao", "Disposição inadequada (IRS3002) e coleta seletiva (IRS0005) por macrorregião",
    ["Região", "Municípios respondentes", "IRS3002 média (%)", "IRS0005 média (%)"],
    [[r[0], br(r[1]), br(r[2], 2), br(r[3], 2)] for r in reg],
    "view sinisa.vw_resumo_regiao, executada pelos autores.",
    nota="médias simples dos municípios de cada região.",
    alinhar="lrrr",
)
tab_faixa = tabela(
    "faixa", "Distribuição dos municípios respondentes por situação do IRS3002",
    ["Situação", "Municípios", "% dos respondentes"],
    [[a, br(b), br(100 * b / n_resp, 1)] for a, b in N["irs3002_faixas"]] + [["Total", br(n_resp), "100,0"]],
    "sinisa.resultado_indicador, executada pelos autores.",
    alinhar="lrr",
)

r_cons = f"""
<h3>5.4 Consultas e views</h3>
<p>A Figura {F['views']} mostra as views em uso: os indicadores de três municípios em colunas e o ranking das UFs com função
de janela (<i>rank() OVER</i>). A Tabela {T['media']} compara média simples e ponderada pela população (consulta do Apêndice
D): a diferença é grande no IRS3002 ({br(msp['IRS3002'][0], 2)}% contra {br(msp['IRS3002'][1], 2)}%), o que indica que os
municípios mais populosos têm valores menores. Na Tabela {T['regiao']}, a região Norte tem a maior média de disposição
inadequada ({br(reg[0][2], 2)}%) e a Sul, a menor ({br(reg[-1][2], 2)}%). A Tabela {T['faixa']} mostra que a distribuição do
IRS3002 se concentra nos extremos. Para São Paulo, a view <i>vw_resumo_uf</i> dá média simples de {br(sp_s, 2)}% e ponderada
de {br(sp_p, 2)}%, na {N['uf_sp_posicao']}ª posição entre as {N['n_ufs']} UFs do ranking de pior destinação. Esses números
coincidem com os do artigo de Estatística do grupo, o que confirma que as duas análises partem da mesma base.</p>
{figura("views", IMG/'07_views.png', 'Views e função de janela em uso (psql)', 'saída do psql, executada pelos autores.')}
{tab_media}
{tab_reg}
{tab_faixa}
"""

r_perf = f"""
<h3>5.5 Plano de execução e índice</h3>
<p>Para a consulta da média do IRS3002, o planejador escolheu o índice <i>idx_resultado_indicador</i> (Bitmap Index Scan),
lendo {paginas_heap} páginas da tabela (Figura {F['explain']}). Forçando o planejador a ignorar índices, a mesma consulta passa
a usar varredura sequencial. Em uma execução de cada, o tempo foi de {br(t_idx, 1)} ms com o índice e {br(t_seq, 1)} ms sem ele.
Em outras execuções feitas durante a preparação do trabalho, o plano sem índice também foi mais lento, mas os tempos
oscilam de uma execução para outra. <b>Leitura cautelosa:</b> com apenas {br(n_fato)} linhas, a diferença absoluta é de
poucos milissegundos e foi obtida sem repetição estatística; ela indica, mas não prova, o ganho do índice. Que o índice
compense mais com volumes maiores é o comportamento esperado, mas é hipótese, não testada neste trabalho.</p>
{figura("explain", IMG/'08_explain.png', 'Plano de execução com e sem índice (EXPLAIN ANALYZE)', 'saída do psql, executada pelos autores; última execução de cada plano.')}
"""

r_seg = f"""
<h3>5.6 Controle de acesso</h3>
<p>A Figura {F['seguranca']} mostra o papel <i>leitor_sinisa</i>, seus privilégios na tabela <i>municipio</i> (“r”, isto é,
somente leitura, contra “arwdDxtm” do dono) e o teste prático: como leitor, a consulta é permitida e o DELETE é recusado
com “permission denied”; de volta ao dono, a tabela segue intacta.</p>
{figura("seguranca", IMG/'09_seguranca.png', 'Papel somente leitura: SELECT permitido e DELETE recusado', 'saída do psql, executada pelos autores.')}
"""

r_arm = f"""
<h3>5.7 Armazenamento físico</h3>
<p>O PostgreSQL já traz dois tablespaces, <i>pg_default</i> e <i>pg_global</i>; nenhum foi criado para o projeto, e todas as
tabelas e índices estão em <i>pg_default</i> (Figura {F['armazenamento']}). A tabela fato é um arquivo dentro da pasta de dados,
gravado em páginas de 8 kB. O banco inteiro ocupa {t_banco}; a tabela fato, {t_fato}, e seus índices, {t_ind}; o staging,
{t_stg}. Com um banco desse tamanho, separar objetos em tablespaces diferentes não traria benefício prático; o recurso foi
estudado e explicado, mas não aplicado.</p>
{figura("armazenamento", IMG/'10_armazenamento.png', 'Tablespaces, localização dos objetos e espaço ocupado', 'saída do psql, executada pelos autores.')}
"""

r_bkp = f"""
<h3>5.8 Cópia de segurança e restauração</h3>
<p>O backup lógico do banco ({bytes_dump} bytes) foi restaurado em um banco novo, <i>residuos_teste</i>, e as contagens, a
soma da população e a média do IRS3002 foram comparadas com as do original: iguais ({br(n_mun)} municípios, {br(n_fato)}
resultados, {br(N['pop_total'])} habitantes, {br(n_stg)} linhas de staging e média {br(msp['IRS3002'][0], 2)}) (Figura
{F['backup']}). O banco de teste foi removido em seguida. As linhas “set_config” e “setval” impressas na restauração são
comandos do próprio dump, não erros.</p>
{figura("backup", IMG/'11_backup_restore.png', 'Backup com pg_dump e restauração em banco de teste', 'comandos executados pelos autores; saída real.')}
"""

quadro_cmp = quadro(
    "cmp", "Conferências do banco contra a planilha original e contra o SQLite do painel",
    ["Conferência", "Itens comparados", "Diferenças"],
    [["<b>Contra a planilha original (leitura direta, sem o ETL)</b>"],
     ["Campos do município (nome, UF, região, população, respondeu)", br(n_mun), br(cpl["municipios_campos_diferentes"])],
     ["Resultados presentes em apenas um dos lados (município × indicador)", f"{br(cpl['resultados_planilha'])} e {br(n_fato)}", br(cpl["resultados_so_em_um"])],
     ["Valores de indicador diferentes (diferença máxima absoluta: " + f"{cpl['maior_diferenca_absoluta']:g})", br(n_fato), br(cpl["valores_diferentes"])],
     ["População dos respondentes (soma)", br(cpl["pop_resp_planilha"]), br(cpl["pop_resp_planilha"] - N["pop_resp"])],
     ["Valores acima dos limites (IRS3001 &gt; 100: " + f"{cpl['flags_acima_100_irs3001']}; IRS1004 &gt; 3: {cpl['flags_irs1004_acima_3']}) × marcas no banco", f"{cpl['flags_acima_100_irs3001'] + cpl['flags_irs1004_acima_3']} e {N['flags_total']}", br(cpl["flags_acima_100_irs3001"] + cpl["flags_irs1004_acima_3"] - N["flags_total"])],
     ["<b>Contra o SQLite do painel (comparação registro a registro)</b>"],
     ["Municípios presentes em apenas uma base", f"{br(n_mun)} e {br(cmpq['municipios_sqlite'])}", br(cmpq["municipios_so_em_um"])],
     ["Campos do município diferentes", br(n_mun), br(cmpq["municipios_campos_diferentes"])],
     ["Resultados presentes em apenas uma base", f"{br(n_fato)} e {br(cmpq['resultados_sqlite'])}", br(cmpq["resultados_so_em_um"])],
     ["Valores diferentes (diferença máxima absoluta: " + f"{cmpq['maior_diferenca_absoluta']:g})", br(n_fato), br(cmpq["valores_diferentes"])],
     ["Marcas de qualidade diferentes", f"{br(N['flags_total'])} e {br(cmpq['flags_sqlite'])}", br(cmpq["flags_diferentes"])]],
    "script docs/entrega_abd/coletar_numeros.py, que lê a planilha (biblioteca openpyxl) e os dois bancos e compara cada registro pela chave.",
    alinhar="lrr",
)
r_cmp = f"""
<h3>5.9 Conferência com a planilha original e com a base do painel</h3>
<p>A primeira conferência é a mais forte: a planilha original foi lida de novo, diretamente, com uma biblioteca diferente
(openpyxl) e sem usar nenhum código do ETL do projeto, e cada valor foi comparado com o do PostgreSQL (Quadro {Q['cmp']}). Os
{br(cpl['linhas_planilha'])} municípios, os {br(cpl['respondentes_planilha'])} respondentes e os {br(n_fato)} pares
município × indicador coincidem; não há valor diferente, e a população dos respondentes e as {N['flags_total']} marcas de
qualidade também batem.</p>
<p>A segunda conferência compara o PostgreSQL com a cópia em SQLite usada pelo painel, gerada por outro ETL (em
Python): cada um dos {br(n_fato)} resultados e dos {br(n_mun)} municípios foi comparado pela chave, sem nenhuma diferença.
Como a leitura da planilha é comum aos dois ETLs, a comparação com o SQLite valida a transformação e a carga; quem cobre
a leitura é a comparação direta com a planilha.</p>
{quadro_cmp}
"""

r_ui = f"""
<h3>5.10 Interface: painel interativo</h3>
<p>O painel, desenvolvido em Streamlit, consome os dados tratados (SQLite) e tem quatro abas: Panorama, Estados, Municípios
e Método e limitações (esta última declara ao usuário a fonte, a cobertura, o significado dos zeros e os limites do
estudo). A Figura {F['pan']} mostra os indicadores principais e o recorte por região; a Figura {F['est']}, o ranking das UFs;
a Figura {F['mun']}, a distribuição dos municípios e o início da tabela de dados. Os valores exibidos coincidem com os do
banco (por exemplo, disposição inadequada de {br(msp['IRS3002'][0], 2)}%, média ponderada de {br(msp['IRS3002'][1], 2)}%, em
{br(n_resp)} municípios). Os nomes de município aparecem como na planilha do SINISA (por exemplo, “Alta Floresta D Oeste”).</p>
{figura("pan", W/'dash_panorama_crop.png', 'Painel: aba Panorama (indicadores principais e regiões)', 'captura do painel em execução, feita pelos autores.', largura_cm=13.0)}
{figura("est", W/'dash_estados_crop.png', 'Painel: aba Estados (ranking das UFs por disposição inadequada)', 'captura do painel em execução, feita pelos autores.', largura_cm=13.0)}
{figura("mun", W/'dash_municipios_crop.png', 'Painel: aba Municípios (distribuição e tabela de dados)', 'captura do painel em execução, feita pelos autores.', largura_cm=13.0)}
"""

discussao = f"""
<p>O banco cumpre o que se propôs: a estrutura impõe integridade, a carga é rastreável (cada linha do staging guarda sua
posição de origem), as verificações dão zero problema, a restauração reproduz o original e as bases coincidem registro a
registro. As limitações abaixo são fatos conhecidos do projeto, e não hipóteses.</p>
<ul>
<li><b>O painel não lê o PostgreSQL.</b> Ele usa a cópia em SQLite porque o serviço de publicação do painel não alcança um
PostgreSQL local. Para o painel ler o PostgreSQL seria preciso um servidor acessível pela internet, o que não foi feito.</li>
<li><b>A camada PostgreSQL é um subconjunto do SQLite.</b> A tabela de apoio <i>destinacao_municipio</i> (massa das rotas de
coleta por classe de destino, que reproduz o IRS3002) e a tabela de controle <i>etl_meta</i> existem só no SQLite; o dump e os
scripts do PostgreSQL refletem o modelo anterior a elas.</li>
<li><b>Alcance das conferências.</b> A comparação direta com a planilha cobre os seis indicadores, a população, o nome, a UF e
a região; as demais colunas da planilha não são carregadas e, portanto, não foram conferidas. Conferir que o banco reproduz a
planilha não verifica se o dado declarado pelo município está correto.</li>
<li><b>Segurança de laboratório.</b> O servidor aceita conexões só do próprio computador e usa autenticação “trust”, e o
papel de leitura não tem senha. Isso serve a um banco local de estudo e não a produção, que exigiria autenticação por senha,
conexão cifrada e regras de acesso por endereço.</li>
<li><b>Cópia de segurança.</b> Foi testada a restauração de um backup lógico na mesma máquina e versão do PostgreSQL; não foram
testados backup físico, arquivamento contínuo (WAL) nem restauração em outro computador.</li>
<li><b>Desempenho.</b> O volume ({br(n_fato)} linhas, {t_banco}) é pequeno demais para medir o efeito de índices e de
tablespaces (seções 5.5 e 5.7).</li>
<li><b>Dados.</b> São autodeclarados pelos municípios; {br(n_nresp)} municípios ({br(100 - pct_resp, 1)}%) não responderam e ficam
sem indicadores; o estudo cobre um único ano; em alguns indicadores, o valor zero pode significar ausência do serviço ou da
informação.</li>
</ul>
"""

conclusao = f"""
<p>Foi implantado, no PostgreSQL {N['versao_pg']}, um banco relacional para os indicadores de resíduos sólidos urbanos do
SINISA 2025, com staging, esquema estrela, {n_check} restrições CHECK, {rst['resultado_indicador']['f']} chaves estrangeiras,
uma restrição UNIQUE, três views, um papel somente leitura e um ciclo testado de backup e restauração. A carga de
{br(n_fato)} resultados de {br(n_resp)} municípios foi validada por verificações de integridade e por comparação, registro a
registro, com a planilha original e com a base do painel, sem diferenças. O trabalho entrega, além do banco, os scripts, as
evidências de execução e um painel que mostra os dados ao usuário final.</p>
<p>Como próximos passos, sugerem-se: levar a tabela <i>destinacao_municipio</i> à camada PostgreSQL e regerar o dump; publicar um
PostgreSQL acessível para que o painel o consulte; adotar autenticação por senha e conexão cifrada; e carregar edições futuras do
SINISA para medir a evolução, o que permitiria testar o efeito de índices e de particionamento com volumes maiores.</p>
"""

refs = [
    "BRASIL. Lei nº 12.305, de 2 de agosto de 2010. Institui a Política Nacional de Resíduos Sólidos; altera a Lei nº 9.605, de 12 de fevereiro de 1998; e dá outras providências. <b>Diário Oficial da União</b>: seção 1, Brasília, DF, 3 ago. 2010.",
    "BRASIL. Ministério das Cidades. <b>Sistema Nacional de Informações em Saneamento Básico (SINISA)</b>: indicadores de resíduos sólidos urbanos, ano de referência 2024. Brasília, DF: MCID, 2025a. Planilha eletrônica SINISA_RESIDUOS_Indicadores_2024.xlsx. Disponível em: https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa/resultados-sinisa. Acesso em: 9 nov. 2026.",
    "BRASIL. Ministério das Cidades. <b>SINISA</b>: glossário de indicadores de resíduos sólidos urbanos. Brasília, DF: MCID, [2025b]. Disponível em: https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa/resultados-sinisa/Glossario_Indicadores_SINISA_RESIDUOS.pdf. Acesso em: 9 nov. 2026.",
    "ELMASRI, R.; NAVATHE, S. B. <b>Sistemas de banco de dados</b>. 7. ed. São Paulo: Pearson, 2018.",
    "KIMBALL, R.; ROSS, M. <b>The data warehouse toolkit</b>: the definitive guide to dimensional modeling. 3. ed. Indianapolis: John Wiley &amp; Sons, 2013.",
    "McKINNEY, W. Data structures for statistical computing in Python. In: PYTHON IN SCIENCE CONFERENCE, 9., 2010, Austin. <b>Proceedings</b> [...]. Austin: SciPy, 2010. p. 56-61.",
]
refs_html = "".join(f"<p class='ref'>{r}</p>" for r in refs)


# ------------------------------------------------------------------ apêndices (trechos exatos dos arquivos do repositório)
def sql_trecho(arquivo, inicio, fim=None):
    linhas = (RAIZ / arquivo).read_text(encoding="utf-8").split("\n")
    i = next(k for k, l in enumerate(linhas) if inicio in l)
    j = next(k for k, l in enumerate(linhas) if fim in l and k > i) if fim else len(linhas)
    return "\n".join(linhas[i:j]).rstrip()


def sem_comentarios_de_objeto(txt):
    """Tira os comandos COMMENT ON ... ; (documentação do catálogo) para o apêndice ficar enxuto."""
    saida, pulando = [], False
    for l in txt.split("\n"):
        if l.startswith("COMMENT ON"):
            pulando = not l.rstrip().endswith(";")
            continue
        if pulando:
            pulando = not l.rstrip().endswith(";")
            continue
        saida.append(l)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(saida)).strip()


ap_ddl = sem_comentarios_de_objeto(sql_trecho("sql/postgres/01_schema.sql", "CREATE TABLE sinisa.municipio"))
ap_trf = sql_trecho("sql/postgres/02_transformacao.sql", "-- 1) Dimensão município", "ANALYZE sinisa.municipio")
ap_views = sem_comentarios_de_objeto(sql_trecho("sql/postgres/03_views_e_consultas.sql", "-- View: um município por linha", "-- Papel de leitura").rstrip("- \n"))
ap_grant = sql_trecho("sql/postgres/03_views_e_consultas.sql", "DO $$", "-- CONSULTAS DE EXEMPLO").rstrip("= \n-")
ap_val = sql_trecho("sql/postgres/04_validacao.sql", "SELECT 'resultados de municípios")
ap_q05_pg = """SELECT r.codigo_indicador,
       round(avg(r.valor)::numeric, 2) AS media_simples,
       round((sum(r.valor * m.populacao_total) / sum(m.populacao_total))::numeric, 2) AS media_ponderada
FROM sinisa.resultado_indicador r
JOIN sinisa.municipio m ON m.cod_ibge = r.cod_ibge
GROUP BY r.codigo_indicador
ORDER BY r.codigo_indicador;"""


def codigo(t):
    return f"<pre class='cod'>{e(t)}</pre>"


apendices = f"""
<h3 class="ap">Apêndice A – Repositório</h3>
<p class="esq">https://github.com/gchamps/analise-residuos-sinisa (scripts SQL do PostgreSQL em <i>sql/postgres/</i>, ETL em
<i>scripts/etl_postgres.py</i>, dump em <i>dados_tratados/postgres/residuos_sinisa.sql</i>, painel em <i>scripts/app.py</i>).
Os scripts que geraram as evidências e os números deste artigo estão em <i>docs/entrega_abd/</i>.</p>
<h3 class="ap">Apêndice B – Definição das tabelas (sql/postgres/01_schema.sql)</h3>
<p class="esq">Trecho do script, sem os comandos COMMENT ON (descrições do catálogo).</p>
{codigo(ap_ddl)}
<h3 class="ap">Apêndice C – Transformação e carga (sql/postgres/02_transformacao.sql)</h3>
{codigo(ap_trf)}
<h3 class="ap">Apêndice D – Views, papel de leitura, validação e consulta Q05</h3>
<p class="esq">Views (sql/postgres/03_views_e_consultas.sql, sem os COMMENT ON):</p>
{codigo(ap_views)}
<p class="esq">Papel de leitura (mesmo arquivo):</p>
{codigo(ap_grant)}
<p class="esq">Verificações de integridade pós-carga (sql/postgres/04_validacao.sql):</p>
{codigo(ap_val)}
<p class="esq">Consulta Q05 (média simples e ponderada por indicador), adaptada ao schema <i>sinisa</i> do PostgreSQL; a versão em
SQLite está em <i>sql/02_consultas.sql</i>:</p>
{codigo(ap_q05_pg)}
<h3 class="ap">Apêndice E – Como reproduzir (Windows, sem administrador)</h3>
{codigo(
"cd analise-residuos-sinisa\n"
".\\scripts\\postgres_portatil.ps1 instalar     # uma vez: baixa o PostgreSQL portátil\n"
".\\scripts\\postgres_portatil.ps1 iniciar      # liga o servidor em localhost:5433\n"
".\\scripts\\postgres_portatil.ps1 restaurar    # recria o banco a partir do dump versionado\n"
".\\scripts\\postgres_portatil.ps1 psql         # abre o console SQL\n"
"pip install -r requirements-postgres.txt\n"
"python scripts\\etl_postgres.py               # alternativa: recria o banco a partir da planilha e valida\n"
"python docs\\entrega_abd\\gerar_tudo.py <pasta> <saida.pdf>   # regera evidências, figuras e este PDF")}
"""

CSS = """
html { font: 11pt/19pt Arial, 'Liberation Sans', Helvetica, sans-serif; color:#111 }
body { margin:0; text-align: justify }
h1.titulo { font-size: 14pt; line-height: 19pt; text-align:center; margin: 0 0 8pt; text-wrap: balance }
.sub { text-align:center; font-size: 10pt; line-height: 14pt; color:#333; margin: 0 0 14pt }
.rot { font-weight: bold; margin: 12pt 0 3pt; break-after: avoid }
h2 { font-size: 11pt; margin: 18pt 0 4pt; break-after: avoid }
h3 { font-size: 11pt; font-weight: normal; margin: 12pt 0 3pt; break-after: avoid }
h3.ap { font-weight: bold }
p { margin: 0 0 7pt }
p.esq, p.ref { text-align: left } p.ref { margin-bottom: 7pt } p.esq { break-after: avoid }
ul { margin: 0 0 8pt; padding-left: 18pt } li { margin-bottom: 3pt }
ul.autores { text-align: left }
.resumo p { margin-bottom: 6pt }
figure { margin: 8pt 0 10pt; text-align: center; break-inside: avoid }
figure img, figure svg { display:block; margin: 0 auto }
figure svg { width: 100%; height: auto }
.leg { font-size: 10pt; line-height: 13pt; text-align: left; margin: 0 0 4pt; break-after: avoid }
.fonte, .nota { font-size: 9pt; line-height: 12pt; text-align: left; margin-top: 4pt }
figure.tab { text-align: left }
table { border-collapse: collapse; width: 100%; font-size: 9pt; line-height: 12pt;
        border-top: 1pt solid #000; border-bottom: 1pt solid #000 }
th { text-align: left; font-weight: bold; border-bottom: 0.6pt solid #000; padding: 3pt 5pt }
td { padding: 2.5pt 5pt; vertical-align: top; text-align: left }
th.d, td.d { text-align: right } th.c, td.c { text-align: center }
tr.sub td { padding-top: 5pt; border-top: 0.4pt solid #888 }
tbody tr:first-child.sub td { border-top: 0 }
pre.cod { font: 6.8pt/8.6pt Consolas, 'Courier New', monospace; text-align: left; white-space: pre-wrap;
          background: #f6f5f1; border: 0.5pt solid #cfc9bd; padding: 5pt 6pt; margin: 3pt 0 8pt; word-break: break-word; break-inside: avoid }
"""

doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{e(TITULO)}</title>
<style>{CSS}</style></head><body>
<h1 class="titulo">{e(TITULO)}</h1>
<div class="sub">Trabalho da disciplina de Administração de Banco de Dados<br>Curso de Informática para Negócios · São Bernardo do Campo, novembro de 2026</div>
<div class="rot">Lista de participantes (autores)</div>
<ul class="autores">{lista_part}</ul>
<div class="rot">Resumo</div><div class="resumo"><p>{resumo}</p>
<p><b>Palavras-chave:</b> Administração de banco de dados; PostgreSQL; Esquema estrela; ETL; SINISA; Resíduos sólidos urbanos.</p></div>
<h2>1. Introdução</h2>{intro}
<h2>2. Objetivos</h2>{objetivos}
<h2>3. Fundamentação teórica</h2>{fund}
<h2>4. Metodologia</h2>{met_dados}{met_arq}{met_modelo}{met_etl}{met_views}
<h2>5. Resultados e evidências</h2>{r_intro}
{r_estr}{r_carga}{r_integ}{r_cons}{r_perf}{r_seg}{r_arm}{r_bkp}{r_cmp}{r_ui}
<h2>6. Discussão e limitações</h2>{discussao}
<h2>7. Conclusão</h2>{conclusao}
<h2>Referências</h2>{refs_html}
<h2>Apêndices</h2>{apendices}
</body></html>"""

# a ordem de criação tem de coincidir com a numeração usada no texto
assert CRIADAS["fig"] == ORDEM_FIG, (CRIADAS["fig"], ORDEM_FIG)
assert CRIADAS["tab"] == ORDEM_TAB and CRIADAS["qua"] == ORDEM_QUA, CRIADAS
SAIDA.write_text(doc, encoding="utf-8")
print("HTML gerado:", SAIDA, f"({len(doc)//1024} KB); figuras: {len(ORDEM_FIG)}, tabelas: {len(ORDEM_TAB)}, quadros: {len(ORDEM_QUA)}")
