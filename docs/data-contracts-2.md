# Data Contracts - Fase 2


## 1. Stack y supuestos base

- Warehouse local/sandbox: PostgreSQL.
- Orquestación: Dagster o equivalente, con DAGs definidos como código.
- Transformación: dbt.
- BI: Metabase.
- Gobierno de datos: DataHub.
- Estrategia general: arquitectura medallion con `bronze`, `silver`, `gold`, `quality`, `metadata` y `semantic`.

## 2. Schemas del warehouse

| Schema | Uso |
|---|---|
| `bronze` | Datos crudos o casi crudos, con evidencia de la fuente. |
| `silver` | Datos limpios, tipados, normalizados y deduplicados. |
| `gold` | Modelo estrella listo para BI y consumo analítico. |
| `quality` | Resultados persistidos de chequeos de calidad. |
| `metadata` | Corridas, fuentes, hashes, timestamps y estado del pipeline. |
| `semantic` | Vistas lógicas con métricas oficiales. Bonus. |

## 3. Tablas mínimas esperadas

### Bronze

- `bronze.raw_produccion_no_convencional`
- `bronze.raw_pozos_operadoras`

### Silver

- `silver.produccion_no_convencional`
- `silver.pozos_operadoras`

### Gold

- `gold.fact_produccion_pozo`
- `gold.dim_pozo`
- `gold.dim_fecha`
- `gold.dim_operadora`
- `gold.dim_area`
- `gold.dim_yacimiento`

### Quality

- `quality.data_quality_results`

### Metadata

- `metadata.pipeline_runs`
- `metadata.source_files`

### Semantic

- `semantic.vw_produccion_mensual`
- `semantic.vw_produccion_por_operadora`
- `semantic.vw_frescura_datos`

## 4. Metadata obligatoria en Bronze

Toda tabla Bronze debe conservar las columnas originales de la fuente y sumar, como mínimo:

- `_run_id`
- `_source_name`
- `_source_url`
- `_source_file_hash`
- `_ingested_at`
- `_raw_row_number`

Regla: Bronze no hace limpieza agresiva. Bronze guarda evidencia.

## 5. Estrategia de carga

### Extracción

- Full download del CSV público en cada corrida.
- Se valida que el archivo no esté vacío y que se puedan leer headers.

### Bronze

- Append-only por corrida.
- Cada carga conserva hash, timestamps y trazabilidad de origen.

### Silver

- Reconstrucción o upsert idempotente desde la última corrida válida.

### Gold

- Rebuild o upsert idempotente del modelo estrella.

### Backfill

- Debe permitir reprocesar una fecha o rango desde Bronze/Silver sin duplicar datos.

## 6. Grano y modelo de Gold

- `gold.fact_produccion_pozo`: una fila por pozo y período de producción.
- El período se define con los headers reales de la fuente, no por suposición.
- Si la fuente es mensual, el grano es pozo + mes.
- Si la fuente es diaria, el grano es pozo + día.

### Dimensiones esperadas

- `dim_fecha`: fecha, año, mes, trimestre.
- `dim_pozo`: identificador y atributos del pozo.
- `dim_operadora`: empresa operadora.
- `dim_area`: área.
- `dim_yacimiento`: yacimiento.

## 7. Surrogate keys y SCD

Se usarán surrogate keys en dimensiones cuando aplique:

- `sk_fecha`
- `sk_pozo`
- `sk_operadora`
- `sk_area`
- `sk_yacimiento`

Decisión inicial de SCD:

- `dim_fecha`: no aplica.
- `dim_operadora`: tipo 1.
- `dim_area`: tipo 1.
- `dim_yacimiento`: tipo 1.
- `dim_pozo`: tipo 1 inicialmente.

## 8. Calidad de datos

Los checks de calidad deben persistirse en `quality.data_quality_results`.

Checks mínimos:

- schema: columnas esperadas existen.
- completeness: campos clave no nulos.
- uniqueness: claves naturales sin duplicados.
- freshness: última ingesta dentro de umbral acordado.
- lineage: la tabla es trazable vía `_run_id` y metadata.

Fallo crítico esperado:

- schema inválido.
- id o clave natural nula.
- fecha nula.
- duplicados en clave natural.
- fact sin dimensión relacionada.

Consecuencia operativa mínima:

- el pipeline falla o bloquea la promoción aguas abajo,
- y queda un registro `FAILED` visible en `quality.data_quality_results`.

## 9. Puertos y variables de entorno

### Puertos sugeridos

- API FastAPI: `8000`
- Grafana: `3000`
- Metabase: `3001`
- Dagster: `3002`
- Alertmanager: `9093`
- Prometheus: `9090`
- Adminer: `8081`
- DataHub: `9002`
- Postgres warehouse: `5432` interno / `5433` host si hace falta

### Variables mínimas

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
METABASE_ADMIN_EMAIL=admin@demo.com
METABASE_ADMIN_PASSWORD=Admin1234!
```

## 10. Criterios de integración

- No se define Gold sin mirar headers reales.
- No se inventan columnas que no existan en la fuente.
- No se promueve a Gold si falla un check crítico.
- No se documenta como producción algo que solo es sandbox académico.

## 11. Qué debe actualizar cada integrante

- Integrante 1: extracción, Bronze, metadata, orquestación, backfill, stack base.
- Integrante 2: Silver, Gold, calidad persistida, BI, semantic layer si aplica.
- Integrante 3: README, ADR review, runbooks, DataHub, checklist final y validación documental.


