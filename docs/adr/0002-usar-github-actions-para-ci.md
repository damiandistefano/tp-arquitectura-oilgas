# ADR-0002: Usar GitHub Actions para integración continua

## Estado

Aceptado

## Contexto

El proyecto necesita validar automáticamente los cambios antes de integrarlos a `develop` o `main`.
El repositorio vive en GitHub y el equipo es de tres personas. La Fase 1 requiere correr tests,
lint, build de imagen Docker, escaneo de vulnerabilidades y validaciones del stack antes de mergear.

El requerimiento concreto es que cada Pull Request tenga feedback automático y que la imagen Docker
solo se publique cuando CI pase en `main`.

## Alternativas consideradas

### GitHub Actions

Plataforma de CI/CD nativa de GitHub. El repositorio ya está en GitHub, por lo que no hace falta
configurar integraciones externas ni gestionar tokens adicionales para acceder al código.

Ventajas para este proyecto:
- sin configuración extra de webhooks o permisos entre plataformas;
- `GITHUB_TOKEN` disponible de forma automática para publicar en GHCR;
- la ejecución de checks aparece directamente en el PR, visible para todo el equipo;
- runners gratuitos (`ubuntu-latest`) suficientes para el volumen de cambios de una entrega académica.

Desventajas:
- el pipeline queda atado al ecosistema GitHub: si el repo migrara, habría que reescribirlo;
- las minutas gratuitas tienen límite mensual (no problemático para este scope).

### GitLab CI

Alternativa potente con soporte de pipelines complejos y runners propios.

Por qué no la elegimos: el repositorio está en GitHub. Migrar o sincronizar solo para usar GitLab CI
sería overhead innecesario para un equipo de tres personas trabajando en una entrega acotada.

### Jenkins

CI auto-hosteado con mayor control sobre el entorno de ejecución.

Por qué no la elegimos: requiere mantener una instancia propia (servidor, actualizaciones,
autenticación). Para un sandbox académico eso es más trabajo de infraestructura que de desarrollo.
No aporta ventaja sobre GitHub Actions para este scope.

### CircleCI / Travis CI

Otras plataformas SaaS de CI. Comparten el problema de la integración extra con GitHub y en algunos
casos requieren configurar permisos adicionales para publicar imágenes.

## Decisión

Se usa GitHub Actions. El pipeline corre análisis estático, tests, build Docker, escaneo Trivy,
validaciones del stack y publicación en GHCR al mergear a `main`.

El deploy automático por SSH hacia EC2 quedó fuera del pipeline deliberadamente: exponer
credenciales de acceso SSH en GitHub Actions aumenta el riesgo de comprometer el sandbox y agrega
complejidad que no justifica el ahorro de un paso manual en una entrega académica.

## Consecuencias

El equipo tiene feedback automático por PR y un artefacto trazable por commit SHA en GHCR.

Trade-offs que asumimos:
- el pipeline está acoplado a GitHub; migrar a otra plataforma implicaría reescribir los workflows;
- el deploy sigue siendo manual, lo que es un paso extra en cada release;
- si en algún momento se necesita un runner con GPU o dependencias especiales, habría que configurar
  un self-hosted runner.

Queda fuera de esta fase: deploy automático por SSH, ambientes separados dev/staging/prod,
caché de dependencias avanzado y pipelines de múltiples stages con aprobación manual.
