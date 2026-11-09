-- =============================================================================
-- 01_schema.sql (PostgreSQL)  |  Esquema do banco "residuos_sinisa"
--
-- Projeto de Extensão do 4º semestre - FATEC São Bernardo do Campo
-- MPV: Análise e Diagnóstico da Gestão de Resíduos Sólidos
--
-- Fonte: Ministério das Cidades, SINISA 2025 (ano de referência 2024).
--
-- Organização em dois schemas:
--   staging  área de pouso: cópia fiel (tudo texto) da planilha extraída.
--            Serve para auditar a carga e para limpar com SQL, sem tocar na origem.
--   sinisa   modelo final, esquema estrela (dimensões município e indicador;
--            fato resultado_indicador), com tipos, chaves e restrições.
--
-- Este script recria os dois schemas do zero (DROP ... CASCADE).
-- Ordem de execução: 01_schema.sql -> carga do staging (ETL Python) ->
-- 02_transformacao.sql -> 03_views_e_consultas.sql -> 04_validacao.sql
-- =============================================================================

DROP SCHEMA IF EXISTS staging CASCADE;
DROP SCHEMA IF EXISTS sinisa  CASCADE;
CREATE SCHEMA staging;
CREATE SCHEMA sinisa;

COMMENT ON SCHEMA staging IS 'Área de pouso: dados extraídos da planilha, ainda sem tratamento (todas as colunas em texto).';
COMMENT ON SCHEMA sinisa  IS 'Modelo final em esquema estrela, com tipos e restrições de integridade.';


