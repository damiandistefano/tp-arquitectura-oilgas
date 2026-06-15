# Runbook: DataHub en EC2

Este runbook describe como operar DataHub para la entrega de Adenda 2. DataHub cataloga la metadata del warehouse PostgreSQL y permite mostrar datasets, schemas, columnas y gobierno de datos desde una UI.

DataHub no corre en el `docker-compose.yml` principal porque es un stack pesado. Para la demo se usa una EC2 dedicada y on-demand.

---

## 1. Alcance de la demo

DataHub debe mostrar metadata de estos schemas:

| Schema | Que se espera ver |
|---|---|
| `bronze` | Tablas raw y columnas de trazabilidad como `_run_id`, `_source_file_hash`, `_ingested_at`. |
| `silver` | Tablas limpias y tipadas. |
| `gold` | `fact_produccion_pozo` y dimensiones. |
| `quality` | `data_quality_results`. |
| `metadata` | `pipeline_runs` y `source_files`. |
| `semantic` | Vistas usadas por Metabase. |

El objetivo no es mostrar gobierno enterprise, sino discovery, catalogo, metadata tecnica y linaje defendible para el TP.

---

## 2. Recursos

Configuracion probada para el quickstart:

| Recurso | Valor |
|---|---|
| Instancia | EC2 `t3.large` |
| RAM | 8 GB |
| Swap | 2 GB |
| Disco | 30 GB `gp3` |
| UI publica | `9002` |
| GMS interno | `8080` |

No exponer `8080` publicamente. La ingesta lo usa desde la misma EC2.

Nota de costo: DataHub quickstart levanta varios contenedores y no es comodo en `t3.micro`. Para esta entrega se justifica `t3.large` como instancia dedicada y on-demand, prendida solo para validar o grabar la demo. No usar este tamaño como referencia para el sandbox de API si solo se muestra Fase 1.

---

## 3. Levantar la EC2

1. Prender la instancia dedicada de DataHub.
2. Confirmar que el Security Group permita:
   - SSH `22` desde la IP del equipo;
   - TCP `9002` desde la IP desde la cual se va a grabar o mostrar la demo.
3. Conectarse por SSH con la llave correspondiente, sin commitear la llave al repo.

```bash
ssh -i datahub-oilgas.pem ubuntu@3.143.210.125
```

IP publica vigente de la entrega: `3.143.210.125` (instancia mantenida encendida durante la correccion). Si en el futuro se apaga y prende sin Elastic IP, la IP publica puede cambiar; en ese caso actualizar este runbook y el README.

---

## 4. Validar prerequisitos del host

```bash
free -h
sudo sysctl vm.max_map_count
docker ps
```

Esperado:

- swap de 2 GB activo;
- `vm.max_map_count = 262144`;
- Docker disponible sin `sudo`;
- no levantar cAdvisor en esta EC2, porque DataHub GMS usa `8080`.

---

## 5. Levantar warehouse en la EC2

Desde el repo clonado en la EC2:

```bash
git fetch --tags
git checkout v0.2.0
cp .env.example .env
docker compose up -d postgres
docker compose ps
```

Esperado: `warehouse-postgres` healthy y expuesto en `localhost:5433`.

---

## 6. Poblar el warehouse

Con entorno Python del pipeline activo:

```bash
python -m extract.load_to_bronze
dbt build --project-dir dbt
python -m quality.checks
```

Validar que existan filas:

```bash
docker compose exec -T postgres psql -U dwh -d warehouse -c "\dt bronze.*"
docker compose exec -T postgres psql -U dwh -d warehouse -c "\dt gold.*"
docker compose exec -T postgres psql -U dwh -d warehouse -c "\dv semantic.*"
```

---

## 7. Levantar DataHub

El metodo normal es `datahub docker quickstart`, pero en esta EC2 el disco es acotado (28 GB) y el CLI aborta porque exige 13 GB libres ("Total Docker disk space available ... below the minimum threshold 13GB"). El flag `--no-pull-images` no saltea ese chequeo.

