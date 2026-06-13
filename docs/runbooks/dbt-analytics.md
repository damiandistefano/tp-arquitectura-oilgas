# Runbook - Analytics Engineer / Data Engineer

## Proposito

Correr y validar el pipeline analitico desde Bronze hasta Silver, Gold, Semantic y Quality.

Se usa cuando:

- se levanta el stack desde cero;
- cambio un modelo dbt;
- cambio la fuente o la ingesta;
- un dashboard de Metabase muestra datos raros;
- hay que preparar evidencia para la entrega.

## Rol responsable

Analytics Engineer / Data Engineer.

Necesita:

- acceso al repo;
- Docker y Docker Compose;
- Python y dependencias del proyecto;
- conexion al warehouse PostgreSQL;
- permisos para abrir Dagster, Metabase y dbt Docs.

---

## 1. Levantar servicios base

```bash
cp .env.example .env
docker compose up --build -d postgres dagster metabase
docker compose ps
```

Validar que Postgres este healthy.

Desde contenedores, Postgres se accede como `postgres:5432`.
Desde la maquina host, se accede como `localhost:5433`.

---

## 2. Cargar Bronze

Opcion por Dagster:

1. Abrir `http://localhost:3002`.
2. Materializar `extract_to_bronze`.
3. Revisar logs y run id.

Opcion por comando:

```bash
python -m extract.load_to_bronze
```

Validacion:

```sql
select count(*) from bronze.raw_produccion_no_convencional;
select count(*) from bronze.raw_pozos_operadoras;
select source_name, source_file_hash, rows_loaded, ingested_at
from metadata.source_files
order by ingested_at desc;
```

La ingesta es idempotente a nivel hash de archivo: si una fuente ya fue cargada con el mismo hash, no deberia duplicarse en Bronze.

---

## 3. Correr dbt

Preparar perfil local si se ejecuta desde host:

```bash
mkdir -p ~/.dbt
cp dbt/profiles.example.yml ~/.dbt/profiles.yml
```

Ejecutar:

```bash
cd dbt
dbt debug
dbt build
dbt docs generate
cd ..
```

Validacion esperada:

```sql
select count(*) from silver.produccion_no_convencional;
select count(*) from silver.pozos_operadoras;
select count(*) from gold.fact_produccion_pozo;
select count(*) from gold.dim_pozo;
select count(*) from gold.dim_fecha;
select count(*) from gold.dim_operadora;
select count(*) from gold.dim_area;
select count(*) from gold.dim_yacimiento;
select count(*) from semantic.vw_produccion_mensual;
select count(*) from semantic.vw_produccion_por_operadora;
select count(*) from semantic.vw_produccion_por_area;
select count(*) from semantic.vw_frescura_datos;
```

No fijar los counts como contrato absoluto si la fuente publica cambia. Para la entrega, registrar los counts reales del dia en el checklist.

---

## 4. Correr quality gate

Opcion por Dagster:

1. Materializar el asset `run_quality_checks`.
2. Revisar logs y estado.

Opcion por comando:

```bash
python -m quality.checks
```

Validacion:

```sql
select check_name, layer, table_name, dimension, status, severity, rows_failed, executed_at
from quality.data_quality_results
order by executed_at desc
limit 20;
```

Regla operativa:

- `CRITICAL` + `FAILED`: no presentar datos downstream como validos sin explicar y corregir.
- `WARNING`: queda visible para revision, pero puede no bloquear.

---

## 5. Validar dbt Docs

```bash
cd dbt
dbt docs serve
```

Abrir la URL local que imprime dbt y revisar:

- modelos por capa;
- columnas importantes;
- tests;
- lineage de Bronze/Staging hacia Silver, Gold y Semantic.

Registrar evidencia de lineage si se usa dbt Docs para explicar governance.

---

## 6. Si algo falla

### No conecta a Postgres

Revisar desde donde se ejecuta:

- host: `localhost:5433`;
- contenedor: `postgres:5432`.

Revisar:

```bash
docker compose ps
docker compose logs postgres
```

### dbt falla por perfil

Verificar `~/.dbt/profiles.yml` si se corre desde host.
Si se corre dentro de Dagster, verificar que el contenedor tenga perfil dbt disponible y permisos para escribir artefactos.

### Quality falla

1. Identificar check fallido.
2. Revisar capa afectada.
3. Revisar si Bronze tiene fuente correcta.
4. Reejecutar dbt si el error esta en modelos.
5. Volver a correr quality.
6. Registrar resultado en el checklist.

### Datos duplicados

Revisar `metadata.source_files` por hash de fuente y run id. Bronze puede acumular corridas distintas; Silver/Gold deben mantenerse idempotentes para consumo.

---

## 7. Decisiones del proyecto desde este rol

Decision funcional:

- Separar Bronze, Silver, Gold y Semantic. Desde el rol tecnico, esto evita mezclar evidencia cruda con datos de consumo y permite depurar una metrica desde el dashboard hasta la fuente.

Decision no funcional:

- Usar procesamiento batch con quality gate persistido. Para este dataset publico no hay necesidad real de streaming; es mas importante que cada corrida sea trazable, repetible y verificable.

Estas decisiones favorecen mantenibilidad y defensa academica por encima de una arquitectura mas compleja que el equipo no podria operar con seguridad en esta entrega.
