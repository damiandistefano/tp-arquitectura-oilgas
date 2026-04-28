# Estrategia de Deployment

## Contexto

La Fase 1 del proyecto implementa un mock de API REST para consulta de pronósticos de producción, junto con un stack de monitoreo compuesto por Prometheus, Grafana, Alertmanager y cAdvisor.

El sistema se ejecuta en contenedores Docker y puede levantarse localmente o en un ambiente sandbox mediante Docker Compose.

## Artefacto desplegable

El artefacto principal del sistema es la imagen Docker de la API.

El pipeline de CI/CD construye la imagen y la publica en GitHub Container Registry (GHCR), usando dos tags:

- `latest`: última versión disponible.
- commit SHA: versión inmutable asociada a un commit específico.

Esto permite mantener trazabilidad entre código fuente, imagen Docker y despliegue.

## Compose de deploy basado en GHCR

Para el despliegue reproducible de la API se utiliza el archivo `docker-compose.deploy.yml`.

A diferencia del `docker-compose.yml`, que levanta el stack completo y puede construir las imágenes localmente, `docker-compose.deploy.yml` está pensado para ejecutar la API a partir de una imagen Docker ya publicada en GHCR.

Esto evita buildear manualmente la imagen dentro de la instancia EC2 y permite desplegar un artefacto previamente validado por el pipeline de CI/CD.

La imagen utilizada tiene el siguiente formato:

```text
ghcr.io/damiandistefano/tp-arquitectura-oilgas/oilgas-api:<tag>
```

El tag se define mediante la variable `IMAGE_TAG`.

Por defecto se usa `latest`, pero para despliegues trazables se recomienda usar el commit SHA generado por GitHub Actions.

## Estrategia de deployment para Fase 1

Para esta fase se adopta una estrategia de deployment simple tipo **Big Bang Deployment** sobre un ambiente sandbox.

Esto significa que el servicio se actualiza reemplazando la versión anterior por la nueva versión del contenedor.

Se considera aceptable para esta fase porque:

- el sistema es un mock técnico;
- no hay usuarios productivos reales;
- el riesgo operativo es bajo;
- el objetivo principal es validar la arquitectura base, el CI/CD, Docker, GHCR y observabilidad.

## Ambiente objetivo

El ambiente objetivo de despliegue es una instancia sandbox basada en AWS EC2.

El sandbox completo expone los siguientes servicios:

- API: puerto `8000`.
- Grafana: puerto `3000`.
- Prometheus: puerto `9090`.
- Alertmanager: puerto `9093`.
- cAdvisor: puerto `8080`.

El stack completo fue validado con `docker-compose.yml`.

Además, se validó en paralelo el flujo de deploy reproducible de la API desde GHCR usando `docker-compose.deploy.yml`, sin pisar el stack principal. Para esta validación se utilizó el puerto `8001` dentro de la EC2.

El puerto `8001` no necesariamente queda expuesto públicamente, porque su acceso externo depende de las reglas configuradas en el Security Group de AWS. La validación mínima de ese flujo se realiza desde la propia EC2 contra `localhost:8001`.

## Flujo esperado de deploy

El flujo esperado será:

1. Merge de cambios validados hacia `main`.
2. Ejecución del pipeline de CI/CD.
3. Construcción de imagen Docker.
4. Publicación de imagen en GHCR.
5. Actualización del servicio en el ambiente sandbox usando `docker-compose.deploy.yml`.
6. Ejecución de health check post-deploy.

## Validación realizada en AWS

Se validaron dos caminos complementarios:

### Stack completo de sandbox

El stack completo fue levantado en EC2 usando `docker-compose.yml`.

Servicios validados:

```text
http://52.15.50.130:8000/docs
http://52.15.50.130:3000
http://52.15.50.130:9090
http://52.15.50.130:9093
```

También se validó cAdvisor en el puerto `8080` desde la instancia.

### Deploy reproducible desde GHCR

Se validó el deploy de la API desde GHCR usando:

```bash
COMPOSE_PROJECT_NAME=ghcrdeploy \
PROJECT_DIR=/home/ec2-user/app \
API_PORT=8001 \
IMAGE_TAG=latest \
./scripts/deploy.sh
```

La validación post-deploy fue:

```bash
curl -f http://localhost:8001/openapi.json
```

El resultado confirmó que la imagen fue descargada desde GHCR y que la API quedó saludable en el puerto `8001`.

## Health check post-deploy

Para validar la API expuesta públicamente:

```bash
curl -f http://<IP_PUBLICA>:8000/openapi.json
```

Para validar el deploy paralelo desde GHCR dentro de la EC2:

```bash
curl -f http://localhost:8001/openapi.json
```

También se puede validar manualmente accediendo a:

```text
http://<IP_PUBLICA>:8000/docs
```

## Rollback

La estrategia de rollback se basa en volver a desplegar una imagen anterior identificada por su commit SHA o tag.

Como cada imagen publicada en GHCR queda asociada a un commit específico, se puede recuperar una versión previa sin depender del estado actual del código fuente.

Flujo de rollback esperado:

1. Identificar el commit SHA de la última versión estable.
2. Descargar la imagen correspondiente desde GHCR.
3. Reiniciar el servicio usando esa imagen.
4. Ejecutar nuevamente el health check.

En la práctica, el rollback se realiza ejecutando `scripts/rollback.sh` con el tag o commit SHA deseado.

Ejemplo:

```bash
COMPOSE_PROJECT_NAME=ghcrdeploy \
PROJECT_DIR=/home/ec2-user/app \
API_PORT=8001 \
./scripts/rollback.sh <commit_sha_anterior>
```

Para la validación de Fase 1 se probó el flujo usando `latest` como tag:

```bash
COMPOSE_PROJECT_NAME=ghcrdeploy \
PROJECT_DIR=/home/ec2-user/app \
API_PORT=8001 \
./scripts/rollback.sh latest
```

Luego del rollback se vuelve a ejecutar el health check contra `/openapi.json`.

## Secretos y variables

El archivo `.env` no se commitea al repositorio.

En EC2 se usa para configurar variables necesarias para servicios como Alertmanager. Por ejemplo:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXXXXXXX/XXXXXXXX/XXXXXXXX
```

El valor real debe configurarse en el servidor o mediante secretos del entorno, no en Git.

## Estrategias no implementadas en Fase 1

No se implementan en esta fase:

- Canary deployment.
- Blue-green deployment.
- Rolling updates.
- Kubernetes.
- Auto-scaling.
- Multi-region deployment.
- Deploy automático desde GitHub Actions hacia EC2.

Estas estrategias se consideran fuera del alcance actual porque agregarían complejidad operativa innecesaria para un mock técnico.

## Decisión

Para Fase 1 se prioriza una estrategia simple, trazable y reproducible:

- Docker para contenerización.
- Docker Compose para levantar el stack completo de sandbox.
- `docker-compose.deploy.yml` para desplegar la API desde una imagen publicada.
- GHCR como registry de imágenes.
- GitHub Actions para CI/CD.
- EC2 como ambiente sandbox.
- Health check post-deploy como validación mínima.
- Rollback simple mediante commit SHA o tag.

Esta decisión permite validar el sistema completo sin sobrediseñar la infraestructura, y a la vez deja preparado un camino reproducible para desplegar la API desde imágenes versionadas en GHCR.
