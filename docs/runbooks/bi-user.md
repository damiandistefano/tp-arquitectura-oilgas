# Runbook - Usuario BI / Data Analyst

## Proposito

Consultar metricas de produccion de Oil & Gas en Metabase sin tener que conocer las tablas crudas ni escribir transformaciones desde cero.

Se usa cuando:

- hay que revisar produccion mensual;
- se quiere comparar operadoras, areas o yacimientos;
- se prepara evidencia de entrega;
- se valida frescura y estado de calidad de los datos.

## Rol responsable

Usuario BI / Data Analyst.

Necesita:

- acceso a Metabase;
- conexion al warehouse PostgreSQL;
- dashboard `Oil & Gas BI Dashboard`;
- datos ya procesados en `semantic.*` y `quality.data_quality_results`.

---

## 1. Entrar a Metabase

URL local:

```text
http://localhost:3001
```

Base esperada:

```text
Oil & Gas Warehouse
```

Credenciales de acceso local:

| Campo | Valor |
|---|---|
| Email | `martinbianchi@udesa.edu.ar` |
| Password | `Admin1234!` |

Conexion a PostgreSQL desde Metabase:

| Campo | Valor |
|---|---|
| Host | `postgres` |
| Puerto | `5432` |
| Database | `warehouse` |
| User | `dwh` |
| Password | `dwh` |

Desde la maquina host, para validar con `psql`, usar `localhost:5433`.

---

## 2. Regla de consumo

El dashboard debe consumir:

- vistas `semantic.*`;
- tabla `quality.data_quality_results` para estado de calidad.

No consultar Bronze desde BI. Bronze guarda evidencia de ingesta, no datos preparados para usuarios de negocio.

---

## 3. Dashboard esperado

Nombre:

```text
Oil & Gas BI Dashboard
```

Tarjetas minimas:

1. Produccion mensual.
2. Produccion por operadora.
3. Produccion por area/yacimiento.
4. Pozos con produccion mensual.
5. Frescura de datos.
6. Estado de calidad.

---

## 4. Consultas SQL para reconstruir el dashboard

### 1. Produccion mensual

Usar como grafico de linea o barras por `periodo`.

```sql
select
  periodo,
  prod_pet_total,
  prod_gas_total,
  prod_agua_total,
  registros_produccion,
  pozos_con_produccion
from semantic.vw_produccion_mensual
order by fecha_mes;
```

### 2. Produccion por operadora

Usar barras o tabla ordenada por produccion de petroleo/gas.

```sql
select
  empresa,
  sum(prod_pet_total) as prod_pet_total,
  sum(prod_gas_total) as prod_gas_total,
  sum(prod_agua_total) as prod_agua_total,
  sum(registros_produccion) as registros_produccion,
  count(distinct periodo) as periodos_con_datos
from semantic.vw_produccion_por_operadora
group by empresa
order by prod_pet_total desc
limit 20;
```

### 3. Produccion por area y yacimiento

Usar tabla o barras apiladas si el volumen visual queda claro.

```sql
select
  areapermisoconcesion,
  areayacimiento,
  provincia,
  cuenca,
  sum(prod_pet_total) as prod_pet_total,
  sum(prod_gas_total) as prod_gas_total,
  sum(prod_agua_total) as prod_agua_total,
  sum(pozos_con_produccion) as pozos_con_produccion
from semantic.vw_produccion_por_area
group by
  areapermisoconcesion,
  areayacimiento,
  provincia,
  cuenca
order by prod_pet_total desc
limit 20;
```

### 4. Pozos con produccion mensual

Usar grafico de linea por periodo.

```sql
select
  periodo,
  pozos_con_produccion
from semantic.vw_produccion_mensual
order by fecha_mes;
```

### 5. Frescura de datos

Usar tarjeta KPI o tabla chica.

```sql
select
  ultimo_periodo_disponible,
  ultima_ingesta,
  registros_totales,
  pozos_distintos,
  archivos_fuente,
  dias_desde_ultimo_periodo
from semantic.vw_frescura_datos;
```

### 6. Estado de calidad

Usar tabla o grafico por estado/severidad.

```sql
select
  status,
  severity,
  count(*) as checks
from quality.data_quality_results
where executed_at = (
  select max(executed_at)
  from quality.data_quality_results
)
group by status, severity
order by severity, status;
```

Consulta alternativa para detalle:

```sql
select
  check_name,
  layer,
  table_name,
  dimension,
  status,
  severity,
  rows_failed,
  executed_at
from quality.data_quality_results
order by executed_at desc
limit 20;
```

---

## 5. Validacion manual

Antes de cerrar la entrega:

- Metabase abre en `http://localhost:3001`.
- La base `Oil & Gas Warehouse` conecta correctamente.
- Las vistas `semantic.*` aparecen en el explorador.
- El dashboard tiene datos, no solo tarjetas vacias.
- Las tarjetas usan `semantic.*` o `quality.*`, no Bronze.
- Dejar evidencia del dashboard y de una consulta SQL abierta.

Validacion por script:

```bash
bash scripts/metabase-smoke.sh
```

Ese script valida health de Metabase, existencia de vistas semantic y resultados de calidad. No reemplaza la revision visual del dashboard.

---

## 6. Si algo falla

### No abre Metabase

```bash
docker compose ps metabase
docker compose logs metabase
```

### No conecta al warehouse

Revisar que el host sea `postgres` y el puerto `5432` dentro de Metabase. `localhost:5433` solo sirve desde la maquina host, no desde el contenedor.

### Las vistas no existen

Pedir al rol tecnico que corra:

```bash
cd dbt
dbt build
cd ..
```

### No hay resultados de calidad

Pedir al rol tecnico que corra:

```bash
python -m quality.checks
```

### El dashboard muestra datos raros

1. Revisar frescura.
2. Revisar estado de calidad.
3. Comparar una metrica contra la vista semantic correspondiente.
4. Escalar al Analytics Engineer si hay `FAILED` critico o cambios de fuente.

---

## 7. Decisiones del proyecto desde este rol

Decision funcional:

- El usuario BI consume metricas desde la capa `semantic`, no desde Bronze ni desde SQL ad hoc sobre tablas crudas. Esto reduce diferencias entre tarjetas y evita que cada consulta calcule la misma metrica de forma distinta.

Decision no funcional:

- El dashboard se arma desde UI y queda reproducible por runbook, no provisionado automaticamente por API de Metabase. Para esta entrega se priorizo que el usuario de negocio pueda inspeccionar datos reales y que el equipo pueda reconstruir las tarjetas sin manejar tokens internos de Metabase.

Limitacion:

- Si se borra el volumen de Metabase, el dashboard visual puede perderse y debe reconstruirse con las consultas de este runbook.
