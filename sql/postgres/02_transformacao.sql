-- =============================================================================
-- 02_transformacao.sql (PostgreSQL)  |  Limpeza e carga: staging -> sinisa
--
-- Pressupõe que o catálogo sinisa.indicador já foi carregado e que
-- staging.stg_planilha contém a planilha extraída (feito por scripts/etl_postgres.py).
--
-- Regras de limpeza (as mesmas do ETL em SQLite, agora aplicadas dentro do banco):
--   1. Código IBGE: tira espaços e a parte decimal ("3548708.0" -> "3548708");
--      linhas sem código de 7 dígitos são descartadas; duplicatas ficam com a 1ª.
--   2. Texto: trim; UF em maiúsculas; "respondeu" vira booleano ('Sim' -> true).
--   3. População: texto numérico vira inteiro.
--   4. Indicadores: só valores numéricos entram; "null", vazio e traço são descartados.
--   5. Qualidade: valores suspeitos recebem flag_qualidade, mas NÃO são removidos.
-- =============================================================================

TRUNCATE sinisa.resultado_indicador RESTART IDENTITY;
DELETE FROM sinisa.municipio;

-- 1) Dimensão município ---------------------------------------------------------
INSERT INTO sinisa.municipio (cod_ibge, nome_municipio, uf, regiao, populacao_total, respondeu)
SELECT DISTINCT ON (c.cod)
       c.cod,
       trim(s.nom_mun),
       upper(trim(s.uf)),
       NULLIF(trim(s.nom_regiao), ''),
       NULLIF(split_part(trim(s.dfe0001), '.', 1), '')::integer,
       lower(trim(s.respondeu)) = 'sim'
FROM staging.stg_planilha AS s
CROSS JOIN LATERAL (SELECT NULLIF(split_part(trim(s.cod_ibge), '.', 1), '') AS cod) AS c
WHERE c.cod ~ '^[0-9]{7}$'
ORDER BY c.cod, s.linha_origem;

-- 2) Fato: despivota as 6 colunas de indicadores em linhas -----------------------
INSERT INTO sinisa.resultado_indicador (cod_ibge, codigo_indicador, ano_referencia, valor, flag_qualidade)
SELECT m.cod_ibge,
       v.codigo,
       s.ano_referencia,
       v.valor,
       CASE
           WHEN v.codigo = 'IRS1004' AND v.valor > 3   THEN 'MASSA_PER_CAPITA_ALTA'
           WHEN i.unidade = 'Percentual' AND v.valor > 100 THEN 'PERCENTUAL_ACIMA_100'
       END
FROM (
    SELECT DISTINCT ON (split_part(trim(cod_ibge), '.', 1)) *
    FROM staging.stg_planilha
    ORDER BY split_part(trim(cod_ibge), '.', 1), linha_origem
) AS s
JOIN sinisa.municipio AS m ON m.cod_ibge = split_part(trim(s.cod_ibge), '.', 1)
CROSS JOIN LATERAL (
    SELECT u.codigo, u.texto::double precision AS valor
    FROM (VALUES ('IRS0001', s.irs0001), ('IRS0005', s.irs0005), ('IRS1004', s.irs1004),
                 ('IRS3001', s.irs3001), ('IRS3002', s.irs3002), ('IRS3010', s.irs3010)) AS u(codigo, texto)
    WHERE trim(u.texto) ~ '^[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$'
) AS v
JOIN sinisa.indicador AS i ON i.codigo = v.codigo;

ANALYZE sinisa.municipio;
ANALYZE sinisa.resultado_indicador;
