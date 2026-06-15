# Data Contracts - Fase 2

Este documento define el contrato minimo de datos para la Adenda 2. No reemplaza a dbt ni a los tests de calidad: sirve para que el equipo sepa que tablas existen, quien las consume y que reglas no se deberian romper antes de entregar.

---

## 1. Stack base

| Componente | Decision |
|---|---|
| Warehouse | PostgreSQL local/sandbox |
| Orquestacion | Dagster con assets definidos como codigo |
| Transformacion | dbt |
| BI | Metabase |
| Calidad | Checks propios persistidos en `quality.data_quality_results` + tests dbt |
| Governance | DataHub como catalogo externo + dbt Docs, contratos, metadata y quality persistida |

---

## 2. Schemas del warehouse

| Schema | Uso |
|---|---|
| `bronze` | Datos crudos o casi crudos, con evidencia de fuente y corrida. |
| `silver` | Datos limpios, tipados, normalizados y deduplicados. |
| `gold` | Modelo estrella listo para analisis y BI. |
| `quality` | Resultados persistidos de checks. |
| `metadata` | Corridas, fuentes, hashes, timestamps y estado. |
| `semantic` | Vistas logicas con metricas oficiales para consumo. |

---

## 3. Datasets esperados

### Bronze

- `bronze.raw_produccion_no_convencional`
- `bronze.raw_pozos_operadoras`

Contrato:

- conservar payload crudo o equivalente auditable;
- conservar metadata de corrida;
- no limpiar agresivamente;
- permitir volver a la fuente/hash/run.

Metadata obligatoria:

- `_run_id`
- `_source_name`
- `_source_url`
- `_source_file_hash`
- `_ingested_at`
- `_raw_row_number`

### Silver

- `silver.produccion_no_convencional`
- `silver.pozos_operadoras`

Contrato:

- tipos normalizados;
- fechas validas cuando aplique;
- claves principales conservadas;
- metadata de origen conservada;
- no mezclar logica de dashboard.

### Gold

- `gold.fact_produccion_pozo`
- `gold.dim_pozo`
- `gold.dim_fecha`
- `gold.dim_operadora`
- `gold.dim_area`
- `gold.dim_yacimiento`

Contrato:

- `gold.fact_produccion_pozo` tiene grano mensual por pozo/registro de produccion;
- las dimensiones se usan para BI y analisis;
- se usan surrogate keys donde aplica;
- SCD tipo 1 para dimensiones mutables por alcance academico.

### Quality

- `quality.data_quality_results`

Contrato:

- todo check relevante debe dejar resultado persistido;
- los checks criticos deben poder fallar el pipeline;
- warnings quedan visibles sin necesariamente bloquear.

### Metadata

- `metadata.pipeline_runs`
- `metadata.source_files`

Contrato:

- registrar corrida, fuente, hash, filas cargadas y timestamps;
- permitir explicar que version de fuente alimento una capa downstream.

### Semantic

- `semantic.vw_produccion_mensual`
- `semantic.vw_produccion_por_operadora`
- `semantic.vw_produccion_por_area`
- `semantic.vw_frescura_datos`

Contrato:

- exponer metricas de negocio ya agregadas;
- ser la fuente principal para Metabase;
- evitar que usuarios BI consulten Bronze.

---

## 4. Estrategia de carga

La estrategia aceptada esta en [ADR 0007](adr/0007-definir-estrategia-de-carga-y-backfill.md):

- full download de CSV publico en cada corrida;
- hash de archivo completo;
- Bronze append-only por corrida nueva;
- si el hash ya fue cargado, no se duplica esa fuente;
- dbt reconstruye modelos downstream de forma idempotente.

No hay CDC real ni incremental por fila porque la fuente publica no ofrece `updated_at` o endpoint incremental confiable.

Backfill/reprocesamiento:

- Para esta fuente, el reprocesamiento sirve principalmente para reconstruir Silver/Gold/Semantic ante cambios de modelos o correcciones.
- `scripts/backfill.sh` recibe una fecha o rango como intencion operativa, pero por las limitaciones de la fuente descarga el CSV completo disponible y reconstruye downstream.
- No se promete reprocesamiento historico fino por particion: el alcance defendible es reproceso batch completo, idempotente y verificable.

---

## 5. Calidad de datos

Checks minimos esperados:

| Dimension | Ejemplos | Severidad esperada |
|---|---|---|
| Schema | columnas esperadas existen | Critical |
| Completeness | claves/fechas principales no nulas | Critical |
| Uniqueness | grano o surrogate keys sin duplicados | Critical |
| Relationships / lineage | fact con dimensiones relacionadas, metadata no nula | Critical |
| Freshness | ultimo periodo/fuente dentro de umbral definido | Warning |

Consecuencia operativa:

- si falla un critical, el quality gate debe devolver exit code distinto de cero;
- el resultado debe quedar en `quality.data_quality_results`;
- el dashboard o la validacion final deben poder mostrar el estado de calidad.

---

## 6. BI

Metabase debe consumir:

- vistas `semantic.*`;
- `quality.data_quality_results` para estado de calidad.

No consumir Bronze desde BI. Bronze es evidencia de ingesta, no capa de consumo.

Dashboard esperado:

- produccion mensual;
- produccion por operadora;
- produccion por area/yacimiento;
- pozos con produccion;
- frescura de datos;
- estado de calidad.

---

## 7. Governance y DataHub

La consigna pide plataforma de gobierno y lineage. La entrega cubre ese eje con DataHub como catalogo externo del warehouse, complementado por dbt Docs, metadata operacional y resultados de calidad persistidos.

Evidencia esperada en DataHub:

- datasets de los schemas `bronze`, `silver`, `gold`, `quality`, `metadata` y `semantic`;
- columnas y tipos de tablas clave;
- navegacion del catalogo por capas;
- detalle de `gold.fact_produccion_pozo`.

dbt Docs y Dagster complementan la demo para explicar linaje tecnico del pipeline. No decir "governance enterprise". El alcance defendible es gobierno de datos academico: descubrimiento, metadata tecnica, lineage y calidad.

---

## 8. Puertos y variables

Puertos principales:

- API FastAPI: `8000`
- Grafana: `3000`
- Metabase: `3001`
- Dagster: `3002`
- Alertmanager: `9093`
- Prometheus: `9090`
- cAdvisor: `8080`
- DataHub: `9002` en EC2 dedicada, por fuera del Compose principal
- Postgres: `5432` interno / `5433` desde host

Variables minimas:

```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=warehouse
POSTGRES_USER=dwh
POSTGRES_PASSWORD=dwh
PRODUCCION_SOURCE_URL=<url_csv_produccion>
POZOS_SOURCE_URL=<url_csv_pozos>
DATA_PIPELINE_RETRIES=3
DATA_PIPELINE_RETRY_BACKOFF_SECONDS=30
METABASE_ADMIN_EMAIL=martinbianchi@udesa.edu.ar
METABASE_ADMIN_PASSWORD=Admin1234!
```

Atencion: desde la maquina host se usa `POSTGRES_HOST=localhost` y `POSTGRES_PORT=5433`. Desde contenedores se usa `postgres:5432`.

---

## 9. Reglas de integracion

- No definir Gold sin mirar headers reales.
- No inventar columnas que no existen en la fuente.
- No promover a consumo si falla un check critico sin explicarlo.
- No dejar queries de negocio escondidas solo en Metabase si se pueden versionar como vistas semantic.
- No documentar como productivo algo que solo es sandbox.
- Si cambia una parte del pipeline, actualizar README, ADR/runbook afectado y checklist de validacion.
