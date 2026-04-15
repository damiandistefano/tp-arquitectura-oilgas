# ADR-0002: Usar GitHub Actions para integración continua

## Estado
Aceptado

## Contexto
El proyecto necesita validar automáticamente los cambios antes de integrarlos. La Fase 1 requiere pruebas automáticas, análisis estático, construcción de imágenes Docker y validaciones básicas del servicio.

Como el repositorio está alojado en GitHub, conviene usar una herramienta integrada al flujo de pull requests.

## Decisión
Se usará GitHub Actions como herramienta de integración continua.

El pipeline ejecuta pruebas, análisis estático, construcción de imagen Docker, smoke tests del contenedor y validaciones del stack con Docker Compose.

## Consecuencias
GitHub Actions permite que cada pull request tenga feedback automático y visible para el equipo.

Como trade-off, el pipeline queda acoplado a GitHub. Si el proyecto migrara a GitLab u otra plataforma, habría que adaptar la configuración del CI.