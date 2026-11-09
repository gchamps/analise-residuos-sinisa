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
DROP TABLE IF EXISTS etl_meta;
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
-- destinacao_municipio: massa coletada nas rotas declaradas pelo município (SINISA,
-- planilha de Manejo, aba de rotas; GTR1008), somada por classe do tipo de unidade de
-- destino (GTR1011), mais a massa coletada e a recuperada do município (GTR1028 e
-- GTR1029). Uma linha por município da dimensão, com zeros quando não há rota declarada.
-- Massas em toneladas por ano.
--
-- Classes: inadequada = lixão, vazadouro ou aterro controlado; aterro_adequado = aterro
-- sanitário ou de inertes; intermediaria = transbordo, triagem, compostagem,
-- coprocessamento, áreas verdes (o destino final não é informado na rota).
--
-- O IRS3002 é, exatamente, massa_rota_inadequada / (massa_coletada - massa_recuperada) x 100.
-- O ETL confere isso para todos os municípios. Logo, esta tabela explica o indicador a partir
-- da mesma declaração: não é uma verificação independente.
-- -----------------------------------------------------------------------------
CREATE TABLE destinacao_municipio (
    cod_ibge                    TEXT PRIMARY KEY,
    massa_rota_inadequada       REAL NOT NULL CHECK (massa_rota_inadequada >= 0),
    massa_rota_aterro_adequado  REAL NOT NULL CHECK (massa_rota_aterro_adequado >= 0),
    massa_rota_intermediaria    REAL NOT NULL CHECK (massa_rota_intermediaria >= 0),
    massa_coletada              REAL,                     -- GTR1028 (NULL se não informada)
    massa_recuperada            REAL,                     -- GTR1029 (NULL se não informada)
    FOREIGN KEY (cod_ibge) REFERENCES municipio (cod_ibge)
);


-- -----------------------------------------------------------------------------
-- etl_meta: metadados da carga. 'hash_entradas' é a impressão digital das planilhas,
-- do esquema e do ETL; o ETL a usa para pular a execução quando nada mudou.
-- -----------------------------------------------------------------------------
CREATE TABLE etl_meta (
    chave  TEXT PRIMARY KEY,
    valor  TEXT NOT NULL
);


-- -----------------------------------------------------------------------------
-- Índices de apoio às consultas (filtro por UF e por indicador)
-- A busca por cod_ibge já é atendida pelo índice da restrição UNIQUE
-- (cod_ibge, codigo_indicador, ano_referencia), que começa por essa coluna.
-- -----------------------------------------------------------------------------
CREATE INDEX idx_municipio_uf          ON municipio (uf);
CREATE INDEX idx_resultado_indicador   ON resultado_indicador (codigo_indicador);
