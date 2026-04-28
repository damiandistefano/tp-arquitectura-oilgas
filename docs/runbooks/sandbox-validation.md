# Runbook: Validación Sandbox (EC2)

Quién lo ejecuta y cuándo: Integrante 3 (operación), una vez que el Integrante 2 confirma que el deploy en EC2 está activo.

---

## 1. Pre-requisitos

- API deployada via `scripts/deploy.sh` (ver [deploy-aws.md](deploy-aws.md)).
- Para el stack de monitoreo completo: `docker compose up -d` con `docker-compose.yml`.
- Security Group con inbound abierto desde tu IP en:
  - `22` (SSH), `8000` (API), `9090` (Prometheus), `3000` (Grafana), `9093` (Alertmanager).
- Archivo `.env` presente en el host EC2 (ver [`.env.sandbox.example`](../../.env.sandbox.example)).
- Tener la IP pública de la instancia (`<EC2_PUBLIC_IP>`).

---

## 2. Servicios expuestos

| Servicio | URL | Credenciales |
|---|---|---|
| API — Swagger | `http://<EC2_PUBLIC_IP>:8000/docs` | Header `X-API-Key: abcdef12345` |
| API — Metrics | `http://<EC2_PUBLIC_IP>:8000/metrics` | — |
| Prometheus | `http://<EC2_PUBLIC_IP>:9090` | — |
| Grafana | `http://<EC2_PUBLIC_IP>:3000` | admin / admin |
| Alertmanager | `http://<EC2_PUBLIC_IP>:9093` | — |

---

## 3. Smoke test automático

```bash
bash scripts/sandbox-smoke.sh <EC2_PUBLIC_IP>
```

El script valida 11 checks (API, Prometheus, Alertmanager, Grafana) e imprime `✓` / `✗` por cada uno. Sale con código 0 si todo pasa, 1 si algo falla.

Como alternativa CI, el workflow `.github/workflows/aws-smoke.yml` corre 5 checks básicos desde GitHub Actions (activar manualmente con `workflow_dispatch` desde la pestaña Actions).

---

## 4. Checklist de validación manual

Completar tras el smoke test para documentar evidencia.

### API

- [ ] `GET /health` → `{"status":"ok"}` (200)
- [ ] `GET /openapi.json` → 200
- [ ] `GET /docs` renderiza Swagger UI en el browser
- [ ] `GET /metrics` expone `http_requests_total`
- [ ] `GET /api/v1/wells` con `X-API-Key: abcdef12345` → 200
- [ ] `GET /api/v1/wells` sin header → 401 o 403

### Prometheus

- [ ] `http://<EC2_PUBLIC_IP>:9090/targets` → `oilgas-api` en estado **UP**
- [ ] `http://<EC2_PUBLIC_IP>:9090/rules` → 4 reglas cargadas (APIDown, HighErrorRate, HighLatency, APIRecovered)

### Grafana

- [ ] Login con `admin` / `admin` funciona
- [ ] Datasource Prometheus health **OK** (Settings → Datasources → Test)
- [ ] Dashboard "oilgas" muestra paneles con datos

### Alertmanager

- [ ] UI accesible en `:9093`
- [ ] No hay alertas en **firing** al momento de validar (estado limpio)

---

## 5. Validación de alertas (opcional, end-to-end)

> Aplica al stack completo (`docker-compose.yml`). Si solo levantaste la API con `deploy.sh` / `docker-compose.deploy.yml`, primero levantá el monitoreo: `docker compose up -d prometheus grafana alertmanager`.

### Generar tráfico hacia la EC2

```bash
# Adaptar la URL base al host de la EC2
API_URL=http://<EC2_PUBLIC_IP>:8000 bash scripts/generate_traffic.sh
```

### Disparar APIDown

```bash
# En la EC2
ssh -i tu-llave.pem ubuntu@<EC2_PUBLIC_IP>
docker compose stop api
```

Esperar ~1 min → Prometheus debe mostrar la alerta `APIDown` en firing.

### Verificar recuperación (APIRecovered)

