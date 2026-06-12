# Runbook: DataHub (gobierno de datos) en EC2

Este documento describe cómo levantar **DataHub** como catálogo / gobierno de datos del warehouse
del proyecto, en una instancia EC2 **dedicada y on-demand**.

DataHub no corre en el sandbox chico de la API (Fase 1). Es un stack pesado y se monta aparte, en su
propia instancia, que se prende para la demo y se apaga para no gastar créditos.

---

## 1. Qué hace y qué mostramos en la demo

DataHub ingiere la **metadata** del warehouse PostgreSQL (no los datos, solo el catálogo: schemas,
tablas, columnas y tipos) y la expone en una UI navegable en el puerto `9002`.

Para la entrega, DataHub catologa las capas del modelo medallion:

| Schema | Qué se ve en el catálogo |
|---|---|
| `bronze` | `raw_produccion_no_convencional`, `raw_pozos_operadoras` + columnas de trazabilidad (`_run_id`, `_source_*`, `_ingested_at`). |
| `silver` | tablas limpias y tipadas. |
| `gold` | `fact_produccion_pozo` + dimensiones (`dim_pozo`, `dim_fecha`, `dim_operadora`, `dim_area`, `dim_yacimiento`). |
| `quality` | `data_quality_results`. |
| `metadata` | `pipeline_runs`, `source_files`. |
| `semantic` | vistas con métricas oficiales. |

La decisión de usar DataHub está documentada en [ADR 0013](../adr/0013-usar-datahub-para-gobierno-de-datos.md).

---

## 2. Recursos y costos (leer antes de lanzar nada)

DataHub quickstart pide, como mínimo probado: **2 vCPU, 8 GB RAM, 2 GB de swap y ~12 GB de disco**.
Eso descarta el free tier (`t2.micro` / `t3.small`).

| Item | Valor elegido | Por qué |
|---|---|---|
| Instancia | `t3.large` (2 vCPU, 8 GB) | Es el mínimo tested. `t3.xlarge` (16 GB) es más cómodo pero gasta el doble. |
| Disco EBS | 30 GB `gp3` | Las imágenes de DataHub + Elasticsearch ocupan bastante; 8 GB no alcanza. |
| Swap | 2 GB | **Obligatorio.** Sin swap, DataHub se queda sin memoria y los contenedores mueren (OOM). |

**Costo aproximado** (`us-east-1`, junio 2026): `t3.large` ≈ **$0.083/h** mientras corre. Apagada
(stopped) solo pagás el disco EBS: 30 GB `gp3` ≈ **$2.4/mes**.

> Regla de oro para cuidar créditos: **prendé la instancia solo cuando trabajás o demostrás, y
> apagala (`stop`) cuando terminás.** No la dejes corriendo de un día para el otro.

---

## 3. Topología elegida

EC2 dedicada y self-contained: el warehouse y DataHub viven en la misma instancia, y la ingesta
corre desde el host apuntando a `localhost`. No hay networking entre instancias.

```text
┌─────────────────────────── EC2 t3.large (dedicada) ──────────────────────────┐
│                                                                              │
│  docker compose up -d postgres        datahub docker quickstart              │
│  ┌─────────────────────────┐          ┌──────────────────────────────────┐  │
│  │ warehouse-postgres :5433 │          │ datahub-frontend  :9002 (UI)     │  │
│  │  bronze / silver / gold  │          │ datahub-gms       :8080 (API)    │  │
│  │  quality / metadata / sem│          │ elasticsearch / kafka / mysql    │  │
│  └────────────▲────────────┘          └─────────────▲────────────────────┘  │
│               │                                      │                       │
│               │   datahub ingest -c recipe.yml       │                       │
│               └──────────────(desde el host)─────────┘                       │
└──────────────────────────────────────────────────────────────────────────────┘
        Puerto público: 9002 (UI DataHub). 22 SSH restringido a tu IP.
```

No se levanta el stack de monitoreo (API, Grafana, Prometheus, cAdvisor) en esta instancia: solo
`postgres`. Importante, porque cAdvisor usa el `8080`, que acá lo necesita DataHub GMS.

---

## 4. Paso 1 — Lanzar la instancia EC2 (desde cero)

En la consola de AWS → **EC2** → **Launch instance**:

1. **Name**: `datahub-oilgas`.
2. **AMI**: Ubuntu Server 24.04 LTS (x86_64).
3. **Instance type**: `t3.large`.
4. **Key pair**: crear uno nuevo (`datahub-oilgas.pem`), descargarlo y guardarlo. Es la llave SSH;
   no se commitea nunca.
5. **Network settings → Edit → Security group** (crear uno nuevo, ej. `datahub-sg`):
   | Type | Port | Source | Uso |
   |---|---|---|---|
   | SSH | `22` | My IP | conexión administrativa, restringida a tu IP. |
   | Custom TCP | `9002` | My IP (o Anywhere si la demo es remota) | UI de DataHub. |

   El `8080` (GMS) **no** se expone público: la ingesta lo usa desde el mismo host.
