# DataHub — gobierno de datos

DataHub cataloga la metadata del warehouse medallion (schemas, tablas, columnas) y la expone en una
UI navegable. Es el componente de gobierno de datos de la Adenda 2 (Integrante 3).

DataHub **no** se levanta con el `docker-compose.yml` del repo: es un stack pesado (~8 GB RAM) que
corre en una instancia EC2 dedicada y on-demand.

| Archivo | Qué es |
|---|---|
| `recipe.postgres.yml` | Receta de ingesta: lee la metadata del warehouse (`localhost:5433`) y la empuja a DataHub GMS (`localhost:8080`). |

- Decisión: [ADR 0013](../docs/adr/0013-usar-datahub-para-gobierno-de-datos.md).
- Procedimiento completo (lanzar EC2, levantar DataHub, ingerir, validar, apagar): [docs/runbooks/datahub.md](../docs/runbooks/datahub.md).

Comando de ingesta (desde la EC2, con el venv de `acryl-datahub` activo):

```bash
datahub ingest -c datahub/recipe.postgres.yml
```
