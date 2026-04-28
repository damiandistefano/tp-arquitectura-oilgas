# Runbook: Deploy en AWS EC2 Sandbox

Este documento describe el proceso para desplegar la API en una instancia EC2 o en un sandbox Linux equivalente.

Para Fase 1, el objetivo mínimo es dejar accesible la API mock desde una IP pública y validar que responde correctamente. El stack completo de monitoreo puede desplegarse en la misma instancia si se quiere validar Prometheus, Grafana, Alertmanager y cAdvisor.

---

## 1. Nota estratégica

Para Fase 1 se usa un enfoque de **Big Bang Deployment** sobre un ambiente sandbox.

Esto significa que la versión anterior del servicio se reemplaza por una nueva versión del contenedor.

Se considera aceptable en esta etapa porque:

- el sistema es un mock técnico;
- no hay usuarios productivos reales;
- el riesgo operativo es bajo;
- el objetivo principal es validar CI/CD, Docker, GHCR, deploy reproducible y observabilidad.

No se implementan en esta fase estrategias como canary, blue-green, rolling updates o Kubernetes.

---

## 2. Prerrequisitos AWS

La instancia EC2 debe cumplir:

- Linux, por ejemplo Amazon Linux 2023 o Ubuntu 22.04.
- Acceso por SSH con key pair `.pem`.
- Docker instalado.
- Docker Compose plugin disponible.
- Acceso a internet para descargar imágenes desde GHCR.

Security Group recomendado:

| Puerto | Uso | Observación |
|---|---|---|
| `22` | SSH | Restringir a IP del equipo. |
| `8000` | API REST | Necesario para la corrección. |
| `3000` | Grafana | Opcional, restringir si es posible. |
| `9090` | Prometheus | Opcional, restringir si es posible. |
| `9093` | Alertmanager | Opcional, restringir si es posible. |
| `8080` | cAdvisor | Opcional, preferentemente no público. |

---

## 3. Seguridad

No se deben commitear:

- archivos `.pem`;
- archivos `.env` reales;
- access keys de AWS;
- tokens de GitHub;
- passwords;
- claves privadas;
- credenciales de Slack.

El archivo `.env` debe existir solo en el servidor o en entornos locales controlados.

---

## 4. Preparación inicial del servidor

Conectarse a la instancia:

```bash
ssh -i tu-llave.pem ec2-user@<EC2_PUBLIC_IP>
```

O, si la AMI es Ubuntu:

```bash
ssh -i tu-llave.pem ubuntu@<EC2_PUBLIC_IP>
```

Clonar el repo:

```bash
git clone https://github.com/damiandistefano/tp-arquitectura-oilgas.git
cd tp-arquitectura-oilgas
```

Crear `.env` para el stack completo:

```bash
cp .env.example .env
```

Editar solo si se va a usar un webhook real:

```bash
nano .env
```

---

## 5. Bootstrap inicial opcional

Existe `scripts/initial_setup.sh` para preparar o reconstruir el sandbox siguiendo la práctica de EC2.

Uso:

```bash
INSTANCE_IP=<EC2_PUBLIC_IP> \
PEM_KEY=./tu-key.pem \
EC2_USER=ec2-user \
bash scripts/initial_setup.sh
```

Este script:

1. instala Docker/Compose en la EC2;
2. copia archivos necesarios con `rsync` excluyendo secretos;
3. levanta la API inicial con Docker Compose.

No es el flujo principal de release. El flujo recomendado de release usa GHCR y `scripts/deploy.sh`.

---

## 6. Artefacto desplegable

La API se despliega desde una imagen Docker publicada en GitHub Container Registry:

```text
ghcr.io/damiandistefano/tp-arquitectura-oilgas/oilgas-api:<tag>
```

Tags usados:

- `latest`: última imagen publicada;
- commit SHA: versión trazable e inmutable asociada a un commit.

Para despliegues reproducibles, se recomienda usar commit SHA.

---

## 7. Deploy de API desde GHCR

El deploy de la API usa `docker-compose.deploy.yml`.

Dar permisos de ejecución:

