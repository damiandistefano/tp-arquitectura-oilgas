# Checklist de entrega - Adenda 2

Este documento es la verdad operativa para cerrar la entrega. Si un componente no puede mostrarse o validarse, se deja aclarado como limitacion y no se promete como productivo.

Responsables por area:

- I1: ingesta, Bronze, metadata, Dagster, estrategia de carga/backfill.
- I2: dbt, Silver, Gold, Semantic, calidad persistida, Metabase.
- I3: governance/DataHub, README, ADR review, runbooks, checklist final y evidencia de entrega.

---

## 1. Estado por componente

| Componente | Responsable | Estado para entrega | Evidencia esperada |
|---|---|---|---|
| API REST + Swagger | Equipo / Fase 1 | Listo | `/health`, `/docs`, endpoints con API key |
| Monitoreo tecnico | Equipo / Fase 1 | Listo | Grafana, Prometheus targets, Alertmanager |
| PostgreSQL warehouse | I1 | Listo | Schemas `bronze`, `silver`, `gold`, `quality`, `metadata`, `semantic` |
| Ingesta Bronze | I1 | Listo | Tablas `bronze.raw_*` con filas y metadata |
| Dagster | I1 | Validado localmente | UI `:3002`, assets visibles, corrida del pipeline o logs |
| dbt Silver/Gold/Semantic | I2 | Listo | `dbt build`, tablas/vistas con filas, dbt Docs |
| Calidad persistida | I2 | Listo | `quality.data_quality_results` con resultados recientes |
| Metabase | I2 | Listo con setup manual | Dashboard `Oil & Gas BI Dashboard`, 6 tarjetas con datos |
| DataHub / governance | I3 | Stack externo en EC2 dedicada | UI `:9002`, datasets del warehouse, columnas/tipos y metadata tecnica |
| Documentacion | I3 + equipo | Lista para entrega | README, ADRs, runbooks, contratos y checklist coherentes |

Nota sobre DataHub: no aparece en el `docker-compose.yml` principal porque su quickstart es pesado. Se opera con una EC2 dedicada y on-demand; ver [docs/runbooks/datahub.md](runbooks/datahub.md).

---

## 1.1 Instancias e IPs para la demo

Completar el dia de la entrega con las IPs vigentes. No commitear llaves `.pem`, `.env` reales ni capturas con secretos.

| Instancia | Uso | Tamaño esperado | URL/IP a validar | Responsable |
|---|---|---|---|---|
| Sandbox API/monitoreo | API, Swagger, Prometheus, Grafana, Alertmanager, cAdvisor | `t3.micro` para API sola; `t3.small`/`t3.medium` si se muestra monitoreo completo | `http://<ip-o-dominio>` | Equipo / I1 |
| Sandbox datos | Postgres, Dagster, Metabase, dbt local/containers | `t3.medium` o `t3.large` si se levanta todo junto para demo | `http://<ip-o-dominio>:3001` y `:3002` | I1 + I2 |
| DataHub | Catalogo/governance | `t3.large` dedicada, on-demand | `http://<ip-datahub>:9002` | I3 |

Criterio: si una instancia `large` solo corre API/monitoreo, conviene bajarla. Si corre DataHub o todo el stack de datos en una sola maquina, `large` es defendible para una demo corta, siempre apagandola al terminar.

---

## 2. Arranque desde cero

### Pre-requisitos

- Docker Desktop o Docker Engine + Docker Compose.
- Python 3 con `pip`, o entorno equivalente usado por el equipo.
- Acceso a internet para descargar CSVs desde datos.energia.gob.ar.

### 1. Configurar entorno

```bash
cp .env.example .env
```

Revisar puertos segun desde donde se ejecute:

- Desde la maquina host: Postgres se accede por `localhost:5433`.
- Desde contenedores en Compose: Postgres se accede por `postgres:5432`.

### 2. Levantar stack

```bash
docker compose up --build -d
docker compose ps
```

Servicios esperados:

- `postgres` / `warehouse-postgres` healthy.
- `api` en `8000`.
- `prometheus` en `9090`.
- `grafana` en `3000`.
- `alertmanager` en `9093`.
- `cadvisor` en `8080`.
- `metabase` en `3001`.
- `dagster` en `3002`.

### 3. Ejecutar pipeline de datos

Opcion A: desde Dagster UI.

1. Abrir `http://localhost:3002`.
2. Ver assets `extract_to_bronze`, `run_silver_transformations`, `run_quality_checks`.
3. Materializar el pipeline.
4. Revisar logs por asset.

Opcion B: comandos manuales.

```bash
python -m extract.load_to_bronze

cd dbt
dbt debug
dbt build
dbt docs generate
cd ..

python -m quality.checks
```

---

## 3. Verificaciones automaticas y semi-automaticas

### Codigo y configuracion

```bash
ruff check .
pytest -q
docker compose config
IMAGE_TAG=ci API_PORT=8002 docker compose -f docker-compose.deploy.yml config
```

### API y monitoreo

```bash
curl http://localhost:8000/health
curl http://localhost:8000/openapi.json
curl -H "X-API-Key: abcdef12345" "http://localhost:8000/api/v1/wells?date_query=2026-03-15"
curl http://localhost:3000/api/health
curl http://localhost:9090/-/healthy
```

### Warehouse

