# ♻️ MPV - Análise e Diagnóstico da Gestão de Resíduos Sólidos

Projeto de extensão do 4º semestre (FATEC São Bernardo do Campo). Organiza, analisa e apresenta dados abertos do **SINISA 2025 (ano de referência 2024)** sobre resíduos sólidos urbanos e integra o resultado a um diagnóstico ambiental e de qualidade feito na empresa CGA Equipamentos Contra Incêndio LTDA.

**Público-alvo:** comunidade em geral (gestores, estudantes, empresas pequenas).

## O que o projeto entrega
| Entrega | Onde |
|---|---|
| Banco de dados PostgreSQL: extração, limpeza, carga, modelo, views e validação | `docs/banco_de_dados.md` (documentação), `sql/postgres/` (scripts), `scripts/etl_postgres.py` (ETL), `dados_tratados/postgres/residuos_sinisa.sql` (dump) |
| Script de banco de dados (SQL) documentado, versão SQLite usada pelo dashboard | `sql/01_schema.sql` (esquema) e `sql/02_consultas.sql` (consultas) |
| Código-fonte da aplicação web (Streamlit) | `scripts/app.py` |
| ETL (Excel → SQLite), com conferência do IRS3002 contra as rotas de coleta | `scripts/etl_sqlite.py` |
| Planilha estatística com análises | `resultados/Analise_Estatistica_Residuos.xlsx` |
| Relatório diagnóstico de qualidade | `analise-residuos-sinisa.docx` |
| Testes automatizados e CI | `tests/`, `.github/workflows/ci.yml` |
| MPV publicado | _link da aplicação: preencher após o deploy (veja "Publicação")_ |

## Como rodar
Requer Python 3.10+ (testado com 3.12).

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\etl_sqlite.py        # recria o banco e os CSVs (pula se nada mudou; --forcar refaz)
.\.venv\Scripts\python.exe -m streamlit run scripts\app.py
```

**Linux / macOS**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/etl_sqlite.py
streamlit run scripts/app.py
```

O banco e os CSVs já vêm versionados, então dá para abrir o dashboard sem rodar o ETL. Para reproduzir exatamente as versões testadas use `requirements.lock.txt` no lugar de `requirements.txt`.

Planilha estatística: `python scripts/gerar_planilha.py` (usa `scripts/analise_estatistica.py`). Resumo no console: `python scripts/analise_estatistica.py`.

### Testes
```bash
pip install -r requirements-dev.txt
python -m pytest -q
```
Os testes cobrem o ETL (regras de limpeza, carga atômica, conferência do indicador), os cálculos, o banco versionado e o dashboard inteiro (executado sem navegador). Um deles falha se alguém mudar as planilhas, o esquema ou o ETL e esquecer de regerar o banco versionado: nesse caso rode `python scripts/etl_sqlite.py --forcar` e faça commit do banco e dos CSVs.

### Banco PostgreSQL (opcional)
Para a parte de administração de banco de dados, veja `docs/banco_de_dados.md`. Resumo:
```powershell
.\scripts\postgres_portatil.ps1 instalar
.\scripts\postgres_portatil.ps1 iniciar
pip install -r requirements-postgres.txt
python scripts\etl_postgres.py
```
A camada PostgreSQL reflete o modelo anterior à tabela `destinacao_municipio` (veja "Limitações").

## Publicação (Streamlit Community Cloud)
1. Faça o push do repositório para o GitHub (a conta que vai publicar precisa de acesso a `gchamps/analise-residuos-sinisa`).
2. Em [share.streamlit.io](https://share.streamlit.io), escolha **Create app**, o repositório, a branch `main` e o arquivo principal `scripts/app.py`.
3. Em **Advanced settings**, selecione Python 3.12. As dependências vêm de `requirements.txt`.
4. O banco `dados_tratados/projeto_residuos.db` e a malha `dados_tratados/br_ufs.geojson` precisam estar no repositório: o app só lê esses arquivos.
5. Depois de publicado, coloque o link na tabela de entregas acima.

## Estrutura
```text
├── dados_originais/    planilhas brutas do SINISA (o ETL usa a de indicadores e a de Manejo)
├── dados_tratados/     banco SQLite e CSVs gerados pelo ETL; br_ufs.geojson (malha das UFs, IBGE) usada no mapa
├── resultados/         planilha estatística (Excel)
├── scripts/            etl_sqlite.py, calculos.py (cálculos comuns), mapa.py, analise_estatistica.py,
│                       gerar_planilha.py, comparar_bancos.py, app.py
├── sql/                01_schema.sql, 02_consultas.sql (SQLite); postgres/ (esquema, transformação, views, validação)
├── tests/              testes automatizados (pytest)
├── docs/               banco_de_dados.md, plano.md (plano de melhorias e registro), notas_para_o_relatorio.md
├── .github/workflows/  integração contínua
├── analise-residuos-sinisa.docx   relatório acadêmico
└── requirements*.txt   dependências (lock = versões exatas testadas)
```

## Modelo de dados
Esquema estrela: dimensões `municipio` e `indicador`; fato `resultado_indicador` (município × indicador × ano). 4.854 municípios respondentes, 6 indicadores (IRS0001, IRS0005, IRS1004, IRS3001, IRS3002, IRS3010). Valores suspeitos são sinalizados (`flag_qualidade`), não apagados.

Tabelas de apoio: `destinacao_municipio` (massa das rotas de coleta por tipo de destino, da planilha de Manejo) e `etl_meta` (impressão digital das entradas, usada para pular o ETL quando nada mudou).

## Como ler o IRS3002 (disposição final inadequada)
O IRS3002 é a massa das rotas de coleta que vão a lixão, vazadouro ou aterro controlado, dividida pela massa coletada líquida (coletada menos recuperada). O ETL recalcula isso a partir das rotas declaradas e confere com o indicador publicado nos 4.854 municípios (diferença máxima de 0,005 ponto percentual); se divergir, a carga falha.

Por isso um **0%** significa que o município não declarou nenhuma rota para lixão, vazadouro ou aterro controlado. Entre os 3.057 municípios com 0%, 94% declaram rotas a aterro sanitário ou de inertes que cobrem ao menos 90% da massa coletada líquida, 6% completam a massa somando unidades intermediárias (transbordo, triagem, compostagem) e 3 municípios têm declaração incompleta. Nenhum declara rota a lixão. **Os dados são autodeclarados**: o SINISA mostra o que cada município informou, mas não comprova que o destino informado é o real.

## Limitações
- Só municípios que responderam ao módulo de resíduos entram na análise.
- Os indicadores descrevem resíduos **urbanos municipais**; não medem resíduos industriais nem a gestão ambiental de empresas. O diagnóstico da CGA usa o SINISA apenas como contexto.
- Correlação e regressão indicam associação, não causalidade.
- Os valores são autodeclarados pelos municípios (veja acima).
- A camada PostgreSQL ainda não tem a tabela `destinacao_municipio` nem a conferência do IRS3002: não havia servidor PostgreSQL disponível para testar a mudança. O dashboard usa o SQLite.
- A planilha Excel (`gerar_planilha.py`) usa todos os valores, inclusive os sinalizados como suspeitos; o dashboard permite excluí-los no filtro lateral.

## Autores
Gabriel Champin, Gabriel Kenji, Luana Monteiro, Pedro Genaro e Walter Augusto.
Faculdade de Tecnologia de São Bernardo do Campo "Adib Moisés Dib".
