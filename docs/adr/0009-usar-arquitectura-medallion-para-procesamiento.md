# ADR 0009 - Usar arquitectura Medallion para procesamiento de datos

## Estado

Aceptado.

## Contexto

En esta fase entran datos públicos desde CSV de datos.gob.ar. El dato no llega listo para usar en un dashboard: primero hay que cargarlo, conservar evidencia de origen, limpiar tipos y después armar tablas más cómodas para análisis.

También necesitamos que el flujo sea explicable. Si mañana un conteo da raro, tiene que poder verse si el problema viene de la fuente, de la limpieza o del modelo final.

## Problema

Si mezclamos todo en una sola tabla, la solución sale más rápido, pero queda difícil de defender. No queda claro qué parte es dato crudo, qué parte está limpia y qué parte está pensada para BI.

Además, si un dato cambia o una transformación falla, no hay un lugar claro para revisar el paso anterior.

## Alternativas consideradas

### Una sola tabla final

Era la opción más rápida. Bajábamos el CSV, hacíamos las transformaciones y dejábamos todo en una tabla grande.

La descartamos porque mezcla ingesta, limpieza y análisis. Para una demo chica puede alcanzar, pero para esta adenda nos deja con poca trazabilidad.

### Bronze y Gold solamente

Otra opción era guardar el crudo en Bronze y pasar directo a Gold.

La descartamos porque falta una capa intermedia donde dejar datos limpios y tipados. Sin Silver, Gold queda haciendo demasiadas cosas al mismo tiempo.

### Bronze, Silver, Gold y Semantic

Esta opción separa mejor las responsabilidades. Bronze guarda evidencia de la fuente, Silver limpia y normaliza, Gold arma el modelo analítico y Semantic expone vistas listas para consumo.

## Decisión

Usamos arquitectura Medallion:

- `bronze`: datos crudos o casi crudos, con metadata de origen.
- `silver`: datos limpios, tipados y trazables.
- `gold`: modelo estrella para análisis.
- `semantic`: vistas SQL para consultas de BI.

## Consecuencias

La solución queda más larga que una tabla única, pero también queda más ordenada. Cada capa tiene un propósito concreto.

Esto ayuda a probar, explicar y depurar. Por ejemplo, si una métrica del dashboard está mal, se puede revisar si el error aparece en Gold, Silver o ya venía desde Bronze.

La contra es que hay más archivos y más pasos. Para esta entrega nos parece aceptable porque la separación por capas era parte importante de la adenda.

## Fuera de alcance

No armamos un data lake real ni almacenamiento en S3/Parquet. Todo queda en PostgreSQL porque alcanza para el alcance académico del TP.
