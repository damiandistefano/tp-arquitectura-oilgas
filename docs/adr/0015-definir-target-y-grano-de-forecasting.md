# ADR 0015 — Definir target y grano de forecasting

## Estado
Aceptado

## Contexto

Adenda 3 pide agregar un modelo de forecasting sobre el warehouse que ya tenemos. Antes de tocar código había que decidir qué se predice y con qué nivel de detalle, porque eso afecta las features, el entrenamiento y la API. Si esto no queda cerrado desde el principio, cada uno lo hace distinto y después no encaja.

## Problema

Necesitamos elegir:
- qué columna se predice (el target)
- con qué frecuencia y a qué nivel (el grano)
- qué tan lejos hay que anticiparse

## Alternativas consideradas

**Predecir por día**
- Es el grano que ya usa la API mock actual
- Los datos de producción que tenemos vienen agregados por mes, no por día, así que habría que inventar una distribución diaria
- No tiene mucho sentido para pozos de petróleo, la producción se reporta mensual

**Predecir varias columnas (petróleo, gas, agua)**
- Sería más completo
- Multiplica el trabajo de features, entrenamiento y validación por 3
- No es necesario para cumplir el entregable, que pide un modelo funcionando end to end, no varios modelos

**Predecir prod_pet mensual por pozo (elegida)**
- Coincide con el grano real de los datos de origen (`gold.fact_produccion_pozo`)
- Es una sola columna, permite enfocarse en el pipeline completo en vez de en el modelo
- El id_pozo + periodo_mes ya es la clave natural de la tabla de features

## Decisión

El target es `prod_pet` y el grano es `id_pozo + periodo_mes` (un valor por pozo y por mes). El contrato de la API usa esos mismos nombres en español (`id_pozo`, `periodo_mes`, `prod_pet`), no `id_well` como tenía el mock viejo.

## Consecuencias

- Todas las features de `ml/config.py` están pensadas para ese grano (lags mensuales, rolling mean/std mensual)
- La tabla `features.pozo_monthly_features` tiene esa clave primaria
- Si más adelante se quiere predecir gas o agua, hay que repetir el mismo trabajo para esa columna

## Qué queda fuera

No se predice a nivel diario ni se predicen `prod_gas` o `prod_agua` en esta entrega.
