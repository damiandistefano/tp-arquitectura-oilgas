# Feature Store

Feature store offline sobre Postgres (schema `features`), poblado desde el
warehouse Gold. Lo consumen training (Integrante 1) y la API de inferencia
(Integrante 2) a través de `feature_store/repository.py`.

## Tablas

| Tabla | Contenido |
|---|---|
| `features.pozo_monthly_features` | Una fila por `id_pozo` + `periodo_mes` con target y features. PK compuesta. |
| `features.feature_generation_runs` | Auditoría de cada corrida: as_of_date, filas, pozos, rango de períodos, status. |
| `features.feature_reference_stats` | Stats de las features del set de entrenamiento, por `training_run_id`. Base del drift check. |

El schema se crea con `postgres-init/02_features_schema.sql` (init de
contenedor nuevo). Para un Postgres ya inicializado, aplicarlo a mano:

```bash
docker compose exec -T postgres psql -U dwh -d warehouse < postgres-init/02_features_schema.sql
```

## Generación

```bash
python -m ml.build_features --as-of-date 2026-06-01
```

- Lee `gold.fact_produccion_pozo` (agregada a pozo+mes) y `gold.dim_pozo`.
- Corta a `as_of_date`: nunca entran datos posteriores al mes de corte.
- Calcula lags 1/2/3, rolling mean/std 3, `mes`, `anio`, `antiguedad_meses`
  y categóricas, sobre un calendario mensual continuo por pozo.
- Reemplaza el contenido de la tabla (rebuild completo, reproducible) y
  registra la corrida en `feature_generation_runs`.

## No-leakage

Regla del contrato: para el mes M solo se usan datos hasta M-1.

- Los lags se calculan con `shift` sobre el calendario continuo: `lag_1` del
  mes M es siempre el mes calendario M-1, aunque falten meses en la fuente.
- Las rolling stats usan la serie ya desplazada (`shift(1)`), por lo que la
  ventana es M-3..M-1 y nunca incluye a M.
- `tests/test_ml_features.py` verifica lags, ventana rolling, corte por
  `as_of_date` y que un mes faltante no corra la ventana.

## Verificación rápida

```sql
select * from features.feature_generation_runs order by started_at desc limit 5;
select count(*) from features.pozo_monthly_features;
select count(*) from features.feature_reference_stats;
```
