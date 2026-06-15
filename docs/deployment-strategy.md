# Estrategia de Deployment

## Contexto

La Fase 1 del proyecto implementa un mock de API REST para consulta de pronósticos de producción, junto con un stack de monitoreo compuesto por Prometheus, Grafana, Alertmanager y cAdvisor.

El sistema se ejecuta en contenedores Docker y puede levantarse localmente o en una instancia EC2 sandbox mediante Docker Compose.

El objetivo principal no es tener una arquitectura productiva completa, sino validar una base técnica reproducible, observable y defendible para futuras fases.

---

## Artefacto desplegable

El artefacto principal del sistema es la imagen Docker de la API.

El pipeline de CI/CD construye la imagen y la publica en GitHub Container Registry (GHCR), usando dos tipos de tag:

- `latest`: última versión disponible;
- commit SHA: versión trazable e inmutable asociada a un commit específico.

Esto permite mantener trazabilidad entre:

```text
commit -> build -> imagen Docker -> deploy
```

Para despliegues reproducibles se recomienda usar el commit SHA, no `latest`.

La imagen de la API usa `python:3.11-alpine` para reducir peso del artefacto y consumo de disco/red en el sandbox. Las dependencias nativas se instalan durante el build y se eliminan antes de publicar la imagen final.

---

## OpenAPI / Swagger accesible públicamente

La API expone por defecto (sin configuración adicional):

- `/docs` — Swagger UI interactivo.
- `/openapi.json` — especificación OpenAPI en JSON.

Estos endpoints están activos en cualquier ambiente donde corra la API.
En el sandbox EC2 son accesibles como:

```text
http://<EC2_PUBLIC_IP>:8000/docs
http://<EC2_PUBLIC_IP>:8000/openapi.json
```

No requieren autenticación. Los endpoints funcionales sí requieren `X-API-Key: abcdef12345`.

---

## Compose de deploy basado en GHCR

Para el despliegue reproducible se utiliza `docker-compose.deploy.yml`.

A diferencia de `docker-compose.yml`, que levanta el stack completo y construye imágenes localmente,
`docker-compose.deploy.yml` tira la imagen de la API desde GHCR y construye localmente Prometheus,
Grafana y Alertmanager (cuyos builds son ligeros y están versionados en el repo).

Esto evita buildear la API manualmente dentro de la EC2, pero mantiene el monitoreo en el mismo
compose para que el dashboard esté accesible en el sandbox.

Formato de imagen de la API:

```text
ghcr.io/damiandistefano/tp-arquitectura-oilgas/oilgas-api:<tag>
```

El tag se define mediante `IMAGE_TAG`.

---

## Estrategia elegida para Fase 1

Para esta fase se adopta una estrategia simple de **Big Bang Deployment** sobre un ambiente sandbox.

Esto significa que el servicio se actualiza reemplazando la versión anterior del contenedor por una nueva.

Se considera aceptable porque:

- el sistema es un mock técnico;
- no hay usuarios productivos reales;
- el riesgo operativo es bajo;
- el objetivo principal es validar API, CI/CD, Docker, GHCR, monitoreo y operación básica;
- una estrategia más compleja agregaría overhead innecesario para esta adenda.

---

## Ambiente objetivo

El ambiente objetivo es una instancia AWS EC2 usada como sandbox.

Servicios del stack completo:

| Servicio | Puerto |
|---|---|
| API | `8000` |
| Grafana | `3000` |
| Prometheus | `9090` |
| Alertmanager | `9093` |
| cAdvisor | `8080` |

El stack completo se valida con `docker-compose.yml`.

El flujo reproducible de API desde GHCR se valida con `docker-compose.deploy.yml`.

---

## Flujo esperado de release

1. Merge de cambios validados hacia `main`.
2. Ejecución del pipeline de CI/CD.
3. Tests y análisis estático.
4. Build de imagen Docker.
5. Escaneo de vulnerabilidades con Trivy.
6. Publicación de imagen en GHCR.
7. Deploy controlado en EC2 usando `scripts/deploy.sh`.
8. Health check post-deploy.
9. Smoke test del sandbox.

---

## Health check post-deploy

Para validar API localmente en EC2:

```bash
curl -f http://localhost:8000/openapi.json
```

Para validar Grafana localmente en EC2:

```bash
curl -f http://localhost:3000/api/health
```

Para validar desde afuera:

```bash
curl -f http://<EC2_PUBLIC_IP>:8000/openapi.json
curl -f http://<EC2_PUBLIC_IP>:3000/api/health
```

Para validar endpoint protegido:

```bash
curl -H "X-API-Key: abcdef12345" \
  "http://<EC2_PUBLIC_IP>:8000/api/v1/wells?date_query=2026-03-15"
```

---

## Rollback

La estrategia de rollback se basa en desplegar una imagen anterior identificada por su commit SHA o tag.

Como cada imagen publicada en GHCR queda asociada a un commit, se puede recuperar una versión previa sin depender del estado actual del código fuente.

Flujo:

1. identificar commit SHA estable;
2. ejecutar rollback con ese tag;
3. levantar contenedor;
4. ejecutar health check;
5. correr smoke test si aplica.

Comando:

```bash
./scripts/rollback.sh <commit_sha_anterior>
```

---

## Secretos y configuración

El archivo `.env` no se commitea.

Se usa para variables de entorno como:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXXXXXXX/XXXXXXXX/XXXXXXXX
```

En sandbox puede usarse un valor dummy para permitir que Alertmanager levante sin exponer credenciales reales.

---

## Estrategias no implementadas en Fase 1

No se implementan:

- canary deployment;
- blue-green deployment;
- rolling updates reales;
- Kubernetes;
- auto-scaling;
- multi-region deployment;
- separación completa dev/staging/prod;
- deploy automático por SSH desde GitHub Actions hacia EC2;
- performance testing formal con Locust.

Estas estrategias se consideran fuera del alcance de esta adenda. Son válidas para una fase posterior si el sistema pasa de mock técnico a servicio productivo real.

---

## Justificación de la decisión

Para Fase 1 se prioriza una estrategia simple, trazable y reproducible:

- Docker para contenerización;
- Docker Compose para stack local/sandbox;
- GHCR como registry;
- GitHub Actions para CI/CD hasta publicación del artefacto;
- EC2 como sandbox;
- health check post-deploy;
- rollback por tag/SHA;
- Prometheus/Grafana/Alertmanager/cAdvisor para observabilidad.

La decisión prioriza reproducibilidad y trazabilidad sobre automatización completa. El equipo prefirió mantener el deploy controlado por scripts versionados antes de exponer credenciales SSH en GitHub Actions, que es un riesgo real para un sandbox compartido.
