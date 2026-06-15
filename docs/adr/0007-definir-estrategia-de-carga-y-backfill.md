# ADR 0007 — Estrategia de carga y backfill

## Estado
Aceptado

## Contexto

Las fuentes son dos CSV públicos de datos.gob.ar (producción no convencional y pozos operadoras). Cada vez que corre el pipeline hay que descargar esos archivos, cargarlos en Bronze y después transformar a Silver y Gold. Hay que decidir cómo manejar corridas repetidas (idempotencia) y cómo reprocesar datos si algo salió mal.

## Problema

Sin una estrategia clara:
- Correr el pipeline dos veces duplica filas en Bronze
- Si falla una corrida a mitad, no queda claro qué se cargó y qué no
- No hay forma de reprocesar un rango de fechas sin intervención manual

## Alternativas consideradas

**Incremental append real (CDC / updated_at)**
- Solo descargamos filas nuevas o modificadas desde la última corrida
- Requiere que la fuente exponga un campo `updated_at` confiable o un endpoint incremental
- Los CSV de datos.gob.ar no tienen esto — el archivo completo se publica como un dump
- Implementar incremental falso (comparar por hash de fila) es complejo y frágil

**Truncate y reload completo**
- Borramos todo Bronze en cada corrida y recargamos desde cero
- Simple, pero perdemos el historial de corridas y no hay forma de auditar qué había antes
- No cumple el requisito de mantener evidencia de la fuente

**Full download + Bronze append-only con hash de archivo**
- Descargamos el CSV completo cada corrida
- Antes de cargar, calculamos el hash del archivo
- Si el hash ya existe en `metadata.source_files`, saltamos esa fuente (idempotencia)
- Si el hash es nuevo, insertamos todas las filas con el `run_id` de esta corrida
- Bronze acumula corridas históricas — si la fuente cambió, tenemos ambas versiones

Esta es la opción elegida porque las fuentes no ofrecen incrementales y queremos mantener trazabilidad.

## Decisión

Full download en cada corrida, Bronze append-only. La deduplicacion se hace por hash del archivo completo a nivel de fuente. Si el hash ya fue cargado, esa fuente se saltea y no se insertan filas duplicadas en Bronze.

Silver, Gold y Semantic se reconstruyen de forma idempotente desde Bronze con `dbt build`. En este proyecto los modelos Silver/Gold estan materializados como tablas y las vistas Semantic se recrean desde esas tablas, por lo que volver a correr dbt deja el mismo resultado para la misma entrada.

Para backfill/reproceso: el script `scripts/backfill.sh` recibe una fecha o rango como intencion operativa, descarga nuevamente los CSV publicos disponibles y reconstruye los modelos downstream para todos los periodos presentes en la fuente. No es un backfill particionado fino, porque la fuente publica no expone un endpoint incremental confiable por fecha.

## Consecuencias

- Correr el pipeline dos veces con el mismo CSV no inserta filas duplicadas en Bronze
- Si el CSV cambia (la fuente actualiza datos), la nueva versión entra en Bronze como una corrida nueva
- Bronze crece con el tiempo — para este alcance académico no es problema
- No hay CDC ni detección de cambios a nivel fila — aceptable dado que la fuente no lo ofrece
- El hash se calcula sobre el archivo completo, no por fila, lo que es rápido pero no detecta cambios parciales dentro de un mismo archivo descargado en el mismo día
- El reproceso por fecha queda documentado como reconstruccion batch de downstream, no como particionamiento real por dia/mes

## Qué queda fuera

No implementamos comparación de filas individuales ni staging incremental. Si en el futuro la fuente expone un endpoint con filtro por fecha, habría que revisar esta decisión.
