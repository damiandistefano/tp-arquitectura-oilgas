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

-- 13 meses (2025-01 a 2026-01) por pozo, con una tendencia simple para
-- que el modelo tenga algo que aprender por encima del baseline naive.
INSERT INTO gold.fact_produccion_pozo (idpozo, fecha_mes, prod_pet)
SELECT
    pozo.idpozo,
    (DATE '2025-01-01' + (month_offset || ' months')::interval)::date AS fecha_mes,
    (pozo.base + month_offset * pozo.trend)::numeric AS prod_pet
FROM generate_series(0, 12) AS month_offset
CROSS JOIN (
    VALUES ('POZO-001', 100.0, 3.0), ('POZO-002', 80.0, 2.0)
) AS pozo(idpozo, base, trend);
