# DataHub - gobierno de datos

DataHub cataloga la metadata del warehouse medallion y la expone en una UI navegable. Es el componente de gobierno de datos de Adenda 2.

DataHub no se levanta con el `docker-compose.yml` principal del repo porque el stack es pesado. Corre en una EC2 dedicada y on-demand para la demo.

| Archivo | Uso |
|---|---|
| `recipe.postgres.yml` | Receta de ingesta: lee metadata del warehouse PostgreSQL en `localhost:5433` y la publica en DataHub GMS en `localhost:8080`. |

Referencias:

- Decision: [ADR 0013](../docs/adr/0013-usar-datahub-para-gobierno-de-datos.md).
- Operacion: [docs/runbooks/datahub.md](../docs/runbooks/datahub.md).

Comando de ingesta desde la EC2, con el venv de `acryl-datahub` activo:

```bash
datahub ingest -c datahub/recipe.postgres.yml
```
