# ADR 0012 - Usar vistas SQL como semantic layer

## Estado

Aceptado.

## Contexto

La Fase 2 contempla una capa semántica simple. El objetivo es que un usuario o dashboard no tenga que conocer todo el modelo Gold para consultar métricas comunes.

En este proyecto, las métricas esperadas son bastante directas: producción mensual, producción por operadora, producción por área/yacimiento y frescura de datos.

## Problema

Si Metabase o cualquier herramienta de BI consulta directo las tablas Gold, cada dashboard puede terminar armando sus propias agregaciones. Eso aumenta el riesgo de que dos gráficos calculen distinto la misma métrica.

Necesitamos un lugar común donde queden definidas las métricas principales.

## Alternativas consideradas

### Consultar Gold directamente desde BI

Es simple y no requiere más modelos. El problema es que deja la lógica de negocio repartida en cada consulta o dashboard.

### Usar dbt Semantic Layer o Cube

Son alternativas más potentes para una capa semántica formal. Las descartamos porque agregan complejidad y no hacen falta para este alcance.

### Usar vistas SQL en PostgreSQL

La opción elegida fue crear vistas en el schema `semantic`. Es simple, transparente y alcanza para las métricas pedidas.

## Decisión

Se crean vistas SQL en la capa Semantic:

- `semantic.vw_produccion_mensual`
- `semantic.vw_produccion_por_operadora`
- `semantic.vw_produccion_por_area`
- `semantic.vw_frescura_datos`

Estas vistas se construyen desde Gold y dejan listas las agregaciones principales para BI.

## Consecuencias

La ventaja es que las métricas quedan centralizadas. Metabase o cualquier consumidor puede leer desde Semantic sin repetir lógica.

También hace más fácil validar conteos y explicar qué consulta debería usar un usuario no técnico.

La contra es que no es una semantic layer completa como herramienta dedicada. No hay catálogo de métricas avanzado ni control fino de permisos por métrica.

Para esta fase, nos parece suficiente porque el objetivo era dejar una capa clara, liviana y defendible.

## Fuera de alcance

No se implementa Cube, dbt Semantic Layer ni una herramienta adicional. Tampoco se modelan métricas complejas con dimensiones dinámicas. La capa semántica queda como vistas SQL versionadas en dbt.
