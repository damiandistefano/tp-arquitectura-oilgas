# Runbook: Deploy en AWS (EC2 / Sandbox)

Este documento describe el proceso para desplegar la API en una instancia EC2 de AWS o en un sandbox Linux equivalente.

Para Fase 1, el objetivo mínimo del deploy es dejar accesible la API mock desde una IP pública y validar que responde correctamente. El stack completo de monitoreo puede desplegarse aparte si el equipo decide exponer también Grafana, Prometheus y Alertmanager.

## Nota estratégica

Para Fase 1 se usa un enfoque de **Big Bang Deployment**.

Esto significa que la versión anterior del servicio se reemplaza por la nueva versión del contenedor. Se considera aceptable en esta etapa porque:

- el sistema es un mock técnico;
- no hay usuarios productivos reales;
- el riesgo operativo es bajo;
- el objetivo principal es validar CI/CD, Docker, GHCR y despliegue en sandbox.

No se implementan en esta fase estrategias como canary deployment, blue-green deployment, rolling updates o Kubernetes.

## Prerrequisitos de AWS

La instancia EC2 debe cumplir:

- Sistema operativo Linux, por ejemplo Ubuntu 22.04 o Amazon Linux 2023.
- Acceso por SSH con una key pair `.pem`.
- Docker instalado.
- Docker Compose disponible.
- Acceso a internet para descargar imágenes desde GHCR.

El Security Group debe permitir tráfico entrante en:

- `22`: SSH.
- `8000`: API REST.

Opcionalmente, si se decide exponer monitoreo:

- `3000`: Grafana.
- `9090`: Prometheus. Se recomienda restringir por IP.
- `9093`: Alertmanager. Se recomienda restringir por IP.

## Seguridad

No se deben commitear al repositorio:

- archivos `.pem`;
- archivos `.env`;
- access keys de AWS;
- tokens de GitHub;
- contraseñas;
- claves privadas.

El archivo `.env` debe existir solo en el servidor o en entornos locales controlados.

## Preparación inicial del servidor

Conectarse a la instancia:

```bash
ssh -i tu-llave.pem ubuntu@IP_PUBLICA
```

o, si la instancia usa Amazon Linux:

```bash
ssh -i tu-llave.pem ec2-user@IP_PUBLICA
```

Clonar el repositorio:

```bash
git clone https://github.com/damiandistefano/tp-arquitectura-oilgas.git
cd tp-arquitectura-oilgas
```

Crear el `.env` si se va a usar el stack completo de monitoreo:

```bash
cp .env.example .env
```

Editarlo con valores reales si se van a usar alertas por Slack o email:

```bash
nano .env
```

## Artefacto desplegable

La API se despliega desde la imagen Docker publicada en GitHub Container Registry (GHCR):

```text
ghcr.io/damiandistefano/tp-arquitectura-oilgas/oilgas-api:<tag>
```

El tag puede ser:

- `latest`: última imagen publicada;
- commit SHA: versión inmutable asociada a un commit específico.

Para despliegues reproducibles se recomienda usar el commit SHA.

## Deploy de la API desde GHCR

El deploy de la API debe usar `docker-compose.deploy.yml`, no el `docker-compose.yml` local de desarrollo.

Dar permisos de ejecución a los scripts:

```bash
chmod +x scripts/deploy.sh scripts/rollback.sh
```

Deploy usando `latest`:

```bash
IMAGE_TAG=latest ./scripts/deploy.sh
```

Deploy usando un commit SHA específico:

```bash
IMAGE_TAG=<commit_sha> ./scripts/deploy.sh
```

Ejemplo:

```bash
IMAGE_TAG=4078096 ./scripts/deploy.sh
```

El script `deploy.sh` realiza:

1. lectura del archivo `docker-compose.deploy.yml`;
2. pull de la imagen desde GHCR;
3. levantado del contenedor de API;
4. health check contra `/openapi.json`;
5. fallo explícito si la API no responde.

## Health check post-deploy

Desde la EC2:

```bash
curl -f http://localhost:8000/openapi.json
```

Desde una máquina externa:

```bash
curl -f http://IP_PUBLICA:8000/openapi.json
```

También se puede validar manualmente abriendo:

```text
http://IP_PUBLICA:8000/docs
```

## Logs y operación básica

Ver logs de la API:

```bash
docker compose -f docker-compose.deploy.yml logs -f api
```

Ver estado del contenedor:

```bash
docker compose -f docker-compose.deploy.yml ps
```

Reiniciar el servicio:

```bash
docker compose -f docker-compose.deploy.yml restart api
```

Bajar el servicio:

```bash
docker compose -f docker-compose.deploy.yml down
```

## Rollback

El rollback consiste en volver a desplegar una imagen anterior usando su tag o commit SHA.

Ejemplo:

```bash
./scripts/rollback.sh <commit_sha_anterior>
```

Ejemplo concreto:

```bash
./scripts/rollback.sh 4078096
```

El script de rollback reutiliza `deploy.sh`, pero cambiando `IMAGE_TAG` por el tag indicado.

Después del rollback, se debe volver a validar:

```bash
curl -f http://localhost:8000/openapi.json
```

## Si GHCR requiere autenticación

Si la imagen en GHCR es privada, primero se debe hacer login:

```bash
echo "<TOKEN>" | docker login ghcr.io -u <USUARIO_GITHUB> --password-stdin
```

Si la imagen es pública, este paso no debería ser necesario.

## Deploy del stack completo de monitoreo

El archivo `docker-compose.yml` se mantiene para levantar el stack completo:

- API;
- Prometheus;
- Grafana;
- Alertmanager.

Para levantar todo el stack:

```bash
cp .env.example .env
docker compose up -d --build
```

Validaciones:

```bash
curl -f http://localhost:8000/openapi.json
curl -f http://localhost:8000/metrics
curl -f http://localhost:9090/-/healthy
curl -f http://localhost:3000/api/health
curl -f http://localhost:9093/-/healthy
```

Desde afuera, si los puertos están abiertos:

```text
http://IP_PUBLICA:8000/docs
http://IP_PUBLICA:3000
http://IP_PUBLICA:9090
http://IP_PUBLICA:9093
```

## Troubleshooting

### La API no responde

Ver logs:

```bash
docker compose -f docker-compose.deploy.yml logs api
```

Ver estado:

```bash
docker compose -f docker-compose.deploy.yml ps
```

Reiniciar:

```bash
docker compose -f docker-compose.deploy.yml restart api
```

### El puerto 8000 no responde desde afuera

Revisar:

- que la API responda localmente en la EC2;
- que el Security Group tenga abierto el puerto `8000`;
- que se esté usando la IP pública correcta;
- que el contenedor esté corriendo.

### No se puede descargar la imagen desde GHCR

Revisar:

- que la imagen exista en GHCR;
- que el tag usado en `IMAGE_TAG` exista;
- que la imagen sea pública o que se haya hecho login en GHCR;
- que la EC2 tenga acceso a internet.

## Cierre de release

Cuando el equipo cierre Fase 1:

1. mergear `develop` hacia `main`;
2. verificar que el CI pase en `main`;
3. confirmar que se publicó la imagen en GHCR;
4. desplegar en sandbox;
5. validar health check;
6. crear tag de release, por ejemplo `v0.1.0`.

## Validación post-deploy

Para el checklist completo de validación funcional del sandbox (API, Prometheus, Grafana, Alertmanager) y troubleshooting operativo, ver [sandbox-validation.md](sandbox-validation.md).

El smoke test local contra la EC2 se puede correr con:
```bash
bash scripts/sandbox-smoke.sh IP_PUBLICA
```