```bash
chmod +x scripts/deploy.sh scripts/rollback.sh
```

Deploy usando `latest`:

```bash
IMAGE_TAG=latest ./scripts/deploy.sh
```

Deploy usando un commit SHA:

```bash
IMAGE_TAG=<commit_sha> ./scripts/deploy.sh
```

El script `deploy.sh` realiza:

1. lectura de `docker-compose.deploy.yml`;
2. `pull` de la imagen desde GHCR;
3. levantado del contenedor API;
4. health check contra `/openapi.json`;
5. fallo explícito si la API no responde.

---

## 8. Health check post-deploy

Desde la EC2:

```bash
curl -f http://localhost:8000/openapi.json
```

Desde una máquina externa:

```bash
curl -f http://<EC2_PUBLIC_IP>:8000/openapi.json
```

Endpoint funcional:

```bash
curl -H "X-API-Key: abcdef12345" \
  "http://<EC2_PUBLIC_IP>:8000/api/v1/wells?date_query=2026-03-15"
```

Swagger:

```text
http://<EC2_PUBLIC_IP>:8000/docs
```

---

## 9. Logs y operación básica

Ver logs de API:

```bash
docker compose -f docker-compose.deploy.yml logs -f api
```

Ver estado:

```bash
docker compose -f docker-compose.deploy.yml ps
```

Reiniciar:

```bash
docker compose -f docker-compose.deploy.yml restart api
```

Bajar:

```bash
docker compose -f docker-compose.deploy.yml down
```

---

## 10. Rollback

El rollback consiste en volver a desplegar una imagen anterior usando tag o commit SHA.

```bash
./scripts/rollback.sh <commit_sha_anterior>
```

Ejemplo:

```bash
./scripts/rollback.sh 4078096
```

Después del rollback:

```bash
curl -f http://localhost:8000/openapi.json
```

---

## 11. GHCR privado

Si la imagen en GHCR es privada, hacer login:

```bash
echo "<TOKEN>" | docker login ghcr.io -u <USUARIO_GITHUB> --password-stdin
```

Si la imagen es pública, este paso no debería ser necesario.

---

## 12. Deploy del stack completo de monitoreo

Para levantar API + Prometheus + Grafana + Alertmanager + cAdvisor:

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
http://<EC2_PUBLIC_IP>:8000/docs
http://<EC2_PUBLIC_IP>:3000
http://<EC2_PUBLIC_IP>:9090
http://<EC2_PUBLIC_IP>:9093
```

---

## 13. Smoke test completo

Desde la máquina local:

```bash
bash scripts/sandbox-smoke.sh <EC2_PUBLIC_IP>
```

O:

```bash
bash scripts/sandbox-smoke.sh http://<EC2_PUBLIC_IP>
```

También existe workflow manual:

```text
GitHub Actions → AWS Smoke Test → Run workflow
```

---

## 14. Troubleshooting

### La API no responde

```bash
docker compose -f docker-compose.deploy.yml logs api
docker compose -f docker-compose.deploy.yml ps
docker compose -f docker-compose.deploy.yml restart api
```

### Puerto 8000 no responde desde afuera

Revisar:

- API responde localmente en EC2;
- Security Group permite puerto `8000`;
- IP pública correcta;
- contenedor está corriendo.

### No se puede descargar imagen desde GHCR

Revisar:

- imagen existe;
- tag usado en `IMAGE_TAG` existe;
- imagen es pública o se hizo login en GHCR;
- EC2 tiene acceso a internet.

### Alertmanager no levanta

Revisar:

```bash
docker compose logs alertmanager
```

Errores frecuentes:

- `.env` ausente;
- `SLACK_WEBHOOK_URL` vacío;
- YAML inválido;
- permisos incorrectos en `entrypoint.sh`.

---

## 15. Cierre de release

Cuando el equipo cierre Fase 1:

1. mergear `develop` hacia `main`;
2. verificar que CI pase en `main`;
3. confirmar que se publicó la imagen en GHCR;
4. desplegar en sandbox;
5. correr smoke test;
6. crear tag de release, por ejemplo `v0.1.0`.
