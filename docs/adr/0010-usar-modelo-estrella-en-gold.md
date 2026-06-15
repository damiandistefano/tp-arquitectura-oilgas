# ADR 0010 - Usar modelo estrella en Gold

## Estado

Aceptado.

## Contexto

La capa Gold tiene que servir para consultas analíticas. Las preguntas esperadas son cosas como producción mensual, producción por operadora, producción por área/yacimiento y cantidad de pozos con producción.

Para eso no conviene que Gold sea solo una copia limpia del CSV. Tiene que tener una estructura pensada para leer métricas.

## Problema

La fuente trae muchas columnas mezcladas: algunas son medidas, como producción de gas o petróleo, y otras describen entidades, como pozo, operadora, área o yacimiento.

Si dejamos todo junto, se puede consultar, pero el modelo queda más desprolijo. También cuesta explicar cuál es el grano de los datos y qué significa cada fila.

## Alternativas consideradas

### One Big Table

La opción más simple era una tabla grande con todo.

Tiene la ventaja de que se consulta fácil al principio. La desventaja es que repite datos descriptivos y termina mezclando medidas con atributos. Para BI puede servir, pero no es tan claro como modelo final.

### Modelo muy normalizado

También se podía hacer un modelo más parecido a base transaccional, con varias tablas normalizadas.

Lo descartamos porque no es lo más cómodo para análisis. Requiere más joins y no suma demasiado para este caso.

### Modelo estrella

La opción elegida fue separar una fact table con medidas y varias dimensiones descriptivas.

Esto deja más claro qué se mide y desde qué dimensiones se analiza.

## Decisión

Usamos modelo estrella en Gold.

Tabla de hechos:

- `gold.fact_produccion_pozo`

Grano:

- una fila por registro de producción de un pozo en un período mensual.

Dimensiones:

- `gold.dim_fecha`
- `gold.dim_pozo`
- `gold.dim_operadora`
- `gold.dim_area`
- `gold.dim_yacimiento`

## Consecuencias

El modelo queda más claro para BI y más fácil de explicar. Las métricas viven en la fact table y los datos descriptivos viven en dimensiones.

También permite agregar checks de calidad más concretos, como validar que cada fila de la fact tenga pozo, fecha y operadora relacionados.

La contra es que hay que mantener más modelos dbt. Para esta fase nos parece razonable porque la consigna pide una capa Gold analítica.

## Surrogate keys y SCD

Las claves surrogate se generan con `md5` sobre identificadores naturales de la fuente.

Para las dimensiones se usa SCD tipo 1. No implementamos SCD tipo 2 porque la fuente no garantiza historial confiable de cambios de atributos. Meter SCD tipo 2 ahora sería más complejo de defender que útil.
