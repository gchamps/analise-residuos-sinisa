-- =============================================================================
-- 03_views_e_consultas.sql (PostgreSQL)  |  Views analíticas, papel de leitura
--                                           e consultas de exemplo
-- =============================================================================

-- -----------------------------------------------------------------------------
-- View: um município por linha, indicadores em colunas (só respondentes)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW sinisa.vw_municipio_indicadores AS
SELECT m.cod_ibge,
       m.nome_municipio,
       m.uf,
       m.regiao,
       m.populacao_total,
       max(r.valor) FILTER (WHERE r.codigo_indicador = 'IRS0001') AS irs0001_cobertura_coleta,
       max(r.valor) FILTER (WHERE r.codigo_indicador = 'IRS0005') AS irs0005_cobertura_coleta_seletiva,
       max(r.valor) FILTER (WHERE r.codigo_indicador = 'IRS1004') AS irs1004_massa_per_capita,
       max(r.valor) FILTER (WHERE r.codigo_indicador = 'IRS3001') AS irs3001_desempenho_coleta_seletiva,
       max(r.valor) FILTER (WHERE r.codigo_indicador = 'IRS3002') AS irs3002_disposicao_inadequada,
       max(r.valor) FILTER (WHERE r.codigo_indicador = 'IRS3010') AS irs3010_recuperacao_reciclaveis
FROM sinisa.municipio AS m
JOIN sinisa.resultado_indicador AS r ON r.cod_ibge = m.cod_ibge
GROUP BY m.cod_ibge, m.nome_municipio, m.uf, m.regiao, m.populacao_total;
COMMENT ON VIEW sinisa.vw_municipio_indicadores IS 'Municípios respondentes com os 6 indicadores em colunas.';

-- -----------------------------------------------------------------------------
-- View: resumo por UF da disposição final inadequada (IRS3002):
-- média simples, média ponderada pela população e mediana
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW sinisa.vw_resumo_uf AS
SELECT uf,
       count(*)                                                            AS municipios_respondentes,
       round(avg(irs3002_disposicao_inadequada)::numeric, 2)               AS media_simples,
       round((sum(irs3002_disposicao_inadequada * populacao_total)
              / sum(populacao_total))::numeric, 2)                         AS media_ponderada,
       round((percentile_cont(0.5) WITHIN GROUP
              (ORDER BY irs3002_disposicao_inadequada))::numeric, 2)       AS mediana
FROM sinisa.vw_municipio_indicadores
WHERE irs3002_disposicao_inadequada IS NOT NULL
GROUP BY uf;
COMMENT ON VIEW sinisa.vw_resumo_uf IS 'IRS3002 por UF: média simples, ponderada por população e mediana.';

-- -----------------------------------------------------------------------------
-- View: o mesmo resumo por macrorregião
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW sinisa.vw_resumo_regiao AS
SELECT regiao,
       count(*)                                              AS municipios_respondentes,
       round(avg(irs3002_disposicao_inadequada)::numeric, 2) AS disposicao_inadequada_media,
       round(avg(irs0005_cobertura_coleta_seletiva)::numeric, 2) AS coleta_seletiva_media
FROM sinisa.vw_municipio_indicadores
WHERE irs3002_disposicao_inadequada IS NOT NULL
GROUP BY regiao;
COMMENT ON VIEW sinisa.vw_resumo_regiao IS 'Disposição inadequada e coleta seletiva médias por região.';

-- -----------------------------------------------------------------------------
-- Papel de leitura: quem só consulta (ex.: o dashboard) não precisa alterar dados
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'leitor_sinisa') THEN
        CREATE ROLE leitor_sinisa LOGIN;
    END IF;
END
$$;
GRANT USAGE ON SCHEMA sinisa TO leitor_sinisa;
GRANT SELECT ON ALL TABLES IN SCHEMA sinisa TO leitor_sinisa;

-- =============================================================================
-- CONSULTAS DE EXEMPLO (para a apresentação; não alteram dados)
-- =============================================================================

-- 1) Ranking das UFs pela média simples de disposição inadequada (1 = pior)
--    SELECT uf, media_simples, media_ponderada,
--           rank() OVER (ORDER BY media_simples DESC) AS posicao
--    FROM sinisa.vw_resumo_uf ORDER BY posicao;

-- 2) Municípios sinalizados pelas regras de qualidade, por indicador e tipo de alerta
--    SELECT codigo_indicador, flag_qualidade, count(*)
--    FROM sinisa.resultado_indicador
--    WHERE flag_qualidade IS NOT NULL
--    GROUP BY 1, 2 ORDER BY 1;

-- 3) Quantos municípios registram 0%, entre 1% e 99% e 100% de disposição inadequada
--    SELECT CASE WHEN valor = 0 THEN '0%' WHEN valor >= 100 THEN '100%' ELSE '1% a 99%' END AS situacao,
--           count(*)
--    FROM sinisa.resultado_indicador WHERE codigo_indicador = 'IRS3002'
--    GROUP BY 1 ORDER BY 1;

-- 4) Plano de execução: o índice por indicador é usado?
--    EXPLAIN ANALYZE
--    SELECT avg(valor) FROM sinisa.resultado_indicador WHERE codigo_indicador = 'IRS3002';
