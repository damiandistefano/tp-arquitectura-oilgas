# ADR 0018 — Definir modelo, baseline y gate de promoción

## Estado
Aceptado

## Contexto

Adenda 3 aclara que no se evalúa cuál es "el mejor modelo posible", sino que haya un flujo de entrenamiento y promoción que funcione. Aun así, había que elegir un modelo simple, un baseline para comparar, y una regla clara de cuándo un modelo nuevo reemplaza al que está activo.

## Problema

Necesitamos definir:
- contra qué se compara un modelo nuevo (baseline)
- cómo se separan datos de entrenamiento y de test sin hacer trampa
- cuándo un modelo nuevo pasa a ser el champion

## Alternativas consideradas

**Split aleatorio de filas para train/test**
- Es lo más común en tutoriales de ML
- En una serie de tiempo esto es trampa: el modelo puede "ver" meses futuros mezclados en el train y parecer mejor de lo que es

**Split temporal (elegida)**
- Los últimos 6 meses quedan como test, el resto como train
- Si no hay suficiente historia, se usan los últimos 3 meses como test
- Es la forma correcta de validar un forecast: entrenar con el pasado, evaluar sobre el futuro

**No tener baseline, solo mirar la métrica del modelo**
- Una métrica sola (por ejemplo MAE) no dice si el modelo realmente sirve
- Sin comparación, cualquier modelo por mediocre que sea "parece que funciona"

**Baseline naive: repetir el último valor conocido (elegida)**
- `baseline_pred = prod_pet_lag_1` (predecir que este mes es igual al anterior)
- Es un baseline típico en forecasting y muy fácil de calcular
- Si el modelo no le gana a esto, no aporta nada

**Promover siempre el modelo más nuevo**
- Simplifica el código
- Puede ir empeorando el sistema con el tiempo si un entrenamiento sale mal

**Gate de promoción con bootstrap (elegida)**
- Si no hay champion todavía, el primer modelo que le gane al baseline se promueve (bootstrap)
- Si ya hay champion, el candidato tiene que superar al baseline Y al champion actual, evaluados sobre la misma ventana de test
- Esto evita que un modelo peor reemplace a uno que ya funciona bien

## Decisión

Modelo: un `HistGradientBoostingRegressor` de scikit-learn con las features definidas en `ml/config.py` (lags, rolling mean/std, mes/año, antigüedad y categóricas del pozo). Split temporal de 6 meses de test (o 3 si no alcanza). Baseline naive por lag_1. Gate de promoción con bootstrap sin champion y comparación completa cuando ya hay uno.

## Consecuencias

- El gate puede decidir no promover nada, y eso es correcto, no un bug: significa que el modelo nuevo no mejoró
- Todo el registro de la decisión (métricas, si promovió o no, y por qué) queda guardado en el run
- Un dataset muy chico o muy simple puede hacer que el modelo nunca le gane al baseline naive, sobre todo si la serie es muy lineal

## Qué queda fuera

No se prueban múltiples modelos ni se hace tuning de hiperparámetros en esta entrega. No hay A/B testing ni canary de modelos, la promoción es todo o nada.