```bash
docker compose start api
# o via deploy.sh para volver con imagen GHCR:
IMAGE_TAG=latest ./scripts/deploy.sh
```

Esperar ~5 min → `APIRecovered` en firing, luego `APIDown` resuelto.

> En sandbox con `.env` dummy, las alertas aparecen en la UI de Alertmanager pero no llegan a Slack.

---

## 6. Troubleshooting

### Comandos básicos en la EC2

```bash
# Ver todos los servicios y su estado
docker compose ps

# Logs de un servicio específico
docker compose logs -f api
docker compose logs -f prometheus
docker compose logs -f grafana
docker compose logs -f alertmanager

# Reiniciar un servicio
docker compose restart <servicio>

# Reiniciar todo el stack
docker compose down && docker compose up -d
```

### Casos específicos de sandbox

| Síntoma | Causa probable | Solución |
|---|---|---|
| Conexión rechazada a cualquier puerto | Security Group cerrado | Agregar inbound rule en AWS Console para tu IP |
| `/metrics` no aparece en Prometheus targets | URL de scrape incorrecta o red interna | Verificar `prometheus.yml`, que `api:8000` sea alcanzable dentro de la red docker |
| Grafana no carga datasource | Prometheus no arrancó | `docker compose ps` + `docker compose restart prometheus` |
| Alertmanager no levanta | `.env` ausente o mal formado | Verificar que el archivo `.env` exista y tenga `SLACK_WEBHOOK_URL` |
| `docker compose` no encontrado | Docker Compose plugin no instalado | `sudo apt-get install docker-compose-plugin` |

Para troubleshooting detallado por servicio (disparo de alertas, verificación de reglas, queries PromQL) ver [local-stack.md](local-stack.md).

---

## 7. Evidencia final

Completar antes de la entrega:

| Item | Estado | Notas |
|---|---|---|
| Output smoke script (exit 0) | [ ] | Pegar output o adjuntar captura |
| Screenshot Grafana dashboard | [ ] | Mostrar paneles con datos reales |
| Screenshot Prometheus targets (UP) | [ ] | `/targets` con oilgas-api UP |
| Screenshot Alertmanager UI | [ ] | Estado limpio o alerta de prueba |
| URLs activas el día de entrega | [ ] | Completar tabla de servicios arriba |

### Release tag v0.1.0

Una vez que los tres integrantes cierran su parte:

```bash
git checkout main
git pull origin main
git tag v0.1.0
git push origin v0.1.0
```

Crear el release en GitHub (Releases → Draft a new release → tag `v0.1.0`) con un changelog breve y el link a este runbook.

---

## 8. Cómo verificar lo de AWS (checklist para el equipo)

### GHCR (Integrante 1)

1. GitHub → **Actions** → último run en `main` → step **"Push to GHCR"** en verde.
2. GitHub → **Packages** → `oilgas-api` → ver tags `latest` y el SHA del commit.
3. Verificar pull local:
   ```bash
   docker login ghcr.io   # usar PAT con scope read:packages
   docker pull ghcr.io/<org>/oilgas-api:latest
   ```

### EC2 viva (Integrante 1)

1. Obtener: IP pública, key `.pem`, región, tipo de instancia.
2. Verificar SSH: `ssh -i key.pem ubuntu@<EC2_PUBLIC_IP>`
3. Verificar docker: `docker --version && docker compose version`

### Deploy hecho (Integrante 2 — entregado)

1. En la EC2: `IMAGE_TAG=latest ./scripts/deploy.sh` (o con SHA específico).
2. `docker compose -f docker-compose.deploy.yml ps` → servicio `api` en estado `Up`.
3. `docker images` → imagen `ghcr.io/<org>/oilgas-api` presente (no built local).

### Security Group (AWS Console)

1. EC2 → **Security Groups** → inbound rules.
2. Confirmar puertos 22, 8000, 9090, 3000, 9093 accesibles desde la IP del equipo.

### End-to-end

Correr el smoke script desde tu máquina local:
```bash
bash scripts/sandbox-smoke.sh <EC2_PUBLIC_IP>
```
Si todos los checks son `✓` → AWS está validado desde el lado release.
