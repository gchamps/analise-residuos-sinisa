-- =============================================================================
-- 04_validacao.sql (PostgreSQL)  |  Verificações de integridade pós-carga
-- Cada linha devolvida é (verificacao, problemas). Esperado: problemas = 0.
-- =============================================================================

SELECT 'resultados de municípios que não responderam' AS verificacao, count(*) AS problemas
FROM sinisa.resultado_indicador r
JOIN sinisa.municipio m ON m.cod_ibge = r.cod_ibge
WHERE NOT m.respondeu
UNION ALL
SELECT 'municípios respondentes sem nenhum resultado', count(*)
FROM sinisa.municipio m
WHERE m.respondeu
  AND NOT EXISTS (SELECT 1 FROM sinisa.resultado_indicador r WHERE r.cod_ibge = m.cod_ibge)
UNION ALL
SELECT 'indicadores com número de municípios diferente do de respondentes', count(*)
FROM (
    SELECT i.codigo,
           count(DISTINCT r.cod_ibge) AS n,
           (SELECT count(*) FROM sinisa.municipio WHERE respondeu) AS esperado
    FROM sinisa.indicador i
    LEFT JOIN sinisa.resultado_indicador r ON r.codigo_indicador = i.codigo
    GROUP BY i.codigo
) AS t
WHERE n <> esperado
UNION ALL
SELECT 'linhas do staging sem município correspondente (código IBGE inválido ou duplicado)',
       (SELECT count(*) FROM staging.stg_planilha) - (SELECT count(*) FROM sinisa.municipio);