```bash
psql -h localhost -p 5433 -U dwh -d warehouse -c "
  SELECT 'bronze.raw_produccion_no_convencional' AS tabla, count(*) FROM bronze.raw_produccion_no_convencional
  UNION ALL
  SELECT 'bronze.raw_pozos', count(*) FROM bronze.raw_pozos_operadoras
  UNION ALL
  SELECT 'silver.produccion', count(*) FROM silver.produccion_no_convencional
  UNION ALL
  SELECT 'gold.fact_produccion_pozo', count(*) FROM gold.fact_produccion_pozo
  UNION ALL
  SELECT 'semantic.vw_produccion_mensual', count(*) FROM semantic.vw_produccion_mensual;
"
```

### Calidad

```bash
psql -h localhost -p 5433 -U dwh -d warehouse -c "
  SELECT check_name, layer, table_name, status, severity, executed_at
  FROM quality.data_quality_results
  ORDER BY executed_at DESC
  LIMIT 20;
"
```

### Metabase

Entrar a `http://localhost:3001` y validar:

- login `martinbianchi@udesa.edu.ar` / `Admin1234!`;
- conexion a PostgreSQL `postgres:5432`;
- base `warehouse`;
- dashboard `Oil & Gas BI Dashboard`;
- tarjetas con datos sobre `semantic.*` y `quality.data_quality_results`;
- evidencia de validacion.

### Dagster

Entrar a `http://localhost:3002` y validar:

- assets visibles;
- grafo de dependencias;
- corrida exitosa o, si falla, logs claros;
- evidencia de validacion.

### dbt Docs

```bash
cd dbt
dbt docs generate
dbt docs serve
```

Validar modelos, columnas, tests y lineage.

### DataHub

Validar en la EC2 dedicada antes de grabar o mostrar la demo:

| Dato | Valor |
|---|---|
| URL final | `http://<ip-datahub>:9002` |
| Como se levanta | `datahub docker quickstart` en EC2 dedicada |
| Credenciales | `datahub` / `datahub` |
| Ingesta | `datahub ingest -c datahub/recipe.postgres.yml` |
| Datasets visibles | `bronze`, `silver`, `gold`, `quality`, `metadata`, `semantic` |
| Evidencia guardada | Capturas o registro de validacion de UI |

Evidencia minima esperada:

- datasets del warehouse visibles;
- columnas y tipos visibles;
- capas medallion navegables;
- detalle de `gold.fact_produccion_pozo`;
- si la UI muestra lineage, incluirlo; si no, apoyar el linaje tecnico con dbt Docs y Dagster.

---

## 4. Inventario de entregables

### ADRs

Ver indice completo en [docs/adr/README.md](adr/README.md).

| Rango | Estado |
|---|---|
| 0001-0005 | Presentes, Fase 1 |
| 0006-0008 | Presentes, I1: Dagster, carga/backfill, warehouse |
| 0009-0012 | Presentes, I2: Medallion, Gold, calidad, Semantic |
| 0013 | Presente, I3: DataHub / governance |
| 0014 | Presente, I2: Metabase / BI |

### Runbooks

| Archivo | Estado |
|---|---|
| `docs/runbooks/local-stack.md` | Presente |
| `docs/runbooks/deploy-aws.md` | Presente |
| `docs/runbooks/sandbox-validation.md` | Presente |
| `docs/runbooks/bi-user.md` | Presente |
| `docs/runbooks/dbt-analytics.md` | Presente |
| `docs/runbooks/data-engineer.md` | Presente |
| `docs/runbooks/datahub.md` | Presente |

### Datos y calidad

| Archivo | Estado |
|---|---|
| `docs/data-contracts-2.md` | Presente |
| `docs/data-model.md` | Presente |
| `docs/quality-checks.md` | Presente |

---

## 5. Checklist final de entrega

### Stack base

- [ ] `docker compose up --build -d` levanta sin errores.
- [ ] Postgres queda healthy.
- [ ] API responde `/health`.
- [ ] Grafana abre en `:3000`.
- [ ] Prometheus abre en `:9090`.
- [ ] Dagster abre en `:3002`.
- [ ] Metabase abre en `:3001`.

### Pipeline de datos

- [ ] Bronze tiene filas.
- [ ] dbt construye Silver/Gold/Semantic.
- [ ] Quality checks se persisten y no hay `FAILED` criticos sin explicar.
- [ ] Dagster muestra corrida o logs de la orquestacion.
- [ ] Metabase muestra dashboard con datos.
- [ ] dbt Docs muestra lineage.
- [ ] DataHub abre en `:9002` y muestra datasets del warehouse.

### Documentacion

- [ ] README refleja el estado real.
- [ ] ADRs tienen alternativas y trade-offs.
- [ ] Runbooks tienen pasos, validacion y que hacer si falla.
- [ ] No quedan TODOs ni frases de borrador; las URLs variables de entrega estan identificadas.
- [ ] No se promete produccion real ni alta disponibilidad.

### Entrega final

- [ ] `develop` tiene todos los merges.
- [ ] CI en verde.
- [ ] Imagen GHCR publicada para el commit final si se usa deploy desde registry.
- [ ] Smoke test de AWS ejecutado por script o workflow manual si se muestra EC2.
- [ ] Merge a `main`.
- [ ] Tag de release en `main`.
- [ ] Zip armado sin `.env`, `.pem`, caches, dumps, outputs generados ni `/contexto`.
- [ ] Zip armado y revisado contra la lista de exclusiones.
