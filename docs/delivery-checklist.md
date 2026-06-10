# Checklist de entrega — Adenda 2

Responsable: Integrante 3 (governance, documentación, validación final).

Este documento registra el estado real de la plataforma antes de la entrega y sirve como guía de
verificación el día de la demo. La regla es: si algo no está listo, se anota como pendiente — no
se promete más de lo que hay.

---

## 1. Estado por componente

| Componente | Responsable | Estado | Notas |
|---|---|---|---|
| API REST + monitoreo (Prometheus/Grafana/Alertmanager/cAdvisor) | I3 (Fase 1) | ✅ Listo | Puerto 8000 / 3000 / 9090 / 9093. Dashboard provisioned. |
| Ingesta bronze (`extract/`) | I1 | ✅ Listo | Escribe `bronze.raw_produccion_no_convencional` y `bronze.raw_pozos_operadoras` desde `datos.energia.gob.ar`. |
| Transformación silver/gold/semantic (dbt) | I2 | ✅ Listo | 4 tablas silver, 6 tablas gold, 4 vistas semantic. Requiere correr `dbt run`. |
| Calidad de datos (`quality/`) | I2 | ✅ Listo | Persiste en `quality.data_quality_results`. Checks: schema, completeness, uniqueness, freshness, lineage. |
| Metabase (BI) | I2 | ✅ Listo (conexión manual) | Puerto 3001. Conexión al warehouse se configura en la UI la primera vez. |
| Orquestación (Dagster) | I1 | ⏳ Verificar con I1 | Puerto 3002. |
| DataHub (gobierno de datos) | I3 | ⏳ Pendiente | Puerto 9002. Stack pesado (~6-8 GB RAM), se levanta local para la demo. No corre en EC2 sandbox chica. |

---

## 2. Cómo levantar todo de cero

### Pre-requisitos
- Docker Desktop o Docker Engine + Docker Compose.
- Python 3.x con `pip`.
- Acceso a internet (para descargar CSVs de `datos.energia.gob.ar`).

### Paso a paso

**1. Configurar entorno**
```bash
cp .env.example .env
# Editar .env si hace falta (SLACK_WEBHOOK_URL para alertas reales)
```

**2. Levantar el stack base**
```bash
docker compose up --build -d
```

Esto levanta: Postgres warehouse (`5433`), API (`8000`), Prometheus (`9090`), Grafana (`3000`),
Alertmanager (`9093`), cAdvisor (`8080`), Metabase (`3001`).

Esperar a que Postgres esté healthy antes de continuar:
```bash
docker compose ps
# warehouse-postgres debe mostrar (healthy)
```

**3. Cargar bronze (Integrante 1)**
```bash
pip install -r requirements.txt
python -m extract.load_to_bronze
```

Esto descarga los CSVs y llena `bronze.raw_produccion_no_convencional` y `bronze.raw_pozos_operadoras`.

**4. Correr transformaciones dbt (Integrante 2)**
```bash
pip install -r requirements-dev.txt
cp dbt/profiles.example.yml ~/.dbt/profiles.yml
# Verificar que profiles.yml apunte a localhost:5433
dbt run --project-dir dbt/
```

Esto construye las tablas silver/gold y las vistas semantic en el warehouse.

**5. Correr checks de calidad (Integrante 2)**
```bash
bash scripts/run-quality-checks.sh
```

Persiste resultados en `quality.data_quality_results`. Si falla un check crítico, sale con exit code ≠ 0.

**6. Conectar Metabase al warehouse**

Entrar a `http://localhost:3001`, completar el setup inicial con las credenciales del `.env`
(`METABASE_ADMIN_EMAIL` / `METABASE_ADMIN_PASSWORD`) y agregar una conexión a PostgreSQL:
- Host: `postgres` (nombre del contenedor en la red Docker)
- Puerto: `5432`
- DB: `warehouse`
- Usuario: `dwh` / Contraseña: `dwh`

---

## 3. Verificaciones pre-entrega

### Stack y código
```bash
# Análisis estático
python -m ruff check .

# Tests (los de API no necesitan DB; los de ingesta/calidad necesitan la DB levantada)
pytest tests/test_api.py -q
pytest tests/test_data_ingestion.py tests/test_data_quality.py -q  # con DB levantada

# Sanity de los compose
docker compose config
docker compose -f docker-compose.deploy.yml config
```

### API y monitoreo
```bash
curl http://localhost:8000/health
curl http://localhost:8000/openapi.json
curl -H "X-API-Key: abcdef12345" "http://localhost:8000/api/v1/wells?date_query=2026-03-15"
curl http://localhost:3000/api/health     # Grafana
curl http://localhost:9090/-/healthy      # Prometheus
```

