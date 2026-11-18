# Roteiro prático: o que mostrar no computador

Disciplina: **Administração de Banco de Dados**. Tempo: 10 a 15 minutos. O professor quer entender **o fluxo**, as **ferramentas** e os **conceitos de banco de dados** aplicados, de forma superficial. Não é um tour pelo aplicativo.

## O que o professor quer ver (e o que ignorar)

| Mostrar e explicar | Citar em uma frase, sem mostrar | Ignorar |
|---|---|---|
| De onde vieram os dados e como entraram no banco | A análise estatística (médias, mediana, ranking) | Testes automatizados, CI, auditorias |
| O modelo (esquema estrela), tipos, chaves, restrições, índices | O dashboard e a planilha como "consumidores" do banco | Detalhes do Streamlit, cores, gráficos |
| O tratamento feito **em SQL** (staging → modelo final) | Que os dados são autodeclarados pelos municípios | A discussão sobre os zeros do IRS3002 |
| Integridade, validação, usuário só de leitura, backup | Que o dashboard lê uma cópia em SQLite | Regressão, correlação, testes estatísticos |
| Consultas e plano de execução (índice) | | |

## Antes da apresentação

Siga o arquivo **`passo_a_passo_gabriel.md`** (nesta mesma pasta). Ele leva o notebook do zero até o banco restaurado e termina com a conferência **TUDO PRONTO**. Faça isso **antes**, não na hora.

Deixe abertos, antes de começar: (1) o PowerShell já preparado (passo 8 do guia), (2) o navegador em `https://github.com/gchamps/analise-residuos-sinisa`, (3) o Excel com `resultados\Analise_Estatistica_Residuos.xlsx` (opcional).
## Sequência da demonstração (16 minutos)

| # | Tempo | O que abrir ou rodar | O que apontar (uma frase) |
|---|---|---|---|
| 1 | 1 min | Navegador: repositório no GitHub, pastas `dados_originais`, `scripts`, `sql`, `dados_tratados`, `docs` | "Tudo está no GitHub: dados brutos, scripts, SQL e documentação." |
| 2 | 2 min | Navegador: `docs/banco_de_dados.md`, o **diagrama do pipeline** (Mermaid, aparece desenhado) | "Este é o fluxo: planilha, staging, modelo final, views e validação." |
| 3 | 1 min | Abra `dados_originais\SINISA_RESIDUOS_Indicadores_2024.xlsx` (só olhar o cabeçalho) | "A fonte é uma planilha com cabeçalho em duas linhas; por isso precisou de tratamento." |
| 4 | 3 min | PowerShell: `psql -h localhost -p 5433 -U postgres -d residuos_sinisa -f docs/apresentacao/demo_postgres.sql` — blocos **1** e **2** | "Dois *schemas*: `staging` (bruto) e `sinisa` (modelo). Três tabelas em esquema estrela. Aqui estão tipos, chaves, `CHECK` e índices." |
| 5 | 2 min | Mesmo script, blocos **3** e **4** | "A planilha entra toda como texto no staging. O SQL limpa e carrega. 5.570 linhas viram 29.124 (4.854 respondentes × 6 indicadores)." Depois: a validação deu tudo zero. |
| 6 | 1 min | Navegador: `sql/postgres/02_transformacao.sql` (mostrar só os comentários do topo) | "As regras de limpeza estão aqui, escritas em SQL, dentro do banco." |
| 7 | 1 min | Mesmo script, bloco **5** | "O banco recusa dado inválido: valor negativo, município que não existe, resultado repetido." |
| 8 | 2 min | Mesmo script, blocos **6** e **7** | "A view junta as tabelas e as estatísticas por UF saem do banco. O plano de execução usa o índice." |
| 9 | 1 min | Mesmo script, bloco **8** | "O usuário `leitor_sinisa` só consulta; tentar apagar é negado." |
| 10 | 1 min | Mesmo script, bloco **9** | "Os dados são arquivos numa pasta, em páginas de 8 KB. Tablespace liga tabelas e índices a um local do disco. Não criamos um próprio: está tudo no padrão." |
| 11 | 1 min | Backup (comando abaixo) e, se sobrar tempo, a planilha Excel (abas `Descritiva`, `Ranking_UF`) | "O banco se reconstrói a partir do dump, e a planilha usa os mesmos dados." |

