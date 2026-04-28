# ADR-0002: Usar GitHub Actions para integración continua

## Estado

Aceptado

## Contexto

El proyecto necesita validar automáticamente los cambios antes de integrarlos a `develop` o `main`.

La Fase 1 requiere:

- pruebas automáticas;
- análisis estático;
- construcción de imágenes Docker;
- validaciones básicas de la API;
- validación del stack de Docker Compose;
- generación de un artefacto desplegable.

Como el repositorio está alojado en GitHub, conviene usar una herramienta integrada al flujo de Pull Requests.

## Decisión

Se usará GitHub Actions como herramienta de integración continua.

El pipeline ejecuta:

- instalación de dependencias;
- análisis estático con Ruff;
- tests con Pytest;
- validación de OpenAPI;
- validación de endpoints protegidos por API Key;
- build de imagen Docker;
- escaneo de vulnerabilidades con Trivy;
- smoke test del contenedor;
- validación de scripts;
- validación de Docker Compose;
- chequeo de archivos sensibles trackeados;
- smoke test del stack completo;
- publicación de imagen en GHCR cuando el push es a `main`.

## Consecuencias

GitHub Actions permite que cada Pull Request tenga feedback automático y visible para el equipo.

Esto mejora:

- calidad del código;
- trazabilidad;
- confianza antes de mergear;
- detección temprana de errores;
- reproducibilidad del artefacto Docker.

Como trade-off, el pipeline queda acoplado al ecosistema GitHub. Si el proyecto migrara a GitLab, Cloud Build u otra plataforma, habría que adaptar la configuración.

Además, en esta fase no se implementa deploy automático por SSH hacia EC2 desde CI. Se decidió mantener el deploy controlado por scripts versionados para reducir el riesgo operativo del sandbox y evitar exponer secretos innecesarios.