### Datos en el warehouse
```bash
# Contar filas en las capas principales (requiere psql o cualquier cliente Postgres)
psql -h localhost -p 5433 -U dwh -d warehouse -c "
  SELECT 'bronze.raw_produccion' AS tabla, count(*) FROM bronze.raw_produccion_no_convencional
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

### Calidad de datos
```bash
psql -h localhost -p 5433 -U dwh -d warehouse -c "
  SELECT check_name, layer, table_name, status, severity, executed_at
  FROM quality.data_quality_results
  ORDER BY executed_at DESC LIMIT 20;
"
```

---

## 4. Inventario de entregables

### ADRs

Ver índice completo en [docs/adr/README.md](adr/README.md).

| # | Estado |
|---|---|
| 0001–0005 (Fase 1) | ✅ Presentes, revisados |
| 0006–0008 (I1: orquestación, backfill, warehouse) | ⏳ Pendientes (I1) |
| 0009–0012 (I2: medallion, gold, calidad, semantic) | ✅ Presentes |
| 0013 (I3: DataHub) | ⏳ Pendiente (I3, parqueado) |
| 0014 (I2: Metabase) | ⏳ Pendiente (I2) |

### Runbooks

| Archivo | Estado |
|---|---|
| `docs/runbooks/local-stack.md` | ✅ Presente |
| `docs/runbooks/deploy-aws.md` | ✅ Presente |
| `docs/runbooks/sandbox-validation.md` | ✅ Presente |
| `docs/runbooks/bi-user.md` | ✅ Presente |
| `docs/runbooks/dbt-analytics.md` | ✅ Presente |
| `docs/runbooks/data-engineer.md` | ✅ Presente |

### Contratos de datos y modelo

| Archivo | Estado | Nota |
|---|---|---|
| `docs/data-contracts-2.md` | ✅ Presente | Nombre difiere del esperado en PDF (`data-contracts.md`). Coordinar con I1/I2. |
| `docs/data-model.md` | ✅ Presente | — |
| `docs/quality-checks.md` | ✅ Presente | — |

### URLs oficiales de entrega

Ver [README.md — sección "URLs oficiales de entrega"](../README.md#urls-oficiales-de-entrega).

---

## 5. Responsabilidades por integrante (PDF §11)

| Área | I1 | I2 | I3 |
|---|---|---|---|
| Extracción + bronze | ✅ | — | — |
| Metadata de pipeline | ✅ | — | — |
| Orquestación | ✅ | — | — |
| Silver + Gold (dbt) | — | ✅ | — |
| Calidad persistida | — | ✅ | — |
| BI (Metabase) | — | ✅ | — |
| Semantic layer | — | ✅ | — |
| README | — | — | ✅ |
| ADR review | — | — | ✅ |
| Runbooks | — | — | ✅ |
| DataHub / governance | — | — | ✅ |
| Checklist final | — | — | ✅ |

---

## 6. Checklist para el día de la demo

### Stack base
- [ ] `docker compose up --build -d` levanta sin errores.
- [ ] `warehouse-postgres` muestra `(healthy)` en `docker compose ps`.
- [ ] API responde: `curl http://localhost:8000/health` → 200.
- [ ] Grafana accesible: `http://localhost:3000` (admin/admin).
- [ ] Prometheus accesible: `http://localhost:9090`.

### Pipeline de datos
- [ ] `python -m extract.load_to_bronze` corre sin errores. Bronze tiene filas.
- [ ] `dbt run --project-dir dbt/` corre sin errores. Silver/gold/semantic tienen filas.
- [ ] `bash scripts/run-quality-checks.sh` sale con exit 0. Resultados visibles en `quality.data_quality_results`.
- [ ] Metabase (`localhost:3001`) conectado al warehouse. Dashboard visible.

### Documentación
- [ ] ADRs 0001–0005 y 0009–0012 presentes y con "Alternativas consideradas".
- [ ] Runbooks de operación presentes (local-stack, deploy-aws, sandbox-validation, bi-user, dbt-analytics, data-engineer).
- [ ] `docs/delivery-checklist.md` (este archivo) actualizado con el estado real.
- [ ] `README.md` — sección "URLs oficiales de entrega" refleja el estado real.

### Entrega final
- [ ] Rama `develop` con todos los merges integrados.
- [ ] CI en verde en `develop`.
- [ ] Merge `develop` → `main` con CI en verde.
- [ ] Tag de release creado en `main` (`git tag v1.0.0`).
