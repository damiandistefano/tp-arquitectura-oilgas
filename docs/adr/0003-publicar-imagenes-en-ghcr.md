# ADR-0003: Publicar imágenes Docker en GitHub Container Registry

## Estado
Aceptado

## Contexto
La Fase 1 requiere generar artefactos inmutables listos para despliegue. En este proyecto, el artefacto principal es la imagen Docker de la API.

Publicar la imagen en un registry permite separar el código fuente del artefacto desplegable y facilita futuros despliegues en ambientes externos.

## Decisión
Se publicarán las imágenes Docker en GitHub Container Registry (GHCR) desde el pipeline de CI/CD.

Las imágenes se etiquetarán con `latest` y con el commit SHA para mantener trazabilidad entre código, artefacto y despliegue.

## Consecuencias
GHCR se integra de forma directa con GitHub Actions y evita agregar otra plataforma externa al flujo actual.

Como trade-off, el proyecto queda ligado al ecosistema de GitHub para la publicación de artefactos. Si más adelante se usa AWS ECR, será necesario adaptar el pipeline.