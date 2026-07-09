# ADR 0017 — Usar Postgres como feature store

## Estado
Aceptado

## Contexto

Adenda 3 pide un feature store persistido, que se use tanto para entrenar como para servir predicciones en la API. Ya tenemos Postgres corriendo como warehouse (bronze/silver/gold), así que había que decidir si el feature store va ahí mismo o en otra herramienta aparte.

## Problema

Necesitamos guardar las features (lags, rolling mean/std, atributos del pozo) en algún lado donde:
- el training las pueda leer para entrenar
- la API las pueda leer rápido para predecir
- quede registro de cuándo se generó cada corrida de features

## Alternativas consideradas

**Feast (feature store dedicado)**
- Es la herramienta "de verdad" para esto en la industria
- Requiere levantar infraestructura extra (registry, online store, a veces Redis)
- Es mucho para lo que pide esta entrega, que es un solo modelo con pocas features

**Calcular features al vuelo en cada request**
- No hay que persistir nada
- La API tendría que recalcular lags y rolling stats en cada predicción, consultando producción histórica completa
- Es más lento y mezcla lógica de features con el endpoint

**Postgres, schema nuevo `features` (elegida)**
- Ya tenemos Postgres levantado, no agrega infraestructura nueva
- Permite que training y API lean la misma tabla sin duplicar lógica
- Se puede auditar con SQL directo, que es útil para la demo

## Decisión

Se agrega un schema `features` en el mismo Postgres del warehouse, con tres tablas: `pozo_monthly_features` (las features en sí), `feature_generation_runs` (auditoría de cada corrida) y `feature_reference_stats` (estadísticas para el drift check). Tanto `ml/build_features.py` como la API leen de ahí a través de `feature_store/repository.py`, que es el único lugar que sabe el SQL de estas tablas.

## Consecuencias

- No hay que levantar ni operar una herramienta nueva
- El feature store depende de que Postgres esté arriba, igual que el resto del sistema
- Si el modelo creciera mucho o hubiera que servir en tiempo real con baja latencia, esta solución dejaría de alcanzar

## Qué queda fuera

No se usa Feast ni ningún feature store online/dedicado. No hay un "online store" separado del "offline store": es la misma tabla para todo.
