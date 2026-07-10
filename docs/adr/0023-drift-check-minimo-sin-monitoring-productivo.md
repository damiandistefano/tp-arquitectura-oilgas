# ADR 0023 — Drift check mínimo, sin monitoring productivo completo

## Estado
Aceptado

## Contexto

Adenda 3 pide observabilidad sobre el modelo, incluyendo poder detectar si las features actuales se empezaron a alejar de las que se usaron para entrenar (drift). Esto no tiene que ser un sistema de monitoreo productivo completo, pero tiene que existir algo que corra y de una señal.

## Problema

Necesitamos:
- comparar las features recientes contra alguna referencia del modelo activo
- que esto no dependa de tener el modelo entrenado de nuevo cada vez
- que si no hay todavía un champion, el chequeo no rompa de forma confusa

## Alternativas consideradas

**Evidently o alguna librería de monitoring dedicada**
- Son herramientas hechas justo para esto, con reportes lindos
- Agregan una dependencia grande y un concepto nuevo (dashboards de drift) para algo que acá es un chequeo simple
- Es más de lo que pide la entrega

**Recalcular las estadísticas de referencia en cada corrida del drift check**
- Evita tener que guardar nada de más
- El riesgo es que si el drift check nunca se corrió, "referencia" y "datos actuales" terminan siendo casi lo mismo, y nunca detecta nada (esto se charló como el riesgo de "drift script muerto")

**Guardar la referencia en el mismo run de training (elegida)**
- Cuando se entrena un modelo, ya se calculan mean/std/percentiles de cada feature numérica sobre el set de train, y se guardan en `features.feature_reference_stats`
- El drift check después solo tiene que leer esa tabla para el champion actual y comparar contra los datos recientes
- Si hay un candidato entrenado, siempre hay referencia disponible para compararlo cuando se vuelva champion

## Decisión

`ml/drift_check.py` lee el champion actual, busca sus `feature_reference_stats` (ya calculadas en su momento de entrenamiento) y las compara contra los últimos meses de `features.pozo_monthly_features` usando un z-score simple por feature. Si el z-score pasa un umbral, se marca esa feature como con drift. Si todavía no hay champion o no hay referencia guardada, el script no rompe de forma rara: devuelve un mensaje claro diciendo por qué no se pudo evaluar.

## Consecuencias

- El drift check es liviano, no agrega infraestructura ni dependencias pesadas
- No hay alertas automáticas ni dashboard, hay que correr el script (`scripts/run-drift-check.sh`) a mano o desde CI
- Detectar drift no dispara ninguna acción automática (como forzar un reentrenamiento), solo informa

## Qué queda fuera

No hay monitoring productivo completo, ni alertas automáticas, ni un dashboard de drift. Es un chequeo puntual, pensado para correrlo manual o como parte del checklist de entrega.