6. **Configure storage**: 30 GiB, `gp3`.
7. **Launch instance**.

Anotá la **IP pública** de la instancia (cambia cada vez que la apagás y prendés, salvo que asignes
una Elastic IP — no hace falta para la demo).

Permisos de la llave en tu máquina local:

```bash
chmod 400 datahub-oilgas.pem
```

---

## 5. Paso 2 — Preparar el servidor

Conectarse:

```bash
ssh -i datahub-oilgas.pem ubuntu@<IP_PUBLICA>
```

### 5.1 Swap de 2 GB (obligatorio)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h    # verificar que aparezca Swap: 2.0Gi
```

### 5.2 Parámetro de kernel para Elasticsearch

Elasticsearch no arranca si `vm.max_map_count` es bajo:

```bash
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee /etc/sysctl.d/99-datahub.conf
```

### 5.3 Docker + Compose

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 python3-pip python3-venv git
sudo usermod -aG docker ubuntu
# cerrar y reabrir la sesión SSH para que tome el grupo docker
exit
```

Reconectar y verificar:

```bash
ssh -i datahub-oilgas.pem ubuntu@<IP_PUBLICA>
docker ps        # no debe pedir sudo
```

### 5.4 CLI de DataHub

```bash
python3 -m venv ~/datahub-venv
source ~/datahub-venv/bin/activate
pip install --upgrade pip
pip install 'acryl-datahub[datahub-rest,postgres]'
datahub version
```

> Tip: agregá `source ~/datahub-venv/bin/activate` cuando reconectes, para tener el comando `datahub`.

---

## 6. Paso 3 — Poblar el warehouse

Clonar el repo y levantar **solo** Postgres (no el stack completo). La plataforma de datos vive en
`develop`; `main` solo tiene la API de Fase 1, así que hay que clonar esa rama:

```bash
git clone -b develop https://github.com/damiandistefano/tp-arquitectura-oilgas.git
cd tp-arquitectura-oilgas
cp .env.example .env       # el .env.example de develop trae POSTGRES_* y las SOURCE_URL
docker compose up -d postgres
docker compose ps          # warehouse-postgres debe estar (healthy)
```

> Si clonás sin `-b develop` vas a obtener `main` y `docker compose up -d postgres` falla con
> `no such service: postgres`.

Correr el pipeline para que existan las tablas en todas las capas (ver detalle en
[docs/delivery-checklist.md §2](../delivery-checklist.md)):

```bash
# venv para el pipeline (Ubuntu 24.04 bloquea el pip global)
python3 -m venv ~/pipeline-venv
source ~/pipeline-venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt        # extract + dbt + quality

# exportar las variables del .env y apuntar al warehouse en el host
set -a; source .env; set +a
export POSTGRES_HOST=localhost             # extract/quality corren en el host, no en la red Docker

python -m extract.load_to_bronze           # bronze
mkdir -p ~/.dbt && cp dbt/profiles.example.yml ~/.dbt/profiles.yml
dbt run --project-dir dbt/                 # silver / gold / semantic
python -m quality.checks                   # quality.data_quality_results
```

> Dos detalles del entorno EC2:
> - `extract` y `quality` leen la conexión de variables de entorno (`build_conninfo`), con default
>   `postgres:5432` pensado para la red Docker. Corriendo en el host hay que exportar el `.env` y
>   pisar `POSTGRES_HOST=localhost` (el puerto `5433` ya viene del `.env`).
> - El `profiles.yml` de dbt ya apunta a `localhost:5433`, así que no necesita variables extra.

Si solo querés mostrar la **estructura** del catálogo y no te importa que las tablas tengan filas,
alcanza con `docker compose up -d postgres` + `dbt run` (crea las tablas vacías). Para una demo
completa, corré el pipeline entero.

---

## 7. Paso 4 — Levantar DataHub

```bash
source ~/datahub-venv/bin/activate
datahub docker quickstart
```

El comando descarga las imágenes y levanta el stack completo de DataHub (frontend, GMS,
Elasticsearch, Kafka, MySQL, actions). La primera vez tarda varios minutos.

Cuando termina, la UI queda en:

```text
http://<IP_PUBLICA>:9002
```

Credenciales por defecto: usuario `datahub` / password `datahub`.

Estado de los contenedores:

```bash
datahub docker check
docker ps
```

---

## 8. Paso 5 — Ingerir la metadata del warehouse

La receta de ingesta está versionada en el repo: [`datahub/recipe.postgres.yml`](../../datahub/recipe.postgres.yml).
Conecta al warehouse en `localhost:5433` (source) y empuja a DataHub GMS en `localhost:8080` (sink),
todo desde el host, así que no hay líos de red entre contenedores.

```bash
source ~/datahub-venv/bin/activate
cd ~/tp-arquitectura-oilgas
datahub ingest -c datahub/recipe.postgres.yml
```

Al terminar imprime un resumen (`workunits produced`, `entities`). Si dice `0 tables`, revisá que el
pipeline del Paso 3 haya creado tablas (ver Troubleshooting).

