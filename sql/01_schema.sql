-- =============================================================================
-- 01_schema.sql  |  Esquema do banco de dados (SQLite 3)
--
-- Projeto de Extensão do 4º semestre - FATEC São Bernardo do Campo
-- MPV: Análise e Diagnóstico da Gestão de Resíduos Sólidos
--
-- Fonte dos dados: Ministério das Cidades / SINISA 2025 (ano de referência
-- 2024), planilha de indicadores municipais de resíduos sólidos urbanos.
--
-- Modelo: esquema estrela simplificado (modelo dimensional).
--   * Dimensões: municipio e indicador
--   * Fato:      resultado_indicador (um valor por município x indicador x ano)
--
-- Observação de modelagem: em um esquema estrela as dimensões são mantidas
-- desnormalizadas de propósito. Por isso a coluna "regiao" fica em municipio,
-- embora dependa de "uf".
--
-- Este arquivo é executado automaticamente por scripts/etl_sqlite.py e recria
-- o banco do zero (os DROP abaixo apagam os dados anteriores).
-- =============================================================================

PRAGMA foreign_keys = ON;

-- Remoção na ordem inversa das dependências (fato primeiro, dimensões depois)
DROP TABLE IF EXISTS destinacao_municipio;
DROP TABLE IF EXISTS resultado_indicador;
DROP TABLE IF EXISTS indicador;
DROP TABLE IF EXISTS municipio;


-- -----------------------------------------------------------------------------
-- Dimensão: municipio
-- Contém TODOS os municípios da planilha, inclusive os que não responderam ao
-- módulo de resíduos (respondeu = 0). Esses não possuem linhas na tabela fato.
-- -----------------------------------------------------------------------------
CREATE TABLE municipio (
    cod_ibge         TEXT    PRIMARY KEY,                 -- código IBGE (7 dígitos)
    nome_municipio   TEXT    NOT NULL,
    uf               TEXT    NOT NULL,                    -- sigla do estado
    regiao           TEXT,                                -- macrorregião do país
    populacao_total  INTEGER,                             -- DFE0001 (usada nas médias ponderadas)
    respondeu        INTEGER NOT NULL
                     CHECK (respondeu IN (0, 1))          -- 1 = respondeu ao módulo de resíduos
);


-- -----------------------------------------------------------------------------
-- Dimensão: indicador (catálogo dos indicadores utilizados no projeto)
-- Nomes, unidades e grupos conforme o Glossário de Indicadores do SINISA 2025.
-- -----------------------------------------------------------------------------
CREATE TABLE indicador (
    codigo     TEXT PRIMARY KEY,                          -- ex.: IRS3002
    nome       TEXT NOT NULL,
    unidade    TEXT,                                      -- Percentual ou Kg/hab.dia
    grupo      TEXT,                                      -- Cobertura, Operacional ou Qualidade
    definicao  TEXT                                       -- fórmula resumida (códigos GTR/DFE)
);


-- -----------------------------------------------------------------------------
-- Fato: resultado_indicador
-- Só existem linhas para municípios respondentes com valor numérico válido.
--
-- flag_qualidade sinaliza, sem apagar, valores que merecem cautela na análise:
--   PERCENTUAL_ACIMA_100   indicador percentual com valor acima de 100
--   MASSA_PER_CAPITA_ALTA  IRS1004 acima do limite definido no ETL
-- Valor NULL = nenhum problema detectado pelas regras acima.
-- -----------------------------------------------------------------------------
CREATE TABLE resultado_indicador (
    id_resultado      INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_ibge          TEXT    NOT NULL,
    codigo_indicador  TEXT    NOT NULL,
    ano_referencia    INTEGER NOT NULL,
    valor             REAL,
    flag_qualidade    TEXT
                      CHECK (flag_qualidade IS NULL OR flag_qualidade IN
                             ('PERCENTUAL_ACIMA_100', 'MASSA_PER_CAPITA_ALTA')),
    FOREIGN KEY (cod_ibge)         REFERENCES municipio (cod_ibge),
    FOREIGN KEY (codigo_indicador) REFERENCES indicador (codigo),
    UNIQUE (cod_ibge, codigo_indicador, ano_referencia)
);


-- -----------------------------------------------------------------------------
-- destinacao_municipio: unidades de disposição final EM OPERAÇÃO sediadas no
-- município (planilha SINISA de Infraestrutura - Destinação Final). Um registro por
-- município da dimensão, com zeros quando não sedia nenhuma unidade.
-- Uso: evidência para interpretar IRS3002 = 0. Sedia aterro sanitário em operação =
-- destinação adequada comprovada; não sedia unidade nenhuma = o zero não se confirma
-- (pode enviar a outro município ou não ter informado). Inadequada = lixão, vazadouro
-- ou aterro controlado (mesma definição do IRS3002).
-- -----------------------------------------------------------------------------
CREATE TABLE destinacao_municipio (
    cod_ibge                       TEXT    PRIMARY KEY,
    unidades_inadequadas_operacao  INTEGER NOT NULL CHECK (unidades_inadequadas_operacao >= 0),
    aterros_sanitarios_operacao    INTEGER NOT NULL CHECK (aterros_sanitarios_operacao >= 0),
    aterros_inertes_operacao       INTEGER NOT NULL CHECK (aterros_inertes_operacao >= 0),
    FOREIGN KEY (cod_ibge) REFERENCES municipio (cod_ibge)
);


-- -----------------------------------------------------------------------------
-- Índices de apoio às consultas (filtro por UF e por indicador)
-- A busca por cod_ibge já é atendida pelo índice da restrição UNIQUE
-- (cod_ibge, codigo_indicador, ano_referencia), que começa por essa coluna.
-- -----------------------------------------------------------------------------
CREATE INDEX idx_municipio_uf          ON municipio (uf);
CREATE INDEX idx_resultado_indicador   ON resultado_indicador (codigo_indicador);
