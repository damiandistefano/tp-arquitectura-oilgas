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

El stack se levantará usando Docker Compose.

Servicios esperados:

- API: puerto `8000`
- Prometheus: puerto `9090`
- Grafana: puerto `3000`
- Alertmanager: puerto `9093`

## Flujo esperado de deploy

El flujo esperado será:

1. Merge de cambios validados hacia `main`.
2. Ejecución del pipeline de CI/CD.
3. Construcción de imagen Docker.
4. Publicación de imagen en GHCR.
5. Actualización del servicio en el ambiente sandbox.
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
- Docker Compose para levantar el stack.
- GHCR como registry de imágenes.
- GitHub Actions para CI/CD.
- EC2 como ambiente sandbox futuro.
- Health check post-deploy como validación mínima.

Esta decisión permite avanzar con una base operativa clara sin sobrediseñar la infraestructura.
