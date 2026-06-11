# ADR 0008 — Usar PostgreSQL como warehouse local

## Estado
Aceptado

## Contexto

Necesitamos un lugar donde guardar los datos de Bronze, Silver, Gold, calidad y metadata de corridas. El stack corre en una EC2 con Docker Compose. Los datos son CSV de tamaño moderado (producción de pozos, algunos cientos de miles de filas).

## Problema

Elegir dónde guardar los datos afecta qué herramientas podemos usar (dbt, Metabase, DataHub), cuánta complejidad operacional agregamos y si el stack levanta cómodo en una instancia chica.

## Alternativas consideradas

**Archivos Parquet / S3 + DuckDB**
- Patrón común en data lakes modernos
- DuckDB es muy rápido para consultas analíticas sobre archivos locales
- Metabase no se conecta directamente a Parquet/DuckDB en self-hosted sin configuración especial
- DataHub necesita una fuente de metadatos estructurada — con archivos planos es más difícil de integrar
- Agrega complejidad operacional (gestión de archivos, particiones) que no aporta valor en este alcance

**SQLite**
- Cero configuración, corre en el mismo proceso
- No soporta múltiples conexiones concurrentes bien (Dagster + dbt + Metabase conectados al mismo tiempo)
- No tiene schemas, lo que complica separar Bronze/Silver/Gold/metadata
- dbt tiene soporte limitado para SQLite

**BigQuery / Snowflake / Redshift**
- Son warehouses cloud gestionados, muy buenos para producción
- Requieren cuenta de pago o créditos
- No tienen sentido para un sandbox académico local
- Complican el onboarding del equipo

**PostgreSQL**
- Soporta schemas nativamente: bronze, silver, gold, quality, metadata, semantic
- dbt tiene soporte oficial y maduro para Postgres
- Metabase se conecta directamente sin configuración extra
- DataHub tiene conector de ingestion para Postgres
- Corre bien en Docker con poca RAM
- El equipo ya lo conoce de materias anteriores

## Decisión

Usamos PostgreSQL 16 como warehouse. Corre como contenedor Docker en el puerto 5433 (para no pisar instalaciones locales en el 5432). Los schemas se crean al inicializar el contenedor con los scripts de `postgres-init/`.

## Consecuencias

- dbt, Metabase y DataHub se conectan todos al mismo Postgres — sin fricciones de integración
- Los schemas separan claramente cada capa del medallion
- Postgres no es un warehouse columnar, así que para datasets muy grandes (millones de filas con muchas columnas) puede ser lento en queries analíticas pesadas
- Para el volumen de datos de este proyecto (pozos de producción Argentina) el rendimiento es más que suficiente
- Backup y persistencia se manejan con un volumen Docker — si se borra el volumen se pierden los datos, hay que volver a correr el pipeline

## Qué queda fuera

No configuramos réplicas, pooling de conexiones ni backups automáticos. Es un sandbox académico, no un sistema productivo.
