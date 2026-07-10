-- Fixture chico para el pipeline de ML en CI/local.
--
-- No reemplaza el ETL real (extract -> bronze -> silver -> gold via dbt):
-- crea directamente las tablas gold minimas que consume
-- feature_store.repository.read_source_frames, con dos pozos y 13 meses
-- de historia. Suficiente para build_features -> train -> promotion_gate
-- sin bajar los datasets grandes de datos.energia.gob.ar.
--
-- ATENCION: hace DROP + CREATE de gold.fact_produccion_pozo y
-- gold.dim_pozo. postgres-init/01_metadata_tables.sql ya crea versiones
-- placeholder de esas tablas (para que dbt las reemplace con `dbt run`),
-- asi que CREATE TABLE IF NOT EXISTS no alcanza. Si corres esto contra un
-- warehouse con datos reales de dbt, hace falta un `dbt run` despues para
-- restaurar las tablas gold reales.

CREATE SCHEMA IF NOT EXISTS gold;

DROP TABLE IF EXISTS gold.fact_produccion_pozo;
DROP TABLE IF EXISTS gold.dim_pozo;

CREATE TABLE gold.fact_produccion_pozo (
    idpozo TEXT NOT NULL,
    fecha_mes DATE NOT NULL,
    prod_pet NUMERIC
);

CREATE TABLE gold.dim_pozo (
    idpozo TEXT PRIMARY KEY,
    cuenca TEXT,
    provincia TEXT,
    clasificacion TEXT,
    tipo_reservorio TEXT
);

INSERT INTO gold.dim_pozo (idpozo, cuenca, provincia, clasificacion, tipo_reservorio)
VALUES
    ('POZO-001', 'NEUQUINA', 'NEUQUEN', 'EXPLOTACION', 'SHALE'),
    ('POZO-002', 'NEUQUINA', 'NEUQUEN', 'EXPLOTACION', 'SHALE');

-- 13 meses (2025-01 a 2026-01) por pozo, con una senal alternante:
-- lag_2 anticipa bien el valor actual y el baseline naive lag_1 queda
-- deliberadamente debil. Esto hace deterministico el bootstrap del gate
-- sin agrandar el fixture.
INSERT INTO gold.fact_produccion_pozo (idpozo, fecha_mes, prod_pet)
SELECT
    pozo.idpozo,
    (DATE '2025-01-01' + (month_offset || ' months')::interval)::date AS fecha_mes,
    (
        CASE
            WHEN month_offset % 2 = 0 THEN pozo.high_value
            ELSE pozo.low_value
        END
    )::numeric AS prod_pet
FROM generate_series(0, 12) AS month_offset
CROSS JOIN (
    VALUES ('POZO-001', 180.0, 90.0), ('POZO-002', 140.0, 70.0)
) AS pozo(idpozo, high_value, low_value);
