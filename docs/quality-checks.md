# Calidad de datos

Los checks de calidad se persisten en la tabla quality.data_quality_results.

## Tabla de resultados

Campos principales:
- check_id
- run_id
- layer
- table_name
- check_name
- dimension
- status
- severity
- rows_checked
- rows_failed
- details
- executed_at

## Estados

- PASS: el check pasó.
- WARNING: hay un problema no crítico.
- FAILED: hay un problema crítico.

## Severidades

- CRITICAL: si falla, el pipeline debe cortar.
- WARNING: se registra el problema, pero no bloquea la ejecución.

## Checks implementados

### Schema
Valida que existan columnas esperadas en tablas clave.

Check:
- expected_columns_exist

Severidad:
- CRITICAL

### Completeness
Valida que campos críticos de gold.fact_produccion_pozo no sean nulos.

Campos:
- produccion_id
- pozo_id
- fecha_mes
- operadora_id

Severidad:
- CRITICAL

### Uniqueness
Valida que produccion_id sea único en gold.fact_produccion_pozo.

Check:
- produccion_id_unique

Severidad:
- CRITICAL

### Lineage
Valida que la fact table conserve metadata de origen.

Campos:
- _run_id
- _source_file_hash

Severidad:
- CRITICAL

### Relaciones fact-dimensiones
Valida que la fact tenga relación con dim_pozo, dim_fecha y dim_operadora.

Check:
- fact_has_matching_dimensions

Severidad:
- CRITICAL

### Freshness
Valida que el último período disponible no sea demasiado viejo.

Check:
- latest_period_not_too_old

Severidad:
- WARNING

## Consecuencia operativa

El script se ejecuta con:

    bash scripts/run-quality-checks.sh

Si falla un check crítico, el script termina con exit code distinto de cero.
Esto permite que un orquestador como Airflow marque la tarea como fallida.

Si solo hay warnings, los resultados quedan persistidos pero la ejecución puede continuar.
