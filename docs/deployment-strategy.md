# Estrategia de Deployment

## Contexto

La Fase 1 del proyecto implementa un mock de API REST para consulta de pronósticos de producción, junto con un stack de monitoreo compuesto por Prometheus, Grafana y Alertmanager.

El sistema se ejecuta en contenedores Docker y puede levantarse localmente mediante Docker Compose.

## Artefacto desplegable

El artefacto principal del sistema es la imagen Docker de la API.

El pipeline de CI/CD construye la imagen y la publica en GitHub Container Registry (GHCR), usando dos tags:

- `latest`: última versión disponible.
- commit SHA: versión inmutable asociada a un commit específico.

Esto permite mantener trazabilidad entre código fuente, imagen Docker y despliegue.

## Compose de deploy

Para el despliegue en sandbox se utilizará el archivo `docker-compose.deploy.yml`.

A diferencia del `docker-compose.yml` usado para desarrollo local y monitoreo completo, este archivo está pensado para ejecutar la API a partir de una imagen Docker ya publicada en GHCR.

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
- el objetivo principal es validar la arquitectura base, el CI/CD y la observabilidad.

## Ambiente objetivo

El ambiente objetivo de despliegue será una instancia sandbox, inicialmente basada en AWS EC2.

Para el deploy inicial de sandbox, el servicio mínimo esperado es:

- API: puerto `8000`

El stack completo de monitoreo, compuesto por Prometheus, Grafana y Alertmanager, se mantiene disponible mediante `docker-compose.yml` para validación local y puede ser desplegado en el sandbox si se decide exponer también los servicios de monitoreo.

Puertos del stack completo:

- Prometheus: puerto `9090`
- Grafana: puerto `3000`
- Alertmanager: puerto `9093`

## Flujo esperado de deploy

El flujo esperado será:

1. Merge de cambios validados hacia `main`.
2. Ejecución del pipeline de CI/CD.
3. Construcción de imagen Docker.
4. Publicación de imagen en GHCR.
5. Actualización del servicio en el ambiente sandbox usando `docker-compose.deploy.yml`.
6. Ejecución de health check post-deploy.

## Health check post-deploy

Luego del despliegue se debe validar que la API esté disponible mediante:

```bash
curl -f http://<IP_PUBLICA>:8000/openapi.json
```

También se puede validar manualmente accediendo a:

```text
http://<IP_PUBLICA>:8000/docs
```

## Rollback

La estrategia de rollback se basa en volver a desplegar una imagen anterior identificada por su commit SHA.

Como cada imagen publicada en GHCR queda asociada a un commit específico, se puede recuperar una versión previa sin depender del estado actual del código fuente.

Flujo de rollback esperado:

1. Identificar el commit SHA de la última versión estable.
2. Descargar la imagen correspondiente desde GHCR.
3. Reiniciar el servicio usando esa imagen.
4. Ejecutar nuevamente el health check.

En la práctica, el rollback se realiza cambiando `IMAGE_TAG` a un commit SHA anterior y levantando nuevamente el servicio con `docker-compose.deploy.yml`.

Ejemplo:

```bash
IMAGE_TAG=<commit_sha_anterior> docker compose -f docker-compose.deploy.yml up -d
```

Luego del rollback se debe volver a ejecutar el health check contra `/openapi.json`.

## Estrategias no implementadas en Fase 1

No se implementan en esta fase:

- Canary deployment.
- Blue-green deployment.
- Rolling updates.
- Kubernetes.
- Auto-scaling.
- Multi-region deployment.

Estas estrategias se consideran fuera del alcance actual porque agregarían complejidad operativa innecesaria para un mock técnico.

## Decisión

Para Fase 1 se prioriza una estrategia simple, trazable y reproducible:

- Docker para contenerización.
- Docker Compose para levantar el stack local y de monitoreo.
- `docker-compose.deploy.yml` para desplegar la API desde una imagen publicada.
- GHCR como registry de imágenes.
- GitHub Actions para CI/CD.
- EC2 como ambiente sandbox futuro.
- Health check post-deploy como validación mínima.
- Rollback simple mediante commit SHA.

Esta decisión permite avanzar con una base operativa clara sin sobrediseñar la infraestructura.