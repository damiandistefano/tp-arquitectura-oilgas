# ADR-0003: Publicar imágenes Docker en GitHub Container Registry

## Estado

Aceptado

## Contexto

La Fase 1 genera una imagen Docker de la API que necesita estar disponible para despliegue en EC2
sin buildear manualmente en el servidor. El repositorio vive en GitHub y el pipeline de CI está
en GitHub Actions.

El requisito concreto es: imagen inmutable por commit SHA, accesible desde EC2, publicada
automáticamente desde CI cuando pasa a `main`.

## Alternativas consideradas

### GitHub Container Registry — GHCR (opción elegida)

Registry integrado en el ecosistema GitHub. Las imágenes se publican con el `GITHUB_TOKEN`
que Actions genera automáticamente; no hay que crear ni rotar credenciales adicionales.

Por qué nos convenía:
- autenticación sin secretos extra: `GITHUB_TOKEN` sirve tanto para pushear la imagen como para
  que la EC2 la pueda pullear si el paquete se configura como público;
- visibilidad directa en el repositorio (pestaña "Packages");
- etiquetado con `latest` y commit SHA sin configuración adicional.

Limitaciones:
- si el paquete es privado, la EC2 necesita hacer `docker login ghcr.io` con un token personal;
- el espacio de almacenamiento gratuito es limitado; para este proyecto no es un problema.

### Docker Hub

Registry público más conocido, con buen ecosistema de imágenes base.

Por qué no lo elegimos: Docker Hub requiere crear una cuenta separada y configurar credenciales
adicionales en GitHub Actions (un `DOCKERHUB_TOKEN`). El repositorio ya está en GitHub; agregar
otra plataforma sin ventaja funcional concreta es overhead. Además Docker Hub tiene límites de
pull rate en el plan gratuito que podrían afectar en un entorno compartido.

### Amazon ECR (Elastic Container Registry)

Registry de AWS, natural si el deploy fuera en un entorno AWS gestionado (ECS, EKS, Lambda).

Por qué no lo elegimos: requiere autenticarse contra AWS desde GitHub Actions (credenciales IAM),
configurar la región y el nombre del repositorio. Para un sandbox académico en una EC2 simple,
ese overhead no se justifica. Si el proyecto evolucionara hacia ECS o EKS, ECR sería la opción
obvia.

### Build manual directamente en EC2

Clonar el repo y buildear la imagen en la instancia en cada deploy.

Por qué no lo elegimos: rompe la separación entre build y deploy, hace el proceso no reproducible
(depende del estado del repo en el servidor) y duplica el tiempo de CI si hay que correr tests
en EC2 también. El objetivo era tener un artefacto validado por CI antes de llegar al servidor.

## Decisión

Se publican las imágenes en GHCR desde GitHub Actions, etiquetadas con `latest` y commit SHA.
Para despliegues reproducibles se recomienda usar el SHA, no `latest`.

## Consecuencias

La trazabilidad entre commit → build → imagen → deploy está garantizada. El rollback a una versión
anterior es cuestión de redeployar con el SHA anterior.

Trade-offs que asumimos:
- el flujo de artefactos está ligado a GitHub; migrar implicaría reconfigurar CI y credenciales;
- si el paquete está configurado como privado, la EC2 necesita credenciales para pullear;
- el espacio de imágenes acumuladas en GHCR hay que limpiar manualmente si no se configura
  una política de retención.

Queda fuera: firma de imágenes (cosign), generación de SBOM, políticas de retención automática,
multi-arch builds.
