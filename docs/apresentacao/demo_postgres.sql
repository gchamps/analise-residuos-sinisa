-- =============================================================================
-- Demonstração para a disciplina de Administração de Banco de Dados
--
-- Como usar (na raiz do projeto, com o servidor ligado):
--     psql -h localhost -p 5433 -U postgres -d residuos_sinisa -f docs/apresentacao/demo_postgres.sql
-- Entre os blocos o script espera você apertar Enter: fale, depois avance.
-- Nada aqui altera os dados (os testes de erro rodam dentro de transação com ROLLBACK).
-- =============================================================================
\set ON_ERROR_STOP off
\pset pager off
\pset null '(nulo)'
\encoding UTF8
\set QUIET on

\echo
\echo '=== 1. ESTRUTURA: dois schemas, tres tabelas (esquema estrela) e tres views ==='
\dn staging|sinisa
\dt sinisa.*
\dv sinisa.*
\prompt 'Enter para continuar...' pausa

\echo
\echo '=== 2. A TABELA FATO: tipos, chave primaria, chaves estrangeiras, CHECK e indices ==='
\d sinisa.resultado_indicador
\prompt 'Enter para continuar...' pausa

\echo
\echo '=== 3. TRATAMENTO: da planilha (staging, tudo texto) para o modelo final ==='
\echo '-- Municipios que nao responderam: no staging aparecem com campos vazios'
SELECT cod_ibge, nom_mun, respondeu, irs0001, irs3002
FROM staging.stg_planilha
WHERE respondeu <> 'Sim'
LIMIT 3;
\echo '-- Linhas: planilha larga (1 linha por municipio) -> tabela fato longa (1 linha por municipio x indicador)'
SELECT (SELECT count(*) FROM staging.stg_planilha)                          AS linhas_staging,
       (SELECT count(*) FROM sinisa.municipio)                              AS municipios,
       (SELECT count(*) FROM sinisa.municipio WHERE respondeu)              AS respondentes,
       (SELECT count(*) FROM sinisa.resultado_indicador)                    AS linhas_fato,
       (SELECT count(*) FROM sinisa.municipio WHERE respondeu) * 6          AS respondentes_x_6_indicadores;
\prompt 'Enter para continuar...' pausa

\echo
\echo '=== 4. VALIDACAO: verificacoes de integridade apos a carga (esperado: tudo 0) ==='
\i sql/postgres/04_validacao.sql
\prompt 'Enter para continuar...' pausa

\echo
\echo '=== 5. INTEGRIDADE NA PRATICA: o proprio banco recusa dados invalidos ==='
\echo '-- (a) valor negativo: viola o CHECK'
BEGIN;
INSERT INTO sinisa.resultado_indicador (cod_ibge, codigo_indicador, ano_referencia, valor) VALUES ('3550308', 'IRS3002', 2024, -5);
ROLLBACK;
\echo '-- (b) municipio que nao existe: viola a chave estrangeira'
BEGIN;
INSERT INTO sinisa.resultado_indicador (cod_ibge, codigo_indicador, ano_referencia, valor) VALUES ('9999999', 'IRS3002', 2024, 10);
ROLLBACK;
\echo '-- (c) resultado repetido: viola a restricao UNIQUE'
BEGIN;
INSERT INTO sinisa.resultado_indicador (cod_ibge, codigo_indicador, ano_referencia, valor) VALUES ('3550308', 'IRS3002', 2024, 10);
ROLLBACK;
\prompt 'Enter para continuar...' pausa

\echo
\echo '=== 6. USO NA ANALISE: a view junta as tabelas e calcula as estatisticas por UF ==='
\echo '-- Capital e ABC, indicadores em colunas (view vw_municipio_indicadores, que junta as 3 tabelas)'
SELECT nome_municipio, uf, populacao_total,
       round(irs0001_cobertura_coleta::numeric, 1)      AS cobertura_coleta,
       round(irs3002_disposicao_inadequada::numeric, 1) AS disposicao_inadequada
FROM sinisa.vw_municipio_indicadores
WHERE uf = 'SP' AND nome_municipio IN ('São Paulo', 'São Bernardo do Campo', 'Santo André')
ORDER BY populacao_total DESC;
\echo '-- Ranking das UFs com funcao de janela (media simples x ponderada pela populacao)'
SELECT uf, media_simples, media_ponderada, mediana,
       rank() OVER (ORDER BY media_simples DESC) AS posicao
FROM sinisa.vw_resumo_uf
ORDER BY posicao
LIMIT 5;
\prompt 'Enter para continuar...' pausa

\echo
\echo '=== 7. DESEMPENHO: o plano de execucao usa o indice por indicador ==='
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, BUFFERS OFF)
SELECT avg(valor) FROM sinisa.resultado_indicador WHERE codigo_indicador = 'IRS3002';
\prompt 'Enter para continuar...' pausa

\echo
\echo '=== 8. SEGURANCA: o usuario leitor_sinisa so consulta ==='
\c residuos_sinisa leitor_sinisa
SELECT count(*) AS leitura_permitida FROM sinisa.municipio;
DELETE FROM sinisa.municipio;
\c residuos_sinisa postgres
\prompt 'Enter para continuar...' pausa

\echo
\echo '=== 9. ARMAZENAMENTO FISICO: onde os dados ficam e o que e um tablespace ==='
\echo '-- Tablespaces existentes: so os dois que o PostgreSQL ja cria (nos nao criamos nenhum)'
\db
\echo '-- Tablespace de cada tabela e indice do projeto: todos no padrao (pg_default)'
SELECT c.relname AS objeto,
       CASE c.relkind WHEN 'r' THEN 'tabela' ELSE 'indice' END AS tipo,
       coalesce(t.spcname, 'pg_default') AS tablespace
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_tablespace t ON t.oid = c.reltablespace
WHERE n.nspname = 'sinisa' AND c.relkind IN ('r', 'i')
ORDER BY c.relkind DESC, c.relname;
\echo '-- Cada tabela e um arquivo dentro da pasta de dados, gravado em paginas de 8 KB'
SELECT pg_relation_filepath('sinisa.resultado_indicador') AS arquivo_da_tabela_fato,
       current_setting('data_directory')                 AS pasta_de_dados,
       current_setting('block_size')                     AS bytes_por_pagina;
\echo '-- Quanto espaco o banco ocupa'
SELECT pg_size_pretty(pg_database_size('residuos_sinisa'))             AS banco_inteiro,
       pg_size_pretty(pg_table_size('sinisa.resultado_indicador'))     AS tabela_fato,
       pg_size_pretty(pg_indexes_size('sinisa.resultado_indicador'))   AS indices_da_fato,
       pg_size_pretty(pg_total_relation_size('staging.stg_planilha'))  AS staging;
-- Se fosse um banco grande, o passo seguinte seria (NAO executamos aqui):
--   CREATE TABLESPACE ts_rapido LOCATION 'D:/pgdados/rapido';      -- pasta vazia, em outro disco
--   ALTER INDEX sinisa.idx_resultado_indicador SET TABLESPACE ts_rapido;
\echo
\echo '=== Fim da demonstracao ==='
