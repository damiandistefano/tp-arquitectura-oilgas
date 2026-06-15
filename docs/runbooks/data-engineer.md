# Runbook: Operacion del pipeline de datos

Este runbook describe como correr y validar el pipeline de datos Oil & Gas: ingesta Bronze, transformaciones dbt, quality gate, backfill y recuperacion ante fallas.

Flujo general:

```text
CSV publicos
  -> bronze.raw_*
  -> silver.*
  -> gold.*
  -> quality.data_quality_results
  -> semantic.vw_*
  -> Metabase / dbt Docs / DataHub
```

---

## 1. Prerequisitos

- Docker Desktop o Docker Engine + Docker Compose.
- Python con dependencias del proyecto si se corre fuera de contenedores.
- Acceso a internet para descargar los CSVs publicos.
- `.env` creado desde `.env.example`.
- Postgres healthy.

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

---

## 2. Operacion con Dagster

Dagster es el camino recomendado para demostrar la orquestacion.

1. Abrir `http://localhost:3002`.
2. Ir a `Assets`.
3. Validar assets:
   - `extract_to_bronze`
   - `run_silver_transformations`
   - `run_quality_checks`
4. Materializar el pipeline.
5. Revisar logs de cada asset.

Una corrida exitosa debe dejar:

- fuentes registradas en `metadata.source_files`;
- tablas Bronze con filas;
- modelos dbt construidos en Silver, Gold y Semantic;
- resultados en `quality.data_quality_results`;
- cero fallas criticas sin explicar.

---

## 3. Operacion por comandos

### 3.1 Ingesta Bronze

```bash
bash scripts/run-data-pipeline.sh
```

Equivalente directo:

```bash
python -m extract.load_to_bronze
```

### 3.2 Transformaciones dbt

```bash
dbt build --project-dir dbt
```

Para generar documentacion:

```bash
dbt docs generate --project-dir dbt
dbt docs serve --project-dir dbt
```

### 3.3 Quality gate

```bash
bash scripts/run-quality-checks.sh
```

Equivalente directo:

```bash
python -m quality.checks
```

---

## 4. Smoke test de datos

Con el stack levantado y el pipeline corrido:

```bash
bash scripts/data-smoke.sh
```

Este smoke valida:

- existencia de schemas `bronze`, `silver`, `gold`, `quality`, `metadata`, `semantic`;
- filas en tablas principales;
- filas en vistas semantic;
- resultados persistidos de calidad;
- ausencia de fallas criticas.

---

## 5. Consultas de control

### Conteos por capa

```bash
docker compose exec -T postgres psql -U dwh -d warehouse -c "
  select 'bronze.raw_produccion_no_convencional' as objeto, count(*) from bronze.raw_produccion_no_convencional
  union all
  select 'bronze.raw_pozos_operadoras', count(*) from bronze.raw_pozos_operadoras
  union all
  select 'silver.produccion_no_convencional', count(*) from silver.produccion_no_convencional
  union all
  select 'gold.fact_produccion_pozo', count(*) from gold.fact_produccion_pozo
  union all
  select 'semantic.vw_produccion_mensual', count(*) from semantic.vw_produccion_mensual;
"
```

### Calidad reciente

```bash
docker compose exec -T postgres psql -U dwh -d warehouse -c "
  select check_name, layer, table_name, status, severity, executed_at
  from quality.data_quality_results
  order by executed_at desc
  limit 20;
"
```

### Fuentes cargadas

```bash
docker compose exec -T postgres psql -U dwh -d warehouse -c "
  select source_name, rows_loaded, source_file_hash, ingested_at
  from metadata.source_files
  order by ingested_at desc;
"
```

---

## 6. Backfill y reprocesamiento

El proyecto usa full download de CSVs publicos. Por eso el backfill no recupera una particion incremental desde una fuente transaccional: fuerza una nueva corrida de ingesta y reconstruye modelos downstream para todos los periodos disponibles.

```bash
bash scripts/backfill.sh 2025-01-01 2025-03-31
```

El rango se registra como intencion operativa, pero la fuente disponible se descarga completa. Este comportamiento esta alineado con [ADR 0007](../adr/0007-definir-estrategia-de-carga-y-backfill.md).

---

## 7. Recuperacion ante fallas

### Falla la descarga o la carga Bronze

1. Revisar conectividad a los CSVs publicos.
2. Reintentar `bash scripts/run-data-pipeline.sh`.
3. Verificar `metadata.pipeline_runs` y `metadata.source_files`.

La ingesta evita duplicar una fuente si el hash ya fue cargado.

### Falla dbt

1. Revisar el modelo que falla.
2. Ejecutar:

```bash
dbt debug --project-dir dbt
dbt build --project-dir dbt
```

3. Si cambia un modelo, volver a correr quality checks.

### Falla calidad

1. Consultar `quality.data_quality_results`.
2. Si el check es `CRITICAL`, no considerar exitosa la corrida hasta explicar o corregir la causa.
3. Reprocesar desde dbt o desde Bronze segun corresponda.

---

## 8. Validacion final para demo

- Dagster muestra una corrida exitosa.
- `bash scripts/data-smoke.sh` pasa.
- Metabase muestra el dashboard `Oil & Gas BI Dashboard`.
- dbt Docs muestra modelos y lineage.
- DataHub muestra datasets del warehouse en la EC2 dedicada.

Registrar cualquier limitacion real en `docs/delivery-checklist.md` antes de armar el zip final.