Comando do backup (passo 11):

```powershell
pg_dump -h localhost -p 5433 -U postgres -n sinisa -f "$env:TEMP\backup_sinisa.sql" residuos_sinisa
dir "$env:TEMP\backup_sinisa.sql"
```

| 12 | 1 min | Navegador: `http://localhost:8501` (dashboard já aberto antes) | "Este é o resultado para o usuário: lê o banco (uma cópia em SQLite). Mapa, ranking por estado e, na aba Método, as definições que vêm da tabela `indicador`." |

Se o tempo apertar, corte o passo 10 (tablespaces) e encurte o 12.

**Como usar o script `demo_postgres.sql`:** ele para entre os blocos esperando **Enter**. Fale, aperte Enter e avance. Se preferir rodar bloco a bloco, abra o arquivo e copie as consultas.

## Cola de conceitos (marque os que o professor citou em aula)

| Conceito da matéria | Onde aparece no projeto |
|---|---|
| Modelagem relacional e dimensional (esquema estrela) | `sinisa.municipio`, `indicador` (dimensões) e `resultado_indicador` (fato) |
| Normalização e desnormalização consciente | `regiao` fica em `municipio`, embora dependa de `uf`, por ser dimensão |
| Tipos de dados | `CHAR(7)` (código IBGE), `SMALLINT`, `DOUBLE PRECISION`, `BOOLEAN`, `BIGINT IDENTITY` |
| Restrições de integridade | `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `NOT NULL`, `CHECK` |
| Schemas para organizar o banco | `staging` (bruto) e `sinisa` (final) |
| ETL / ELT e carga em lote | Planilha → `COPY` para o staging → transformação em SQL |
| Transações (ACID) | Esquema, carga e transformação rodam numa transação só; erro desfaz tudo |
| Índices e plano de execução | `idx_resultado_indicador` e `EXPLAIN ANALYZE` |
| Views | `vw_municipio_indicadores`, `vw_resumo_uf`, `vw_resumo_regiao` |
| Consultas avançadas | Função de janela (`rank() OVER`), `percentile_cont` (mediana), `FILTER` |
| Usuários e privilégios | Papel `leitor_sinisa` com `GRANT SELECT` |
| Armazenamento físico e tablespaces | **Não criamos tablespace próprio**: tudo no `pg_default`. O bloco 9 mostra isso, o arquivo de cada tabela e o tamanho do banco. Ao falar, diga "só explicamos", nunca "aplicamos". |
| Backup e restauração | `pg_dump` e `scripts/postgres_portatil.ps1 restaurar` |
| Documentação do banco | `COMMENT ON` nas tabelas e `docs/banco_de_dados.md` |
| Qualidade e validação dos dados | `sql/postgres/04_validacao.sql` e comparação com o SQLite |

## Plano B: se o Postgres não subir a tempo

O professor disse que dá para apresentar sem o banco rodando, e tudo isso funciona só com navegador:
1. **GitHub, `docs/banco_de_dados.md`**: mostra o pipeline e o diagrama entidade-relacionamento já desenhados.
2. **GitHub, `sql/postgres/01_schema.sql`**: tipos, chaves, `CHECK` e índices, tudo comentado.
3. **GitHub, `sql/postgres/02_transformacao.sql`**: o tratamento em SQL.
4. **GitHub, `sql/postgres/03_views_e_consultas.sql`** e **`sql/02_consultas.sql`**: as views e as 11 consultas estatísticas (média, mediana, desvio-padrão, ranking, taxa de resposta).
5. **Excel**: `resultados\Analise_Estatistica_Residuos.xlsx`, abas `Descritiva` e `Ranking_UF`.

Diga com naturalidade: "O servidor local não subiu nesta máquina a tempo; o banco, os scripts e o dump de restauração estão no repositório, e vou mostrar os scripts e o resultado." É a verdade e não gera problema.

## Se der problema na hora
- **Letras quebradas ou `psql` não encontrado:** rode de novo o passo 8 do guia na mesma janela.
- **Conexão recusada:** o servidor está desligado; rode o passo 8 do guia (ele liga sozinho).
- **Quer recomeçar o banco:** rode o `restaurar` (leva uns 2 segundos).
