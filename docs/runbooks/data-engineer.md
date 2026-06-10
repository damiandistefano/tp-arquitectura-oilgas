# Runbook: Operación del pipeline de datos

Este runbook describe cómo operar el pipeline completo de datos Oil & Gas: ingesta bronze,
transformación silver/gold/semantic, checks de calidad, backfill y recovery ante fallas.

Flujo de datos:

```
CSV (datos.energia.gob.ar)
  → bronze (raw_produccion_no_convencional, raw_pozos_operadoras)
    → silver / gold / semantic  (dbt)
      → calidad (quality.data_quality_results)
        → consumo BI (Metabase / semantic views)
```

---

## 1. Pre-requisitos

- Docker Desktop o Docker Engine + Docker Compose.
- Python 3.x con dependencias instaladas:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

- Perfil dbt configurado en `~/.dbt/profiles.yml` apuntando al warehouse local:

```bash
cp dbt/profiles.example.yml ~/.dbt/profiles.yml
# Verificar que host=localhost y port=5433
```

- Acceso a internet (la ingesta descarga CSVs de `datos.energia.gob.ar`).

---

## 2. Levantar el warehouse

El pipeline necesita que el servicio `postgres` esté healthy antes de correr cualquier paso.

```bash
docker compose up -d postgres
docker compose ps
# warehouse-postgres debe mostrar (healthy)
```

Si se quiere levantar el stack completo (API + monitoreo + Metabase):

```bash
cp .env.example .env
docker compose up -d --build
```

Ver [local-stack.md](local-stack.md) para el detalle del stack de monitoreo.

---

## 3. Correr el pipeline completo

Ejecutar los pasos en orden. Cada paso asume que el anterior fue exitoso.

### 3.1 Ingesta bronze

```bash
bash scripts/run-data-pipeline.sh
```

Descarga los CSVs y carga las tablas bronze en el warehouse. Counts esperados:

| Tabla | Filas |
|---|---|
| `bronze.raw_produccion_no_convencional` | 405 996 |
| `bronze.raw_pozos_operadoras` | 84 242 |
| `metadata.source_files` | 2 |

### 3.2 Transformación dbt

```bash
cd dbt
dbt run
dbt test
cd ..
```

Construye las tablas silver, gold y las vistas semantic. Ver [dbt-analytics.md](dbt-analytics.md)
para el detalle de counts por capa y troubleshooting de perfiles.

Counts mínimos esperados:

| Objeto | Filas |
|---|---|
| `silver.produccion_no_convencional` | 405 996 |
| `silver.pozos_operadoras` | 84 242 |
| `gold.fact_produccion_pozo` | 405 996 |
| `gold.dim_pozo` | 84 538 |
| `gold.dim_fecha` | 244 |
| `gold.dim_operadora` | 55 |
| `semantic.vw_produccion_mensual` | 244 |
| `semantic.vw_produccion_por_operadora` | 4 395 |

### 3.3 Checks de calidad

```bash
bash scripts/run-quality-checks.sh
```

Ejecuta `python -m quality.checks` y persiste los resultados en `quality.data_quality_results`.
Si algún check crítico falla, el script sale con exit code ≠ 0 y se debe revisar antes de continuar
(ver [ADR 0011](../adr/0011-persistir-calidad-de-datos-y-bloquear-promocion.md)).

Verificar resultados:

```bash
psql -h localhost -p 5433 -U dwh -d warehouse -c "
  SELECT check_name, layer, table_name, status, severity, executed_at
  FROM quality.data_quality_results
  ORDER BY executed_at DESC
  LIMIT 20;
"
```

---

## 4. Monitoreo de frescura y calidad

### Frescura de datos

```bash
psql -h localhost -p 5433 -U dwh -d warehouse -c "
  SELECT * FROM semantic.vw_frescura_datos;
"
```

Muestra la última ingesta disponible y el último período con datos.

### Estado de calidad

```bash
psql -h localhost -p 5433 -U dwh -d warehouse -c "
  SELECT check_name, dimension, status, severity, rows_failed, executed_at
  FROM quality.data_quality_results
  WHERE executed_at = (SELECT max(executed_at) FROM quality.data_quality_results)
  ORDER BY severity DESC;
"
```

Política: checks con `severity = 'critical'` y `status = 'failed'` bloquean la promoción de datos
a capas superiores (ADR 0011). Si aparece alguno, no se debe considerar el pipeline como exitoso.

---

## 5. Backfill por rango de fechas

**Estado actual: pendiente de implementación (coordinar con I1).**

El script `scripts/backfill.sh` recibe un rango de fechas pero hoy solo imprime el parámetro —
la lógica de re-ingesta filtrada por fecha no está implementada:

```bash
bash scripts/backfill.sh 2025-01-01 2025-03-31
# Solo imprime el rango; no re-carga datos todavía
```

Mientras tanto, para re-procesar un período: re-correr el pipeline completo (sección 3). La
ingesta sobreescribe bronze y dbt es idempotente, por lo que una re-ejecución completa es segura.

---

## 6. Orquestación (estado actual)

**El pipeline se corre hoy de forma manual** siguiendo la secuencia de la sección 3.

Dagster (puerto 3002) está previsto como orquestador pero **no está configurado en
`docker-compose.yml`**; su integración está pendiente de I1. El checklist lo registra como
"verificar con I1". No documentar Dagster como operativo hasta que esté integrado.

---

## 7. Troubleshooting

### Warehouse no está `(healthy)`

```bash
docker compose logs postgres
```

Esperar el healthcheck (puede tardar hasta 30 segundos). Si el contenedor sale con error, revisar
que el puerto 5433 no esté ocupado por otra instancia de Postgres local.

### Ingesta falla o timeout

La extracción tiene reintentos configurados en `extract/retry.py`. Si igual falla:

1. Verificar conectividad a `datos.energia.gob.ar`.
2. Re-correr `bash scripts/run-data-pipeline.sh` — la carga es idempotente.
3. Ver logs detallados: la extracción usa `extract/logging_config.py`.

### `dbt run` falla con error de conexión

Verificar que `~/.dbt/profiles.yml` tenga `host: localhost` y `port: 5433` (no 5432):

```bash
cat ~/.dbt/profiles.yml
dbt debug --project-dir dbt/
```

### Vistas semantic no existen

```bash
cd dbt
dbt run
dbt test
cd ..
```

### Sin resultados en `quality.data_quality_results`

```bash
bash scripts/run-quality-checks.sh
```

Si la tabla no existe, verificar que el warehouse tenga el schema `quality` (se crea al correr
los checks por primera vez con el warehouse levantado).

### `dbt test` falla

Revisar el output de `dbt test`. Los tests de schema, not_null y unique fallan si los datos de
bronze no fueron cargados correctamente. Re-correr desde el paso de ingesta (sección 3.1).

---

## 8. Re-run y recovery

### Re-correr solo la ingesta

```bash
bash scripts/run-data-pipeline.sh
```

Bronze es sobreescrito. Luego correr dbt y calidad (secciones 3.2 y 3.3).

### Re-correr solo dbt

```bash
cd dbt && dbt run && dbt test && cd ..
```

dbt es idempotente: recrea las tablas/vistas sin necesidad de borrar nada antes.

### Re-correr solo calidad

```bash
bash scripts/run-quality-checks.sh
```

Agrega una nueva fila en `quality.data_quality_results` con el timestamp de la ejecución.

### Verificación post-recovery

Confirmar counts con la consulta de la sección 3 y revisar el resultado de calidad con la
consulta de la sección 4. Si todos los checks críticos pasan y los counts coinciden, el pipeline
está en estado bueno.
