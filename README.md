# ♻️ MPV - Análise e Diagnóstico da Gestão de Resíduos Sólidos

Projeto de extensão do 4º semestre (FATEC São Bernardo do Campo). Organiza, analisa e apresenta dados abertos do **SINISA 2025 (ano de referência 2024)** sobre resíduos sólidos urbanos e integra o resultado a um diagnóstico ambiental e de qualidade feito na empresa CGA Equipamentos Contra Incêndio LTDA.

**Público-alvo:** comunidade em geral (gestores, estudantes, empresas pequenas).

## O que o projeto entrega
| Entrega | Onde |
|---|---|
| Banco de dados PostgreSQL: extração, limpeza, carga, modelo, views e validação | `docs/banco_de_dados.md` (documentação), `sql/postgres/` (scripts), `scripts/etl_postgres.py` (ETL), `dados_tratados/postgres/residuos_sinisa.sql` (dump) |
| Script de banco de dados (SQL) documentado, versão SQLite usada pelo dashboard | `sql/01_schema.sql` (esquema) e `sql/02_consultas.sql` (consultas) |
| Código-fonte da aplicação web (Streamlit) | `scripts/app.py` |
| ETL (Excel → SQLite) | `scripts/etl_sqlite.py` |
| Planilha estatística com análises | `resultados/Analise_Estatistica_Residuos.xlsx` |
| Relatório diagnóstico de qualidade | `analise-residuos-sinisa.docx` |
| MPV publicado | _link da aplicação: preencher após o deploy_ |

## Como rodar
Requer Python 3.10+.
```bash
pip install -r requirements.txt
python scripts/etl_sqlite.py        # recria dados_tratados/projeto_residuos.db
streamlit run scripts/app.py        # abre o dashboard
```
Para regenerar a planilha: `python scripts/gerar_planilha.py` (usa `scripts/analise_estatistica.py`).

Banco PostgreSQL (opcional, para a parte de administração de banco de dados): veja `docs/banco_de_dados.md`. Resumo:
```powershell
.\scripts\postgres_portatil.ps1 instalar
.\scripts\postgres_portatil.ps1 iniciar
pip install -r requirements-postgres.txt
python scripts\etl_postgres.py
```

## Estrutura
```text
├── dados_originais/    planilhas brutas do SINISA (o ETL usa só SINISA_RESIDUOS_Indicadores_2024.xlsx)
├── dados_tratados/     banco SQLite e CSVs gerados pelo ETL; br_ufs.geojson (malha das UFs, IBGE) usada no mapa
├── resultados/         planilha estatística (Excel)
├── scripts/            etl_sqlite.py, analise_estatistica.py, gerar_planilha.py, app.py
├── sql/                01_schema.sql, 02_consultas.sql (SQLite); postgres/ (esquema, transformação, views, validação)
├── docs/               banco_de_dados.md (pipeline, modelo e validação do PostgreSQL)
├── analise-residuos-sinisa.docx   relatório acadêmico
└── requirements.txt
```

## Modelo de dados
Esquema estrela: dimensões `municipio` e `indicador`; fato `resultado_indicador` (município × indicador × ano). 4.854 municípios respondentes, 6 indicadores (IRS0001, IRS0005, IRS1004, IRS3001, IRS3002, IRS3010). Valores suspeitos são sinalizados (`flag_qualidade`), não apagados.

## Limitações
- Só municípios que responderam ao módulo de resíduos entram na análise.
- Os indicadores descrevem resíduos **urbanos municipais**; não medem resíduos industriais nem a gestão ambiental de empresas. O diagnóstico da CGA usa o SINISA apenas como contexto.
- Correlação e regressão indicam associação, não causalidade.

## Autores
Gabriel Champin, Gabriel Kenji, Luana Monteiro, Pedro Genaro e Walter Augusto.
Faculdade de Tecnologia de São Bernardo do Campo "Adib Moisés Dib".
