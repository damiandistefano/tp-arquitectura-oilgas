# ADR 0013 - Usar DataHub para gobierno de datos

## Estado

Aceptado.

## Contexto

Adenda 2 pide una plataforma de gobierno de datos en la cual se puedan navegar datasets, metadata y linaje a nivel tabla. El warehouse del proyecto ya organiza los datos en capas `bronze`, `silver`, `gold`, `quality`, `metadata` y `semantic`.

Sin un catalogo, la informacion sobre tablas, columnas y responsables queda repartida entre dbt, contratos Markdown, runbooks y consultas manuales a PostgreSQL. Para una defensa del TP hace falta una UI donde se pueda mostrar el modelo sin entrar al codigo.

## Problema

Necesitamos una herramienta de catalogo que permita:

- buscar datasets del warehouse;
- ver schemas, columnas y tipos;
- explicar el alcance de cada capa;
- mostrar linaje a nivel tabla o, como minimo, la navegacion del catalogo por capas;
- sostener una decision de governance sin prometer una plataforma productiva.

## Alternativas consideradas

### DataHub

DataHub es una herramienta open source de metadata management y data governance. Tiene conector PostgreSQL, UI de catalogo, busqueda, metadata tecnica y soporte de lineage. La contra es operacional: el quickstart levanta varios servicios y requiere mas memoria que el sandbox chico.

### OpenMetadata

OpenMetadata cubre un problema similar y tambien tiene conectores. Para este TP no ofrece una ventaja clara frente a DataHub, y suma una curva de aprendizaje parecida.

### Amundsen

Amundsen es mas simple como catalogo, pero su ecosistema y conectores resultan menos directos para esta entrega. Tambien quedaria corto frente al requerimiento de lineage.

### dbt Docs + documentacion Markdown

dbt Docs es liviano y muy util para modelos dbt, columnas, tests y lineage tecnico. Sin embargo, no cubre todo el warehouse como plataforma de gobierno: Bronze, metadata operacional y calidad quedan mejor representadas si se catalogan desde PostgreSQL.

## Decision

Usar DataHub como herramienta de gobierno de datos, desplegada en una EC2 dedicada y on-demand para la demo.

DataHub no se integra al `docker-compose.yml` principal porque su stack es pesado. La metadata se ingiere con la receta versionada [`datahub/recipe.postgres.yml`](../../datahub/recipe.postgres.yml), que cataloga los schemas:

- `bronze`
- `silver`
- `gold`
- `quality`
- `metadata`
- `semantic`

La UI queda expuesta en el puerto `9002`. El procedimiento esta documentado en [docs/runbooks/datahub.md](../runbooks/datahub.md).

## Consecuencias

La entrega gana un catalogo navegable de los datasets del warehouse y una forma concreta de explicar discovery, metadata y governance.

El costo es operativo: DataHub requiere una instancia mas grande que el sandbox de la API y debe prenderse solo para validar o mostrar la demo. La ingesta de metadata es manual: cuando cambia el warehouse, se vuelve a correr `datahub ingest -c datahub/recipe.postgres.yml`.

## Que queda fuera

No se implementan SSO, RBAC fino, alta disponibilidad, scheduling automatico de ingesta, data contracts nativos de DataHub ni linaje column-level productivo. El alcance es academico: catalogo, metadata tecnica y evidencia de gobierno de datos para la entrega.
