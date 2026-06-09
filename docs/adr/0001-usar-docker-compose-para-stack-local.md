# ADR-0001: Usar Docker Compose para levantar el stack local

## Estado

Aceptado

## Contexto

La Fase 1 tiene un stack de cinco servicios (API, Prometheus, Grafana, Alertmanager, cAdvisor) que
el equipo necesita poder levantar de forma reproducible en local y en un sandbox EC2.

El equipo es de tres personas, todos con Docker instalado. No hay entornos separados de
staging/prod; solo local y un único sandbox compartido.

## Alternativas consideradas

### Docker Compose (opción elegida)

Permite definir el stack entero en un archivo YAML y levantarlo con un comando. La configuración
se versiona junto al código.

Por qué nos convenía:
- curva de aprendizaje baja para el equipo;
- soporta build local y pull de registries en el mismo archivo;
- fácil de validar en CI (`docker compose config`, `docker compose up`);
- `docker-compose.yml` y `docker-compose.deploy.yml` permiten separar el stack de desarrollo del
  flujo de deploy sin duplicar toda la config.

### Kubernetes (Minikube / kind)

Kubernetes ofrece rolling updates, self-healing, autoscaling y service discovery avanzado.

Por qué no lo elegimos: para un sistema de cinco contenedores en un sandbox académico, el overhead
de gestionar un cluster local es desproporcionado. Minikube o kind funcionan, pero agregan capas
de abstracción (Deployments, Services, Ingresses) que no aportan valor cuando el entorno de
ejecución es una sola EC2 con un único equipo de desarrollo. Si el proyecto evolucionara a
múltiples equipos o ambientes productivos reales, Kubernetes sería el paso natural.

### Docker Swarm

Modo de orquestación nativo de Docker, menos complejo que Kubernetes pero con más capacidades que
Compose.

Por qué no lo elegimos: para este scope no necesitamos nada que Swarm ofrezca sobre Compose.
Swarm agrega conceptos de stacks y servicios que habrían complicado la configuración sin
necesidad real.

## Decisión

Se usa Docker Compose. El archivo principal es `docker-compose.yml` (stack local + desarrollo).
Para el deploy en EC2 se usa `docker-compose.deploy.yml`, que separa la imagen publicada en GHCR
del build local y agrega los servicios de monitoreo accesibles públicamente.

## Consecuencias

Cualquier integrante puede levantar el stack completo con:

```bash
cp .env.example .env
docker compose up --build
```

Trade-offs que asumimos:
- sin rolling updates: cambiar la API en el sandbox es un `docker compose pull && up -d`, lo que
  genera un momento de downtime breve;
- sin self-healing automático a nivel cluster: si un contenedor cae y no tiene `restart: unless-stopped`,
  no vuelve solo;
- el archivo `docker-compose.yml` es un punto de conflicto si varios integrantes lo tocan en
  paralelo; se coordinó que una sola persona lo toca por vez.

Queda fuera: autoscaling, multi-node, separación dev/staging/prod a nivel de infraestructura.
