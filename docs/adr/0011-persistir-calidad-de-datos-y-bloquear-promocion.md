# ADR 0011 - Persistir calidad de datos y bloquear promoción ante fallas críticas

## Estado

Aceptado.

## Contexto

La adenda pide que la calidad de datos no sea solo un mensaje por consola. Tiene que quedar evidencia de qué se chequeó, cuándo corrió, qué falló y si el problema era crítico o no.

Además, si aparece una falla grave, el pipeline no debería seguir como si nada.

## Problema

Un `print` o un test que falla localmente no alcanza para operar el pipeline. Si alguien mira el estado después, necesita ver los resultados persistidos.

También necesitamos diferenciar entre errores que bloquean y alertas que solo avisan. No todo problema debería cortar el flujo, pero algunos sí.

## Alternativas consideradas

### Solo usar tests de dbt

Los tests de dbt sirven y ya los usamos, pero no dejan una tabla propia con el historial de resultados. Son buenos para validar modelos, pero no cubren toda la parte operativa que pide la adenda.

### Usar Great Expectations

Great Expectations es más completo para calidad de datos. Lo descartamos para esta fase porque agrega bastante configuración y otra herramienta más al stack. Para el alcance del TP era demasiado.

### Implementar checks propios en Python

La opción elegida fue hacer checks simples en Python y persistir los resultados en PostgreSQL.

No es la solución más sofisticada, pero es clara, corre localmente y se puede enganchar desde un orquestador como Dagster.

## Decisión

Se implementa una tabla:

- `quality.data_quality_results`

Y un script:

- `scripts/run-quality-checks.sh`

Los checks guardan:

- nombre del check;
- capa evaluada;
- tabla evaluada;
- dimensión de calidad;
- estado;
- severidad;
- filas revisadas;
- filas fallidas;
- detalle en JSON;
- timestamp de ejecución.

## Checks incluidos

Checks críticos:

- columnas esperadas existen;
- campos críticos no nulos;
- `produccion_id` único;
- metadata de lineage no nula;
- fact table con dimensiones relacionadas.

Check no crítico:

- frescura del último período disponible.

## Consecuencia operativa

Si falla un check con severidad `CRITICAL`, el script termina con exit code distinto de cero.

Eso permite que Dagster u otro orquestador marque la tarea como fallida. La idea es que una corrida con errores críticos no quede promovida como válida.

Si solo hay `WARNING`, la ejecución puede seguir, pero el problema queda registrado.

## Consecuencias

La ventaja es que la calidad queda visible y trazable en una tabla. También se puede consultar desde BI o desde un runbook.

La contra es que los checks están escritos a mano. Si el proyecto creciera, probablemente convendría evaluar una herramienta más completa.