-- -----------------------------------------------------------------------------
-- STAGING: espelho da planilha. Colunas em texto de propósito: a limpeza e a
-- conversão de tipos acontecem na etapa de transformação, de forma auditável.
-- -----------------------------------------------------------------------------
CREATE TABLE staging.stg_planilha (
    linha_origem    INTEGER,            -- posição da linha na planilha (rastreabilidade)
    cod_ibge        TEXT,
    nom_mun         TEXT,
    uf              TEXT,
    nom_regiao      TEXT,
    dfe0001         TEXT,               -- população total
    respondeu       TEXT,               -- 'Sim' / 'Não'
    irs0001         TEXT,
    irs0005         TEXT,
    irs1004         TEXT,
    irs3001         TEXT,
    irs3002         TEXT,
    irs3010         TEXT,
    ano_referencia  SMALLINT NOT NULL,
    carregado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE staging.stg_planilha IS 'Uma linha por município da planilha de indicadores do SINISA, como extraída.';


-- -----------------------------------------------------------------------------
-- Dimensão: municipio
-- Todos os municípios da planilha, inclusive os que não responderam ao módulo
-- de resíduos (respondeu = false). Esses não têm linhas na tabela fato.
-- -----------------------------------------------------------------------------
CREATE TABLE sinisa.municipio (
    cod_ibge         CHAR(7)      NOT NULL,
    nome_municipio   VARCHAR(100) NOT NULL,
    uf               CHAR(2)      NOT NULL,
    regiao           VARCHAR(20),
    populacao_total  INTEGER,
    respondeu        BOOLEAN      NOT NULL,
    CONSTRAINT pk_municipio        PRIMARY KEY (cod_ibge),
    CONSTRAINT ck_municipio_ibge   CHECK (cod_ibge ~ '^[0-9]{7}$'),
    CONSTRAINT ck_municipio_uf     CHECK (uf ~ '^[A-Z]{2}$'),
    CONSTRAINT ck_municipio_regiao CHECK (regiao IN ('Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul')),
    CONSTRAINT ck_municipio_pop    CHECK (populacao_total >= 0)
);
COMMENT ON TABLE  sinisa.municipio IS 'Dimensão município (código IBGE, UF, região, população, se respondeu ao módulo de resíduos).';
COMMENT ON COLUMN sinisa.municipio.cod_ibge        IS 'Código IBGE do município, 7 dígitos (chave primária).';
COMMENT ON COLUMN sinisa.municipio.populacao_total IS 'DFE0001: população total residente; peso das médias ponderadas.';
COMMENT ON COLUMN sinisa.municipio.respondeu       IS 'true se o município respondeu ao módulo de resíduos do SINISA.';


-- -----------------------------------------------------------------------------
-- Dimensão: indicador (catálogo; nomes e unidades do Glossário SINISA 2025)
-- -----------------------------------------------------------------------------
CREATE TABLE sinisa.indicador (
    codigo     VARCHAR(10)  NOT NULL,
    nome       VARCHAR(200) NOT NULL,
    unidade    VARCHAR(20)  NOT NULL,
    grupo      VARCHAR(20)  NOT NULL,
    definicao  TEXT,
    CONSTRAINT pk_indicador         PRIMARY KEY (codigo),
    CONSTRAINT ck_indicador_unidade CHECK (unidade IN ('Percentual', 'Kg/hab.dia')),
    CONSTRAINT ck_indicador_grupo   CHECK (grupo IN ('Cobertura', 'Operacional', 'Qualidade'))
);
COMMENT ON TABLE sinisa.indicador IS 'Catálogo dos indicadores usados no projeto (IRS0001, IRS0005, IRS1004, IRS3001, IRS3002, IRS3010).';


-- -----------------------------------------------------------------------------
-- Fato: resultado_indicador (um valor por município x indicador x ano)
-- Só existem linhas para municípios respondentes com valor numérico válido.
-- flag_qualidade marca, sem apagar, valores que pedem cautela na análise.
-- -----------------------------------------------------------------------------
CREATE TABLE sinisa.resultado_indicador (
    id_resultado      BIGINT   GENERATED ALWAYS AS IDENTITY,
    cod_ibge          CHAR(7)  NOT NULL,
    codigo_indicador  VARCHAR(10) NOT NULL,
    ano_referencia    SMALLINT NOT NULL,
    valor             DOUBLE PRECISION NOT NULL,
    flag_qualidade    VARCHAR(30),
    CONSTRAINT pk_resultado         PRIMARY KEY (id_resultado),
    CONSTRAINT fk_resultado_mun     FOREIGN KEY (cod_ibge)         REFERENCES sinisa.municipio (cod_ibge),
    CONSTRAINT fk_resultado_ind     FOREIGN KEY (codigo_indicador) REFERENCES sinisa.indicador (codigo),
    CONSTRAINT uq_resultado         UNIQUE (cod_ibge, codigo_indicador, ano_referencia),
    CONSTRAINT ck_resultado_ano     CHECK (ano_referencia BETWEEN 2000 AND 2100),
    CONSTRAINT ck_resultado_valor   CHECK (valor >= 0),
    CONSTRAINT ck_resultado_flag    CHECK (flag_qualidade IS NULL
                                           OR flag_qualidade IN ('PERCENTUAL_ACIMA_100', 'MASSA_PER_CAPITA_ALTA'))
);
COMMENT ON TABLE  sinisa.resultado_indicador IS 'Tabela fato: valor de cada indicador por município e ano de referência.';
COMMENT ON COLUMN sinisa.resultado_indicador.flag_qualidade IS
    'PERCENTUAL_ACIMA_100: percentual > 100. MASSA_PER_CAPITA_ALTA: IRS1004 > 3 kg/hab.dia. NULL: sem alerta.';


-- -----------------------------------------------------------------------------
-- Índices de apoio às consultas (filtro por UF, por indicador e por município)
-- -----------------------------------------------------------------------------
CREATE INDEX idx_municipio_uf        ON sinisa.municipio (uf);
CREATE INDEX idx_resultado_indicador ON sinisa.resultado_indicador (codigo_indicador);
CREATE INDEX idx_resultado_municipio ON sinisa.resultado_indicador (cod_ibge);
