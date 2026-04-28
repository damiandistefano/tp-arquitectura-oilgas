# ADR-0003: Publicar imágenes Docker en GitHub Container Registry

## Estado

Aceptado

## Contexto

La Fase 1 requiere generar artefactos inmutables listos para despliegue.

En este proyecto, el artefacto principal es la imagen Docker de la API.

Publicar la imagen en un registry permite separar:

- código fuente;
- artefacto desplegable;
- ambiente de ejecución.

Esto evita depender de builds manuales dentro de la instancia EC2 y mejora la trazabilidad entre commit, imagen y despliegue.

Se consideraron estas alternativas:

- GitHub Container Registry (GHCR);
- Docker Hub;
- Amazon Elastic Container Registry (ECR);
- build manual directamente en EC2.

## Decisión

Se publicarán las imágenes Docker de la API en GitHub Container Registry (GHCR) desde el pipeline de GitHub Actions.

Las imágenes se etiquetarán con:

- `latest`;
- commit SHA.

Para despliegues reproducibles se recomienda usar el commit SHA o un tag de release, no depender únicamente de `latest`.

## Consecuencias

GHCR se integra directamente con GitHub Actions y evita agregar otra plataforma externa al flujo actual.

Beneficios:

- trazabilidad entre código e imagen;
- rollback más simple por tag o SHA;
- artefacto reutilizable fuera de la EC2;
- separación entre build y deploy;
- menor riesgo que buildear manualmente en el servidor.

Trade-offs:

- el proyecto queda ligado al ecosistema GitHub para la publicación de artefactos;
- si más adelante se decide usar AWS ECR, habrá que adaptar el pipeline;
- si la imagen se configura como privada, la EC2 necesita autenticarse contra GHCR.

Para Fase 1 se considera una solución adecuada porque reduce complejidad y mantiene el flujo alineado con el repositorio.