Para refrescar el catálogo después de un cambio en el warehouse, se vuelve a correr el mismo comando.

---

## 9. Paso 6 — Validar

En la UI (`http://<IP_PUBLICA>:9002`):

1. Login `datahub` / `datahub`.
2. **Datasets** → fuente `postgres` → debería listar los 6 schemas (`bronze`, `silver`, `gold`,
   `quality`, `metadata`, `semantic`).
3. Abrir `gold.fact_produccion_pozo` → ver columnas, tipos y descripción.
4. Probar la búsqueda: buscar `produccion` y confirmar que aparecen tablas de varias capas.

Validación rápida por consola:

```bash
curl -f http://localhost:9002/admin            # frontend arriba
curl -f http://localhost:8080/health           # GMS arriba
```

Esto es lo que se muestra el día de la demo: el catálogo navegable de las capas del warehouse.

---

## 10. Operación y costos

**Apagar para no gastar créditos** (la data y el catálogo quedan en el disco EBS):

```bash
# desde la consola de AWS: Instance state → Stop instance
```

**Volver a prender**: Start instance (la IP pública cambia). Reconectar por SSH y, si los
contenedores no levantaron solos:

```bash
cd ~/tp-arquitectura-oilgas
docker compose up -d postgres
source ~/datahub-venv/bin/activate
datahub docker quickstart      # reusa los volúmenes existentes
```

**Destruir todo** (cuando ya no se necesita, para no pagar ni el EBS):

```bash
# en la EC2, opcional, limpia los contenedores de datahub:
datahub docker nuke
# después, en la consola AWS: Terminate instance (borra también el volumen EBS).
```

---

## 11. Troubleshooting

### Contenedores de DataHub se reinician / mueren (OOM)
- Confirmar que el swap está activo: `free -h` debe mostrar `Swap: 2.0Gi`.
- Confirmar que **no** está corriendo el stack de monitoreo (solo `postgres`): `docker ps`.
- Revisar memoria: `docker stats`. Elasticsearch es el que más consume.

### Elasticsearch no arranca
- `sudo sysctl vm.max_map_count` debe dar `262144`. Si no, repetir el Paso 5.2.

### Puerto 8080 ocupado
- Pasa si se levantó el stack completo (cAdvisor usa 8080). Bajar todo menos postgres:
  `docker compose down` y después `docker compose up -d postgres`.

### `datahub ingest` reporta 0 tablas
- Verificar que el pipeline creó tablas:
  ```bash
  docker exec -it warehouse-postgres \
    psql -U dwh -d warehouse -c "\dt bronze.*; \dt gold.*"
  ```
- Confirmar que la receta apunta a `localhost:5433` y credenciales `dwh`/`dwh`.

### No entra la UI desde afuera
- Security Group: el puerto `9002` debe estar abierto a tu IP.
- La IP pública cambió tras un stop/start: usar la nueva.

### El comando `datahub` no existe tras reconectar
- Activar el venv: `source ~/datahub-venv/bin/activate`.
- Si además se perdió `uv`/`~/.local/bin` del PATH (pasa al hacer `deactivate`): `source ~/.local/bin/env`.

### `pip install` falla con `No matching distribution found for psycopg-binary`
- El pin `psycopg[binary]==3.2.9` quedó sin wheel binario en PyPI. Usar una versión disponible:
  `pip install 'psycopg[binary]>=3.2.10'`, o bumpear el pin en `requirements.txt` (ya corregido a
  `==3.2.10`; si la rama clonada todavía tiene `3.2.9`, aplicar el bump).

### `dbt run` rompe con `mashumaro ... is not serializable`
- dbt 1.9 no soporta Python ≥ 3.13. Aparece en AMIs muy nuevas: Ubuntu 25.10 / 26.04 traen Python
  3.14 por defecto. La solución es recrear el venv del pipeline con Python 3.12 usando `uv`, que baja
  el intérprete sin depender de apt/deadsnakes:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  uv venv --python 3.12 ~/pipeline-venv
  source ~/pipeline-venv/bin/activate
  uv pip install -r requirements-dev.txt
  ```
- Para evitarlo de raíz, usar la AMI **Ubuntu Server 24.04 LTS** (Python 3.12), como indica el Paso 1.

### El CLI de DataHub avisa "Python versions above 3.11 are not actively tested"
- Es solo un warning. Con Python 3.12 el quickstart y la ingesta funcionan igual. Si querés evitarlo,
  creá el `datahub-venv` con `uv venv --python 3.11`.

---

## 12. Fuera de alcance

- No hay ingesta automática programada (la ingesta se corre a mano cuando hace falta).
- No se configura SSO, control de acceso fino ni linaje column-level avanzado.
- No hay alta disponibilidad ni Elasticsearch/Kafka externos: es un quickstart single-node pensado
  para sandbox académico, no para producción.
- DataHub no se integra al CI ni al `docker-compose.yml` del repo principal, porque su peso
  rompería el sandbox chico. Vive en su propia instancia on-demand.
