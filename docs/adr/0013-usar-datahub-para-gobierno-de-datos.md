# ADR 0013 - Usar DataHub para gobierno de datos

## Estado

Aceptado.

## Contexto

La adenda 2 pide una capa de gobierno de datos sobre el warehouse medallion (`bronze`, `silver`,
`gold`, `quality`, `metadata`, `semantic`). La idea es que cualquier integrante o un evaluador pueda
entender qué tablas existen, qué columnas tienen y cómo se relacionan, sin abrir el código de dbt ni
consultar Postgres a mano.

El warehouse ya está poblado por el pipeline (extracción a bronze, dbt para silver/gold/semantic,
checks de calidad). Falta un catálogo navegable que dé visibilidad de ese modelo.

## Problema

Sin un catálogo, el conocimiento del modelo de datos queda repartido entre el `data-contracts-2.md`,
los modelos de dbt y la cabeza de quien lo armó. Eso hace difícil:

- saber rápido qué tablas y columnas existen en cada capa;
- mostrar el modelo a alguien externo de forma autoexplicativa;
- tener un lugar único que represente la metadata del warehouse.

Necesitamos una herramienta de catálogo que ingiera la metadata de PostgreSQL y la exponga en una UI.

## Alternativas consideradas

### DataHub

Catálogo de datos open source con conector nativo a PostgreSQL, búsqueda, vista de columnas/tipos y
linaje. La contra es que es un stack pesado (Elasticsearch + Kafka + MySQL + GMS + frontend, ~8 GB
RAM), que no entra en el sandbox chico de la API.

### OpenMetadata

Funcionalmente parecido a DataHub y también open source. Igual de pesado en recursos. No aportaba
ventaja clara para el alcance del TP y el equipo no tenía experiencia previa con él.

### Amundsen

Más liviano que DataHub, pero su conector y su modelo de metadata son menos directos para una demo
rápida, y el proyecto tiene menos tracción que DataHub.

### dbt docs (o solo el data contract en Markdown)

`dbt docs generate` produce un sitio estático con el catálogo de los modelos de dbt, casi sin costo
de infraestructura. Lo descartamos como solución de gobierno porque solo cubre lo que pasa por dbt
(silver/gold/semantic) y no es una herramienta de gobierno: no ingiere bronze ni metadata externa,
ni ofrece búsqueda/linaje como un catálogo dedicado. Sirve como documentación complementaria, no como
la capa de governance pedida.

## Decisión

Se usa **DataHub** como herramienta de gobierno de datos, desplegado en una **instancia EC2 dedicada
y on-demand** (`t3.large`), separada del sandbox de la API.

La metadata del warehouse se ingiere con el conector PostgreSQL de DataHub mediante una receta
versionada (`datahub/recipe.postgres.yml`), que cataloga los seis schemas del modelo medallion. La
UI queda expuesta en el puerto `9002`.

El procedimiento completo de deploy, ingesta y operación está en
[docs/runbooks/datahub.md](../runbooks/datahub.md).

## Consecuencias

DataHub da un catálogo navegable de todo el warehouse, con búsqueda y vista de columnas/tipos por
tabla. Es un lugar único para entender el modelo sin leer código.

Como contrapartida, es un stack pesado: por eso no se integra al `docker-compose.yml` principal ni al
CI, y vive en su propia instancia, que se prende para la demo y se apaga para no gastar créditos. La
ingesta es manual (se corre la receta cuando hace falta refrescar el catálogo).

El despliegue en EC2 dedicada agrega un costo operativo (instancia paga, ~$0.08/h mientras corre),
mitigado apagando la instancia cuando no se usa.

## Fuera de alcance

No se implementa ingesta programada automática, SSO, control de acceso fino ni linaje column-level.
Tampoco alta disponibilidad ni componentes externos (Elasticsearch/Kafka gestionados): es un
quickstart single-node para sandbox académico, no una instalación productiva.