Como las imagenes de DataHub ya estan bajadas, se levanta el compose cacheado del quickstart directamente (saltea el chequeo de disco del CLI):

```bash
cd ~/.datahub/quickstart
COMPOSE_PROFILES=quickstart DATAHUB_VERSION=v1.5.0.6 \
  docker compose -p datahub -f docker-compose.yml --env-file .local-secrets.env up -d --pull never
```

Si Elasticsearch/OpenSearch no arranca, ajustar el kernel antes: `sudo sysctl -w vm.max_map_count=262144`.

Validar (desde dentro de la EC2):

```bash
curl -f http://localhost:9002/admin
curl -f http://localhost:8080/health
```

Para que DataHub sobreviva reinicios de la instancia, dejar los contenedores con restart automatico:

```bash
docker update --restart unless-stopped $(docker ps --filter "name=datahub-" -q) warehouse-postgres
```

La UI queda en:

```text
http://3.143.210.125:9002
```

Credenciales por defecto:

```text
usuario: datahub
password: datahub
```

---

## 8. Ingerir metadata de PostgreSQL

Desde la raiz del repo en la EC2:

```bash
source ~/datahub-venv/bin/activate
datahub ingest -c datahub/recipe.postgres.yml
```

La receta lee `localhost:5433` y publica en `localhost:8080`.

Si la ingesta devuelve 0 tablas:

- confirmar que el warehouse tiene tablas y vistas;
- confirmar que `docker compose ps` muestra Postgres healthy;
- revisar `datahub/recipe.postgres.yml`;
- volver a correr la ingesta.

---

## 9. Validacion UI para la entrega

En `http://3.143.210.125:9002`:

1. Login con `datahub` / `datahub`.
2. Buscar `produccion`.
3. Abrir `gold.fact_produccion_pozo`.
4. Ver columnas y tipos.
5. Buscar datasets de `bronze`, `silver`, `gold`, `quality`, `metadata` y `semantic`.
6. Abrir alguna vista `semantic.vw_*`.
7. Mostrar que DataHub funciona como catalogo navegable del warehouse.

Evidencia minima para la defensa:

- pantalla de login o home de DataHub;
- busqueda con tablas del warehouse;
- detalle de `gold.fact_produccion_pozo`;
- datasets de al menos tres capas;
- si aparece lineage en la UI, mostrarlo; si no, explicar que el linaje tecnico principal tambien esta en dbt Docs y que DataHub se usa como catalogo de governance.

---

## 10. Apagar para no gastar creditos

Para la entrega la instancia se mantiene **encendida** durante toda la ventana de correccion, asi el profe puede abrir `http://3.143.210.125:9002` cuando quiera.

Una vez terminada la correccion, apagar para no gastar creditos:

```bash
# desde AWS Console: Instance state -> Stop instance
```

No terminar la instancia si se quiere conservar los volumenes y el catalogo para la presentacion. Con `restart: unless-stopped` (paso 7) DataHub se vuelve a levantar solo cuando se prende de nuevo.

---

## 11. Troubleshooting

### DataHub se queda sin memoria

- Confirmar swap: `free -h`.
- Confirmar que no se levanto el stack completo de monitoreo.
- Revisar `docker stats`.

### Elasticsearch no arranca

```bash
sudo sysctl -w vm.max_map_count=262144
```

### No abre la UI desde el navegador

- Revisar que `curl -f http://localhost:9002/admin` funcione dentro de la EC2.
- Revisar Security Group para puerto `9002`.
- Confirmar IP publica vigente.

### El comando `datahub` no existe

```bash
source ~/datahub-venv/bin/activate
datahub version
```

### La ingesta no encuentra tablas

```bash
docker compose exec -T postgres psql -U dwh -d warehouse -c "\dn"
docker compose exec -T postgres psql -U dwh -d warehouse -c "\dt gold.*"
```

Si faltan tablas, correr de nuevo Bronze, dbt y calidad antes de ingerir metadata.
