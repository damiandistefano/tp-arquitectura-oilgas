#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# initial_setup.sh
#
# Bootstrap inicial de una instancia EC2 para Fase 1.
#
# Este script instala Docker/Compose en la EC2, copia los archivos necesarios
# del proyecto y levanta la API para validar el primer despliegue.
#
# Nota:
#   El flujo recomendado de release es `scripts/deploy.sh` con imagen publicada
#   en GHCR. Este script queda como ayuda para preparar o reconstruir el sandbox.
#
# Prerrequisitos:
#   - INSTANCE_IP debe estar definido.
#   - PEM_KEY apunta a la clave .pem local.
#   - EC2_USER depende de la AMI: ec2-user para Amazon Linux, ubuntu para Ubuntu.
#   - rsync debe estar instalado localmente.
#
# Uso:
#   INSTANCE_IP=<ec2-public-ip> PEM_KEY=./tu-key.pem EC2_USER=ec2-user bash scripts/initial_setup.sh
# ---------------------------------------------------------------------------

INSTANCE_IP="${INSTANCE_IP:-}"
PEM_KEY="${PEM_KEY:-./tp-soft.pem}"
EC2_USER="${EC2_USER:-ec2-user}"
APP_REMOTE_DIR="${APP_REMOTE_DIR:-/home/${EC2_USER}/app}"

if [[ -z "${INSTANCE_IP}" ]]; then
  echo "ERROR: INSTANCE_IP no está definido."
  echo "Uso: INSTANCE_IP=<ec2-public-ip> PEM_KEY=./tu-key.pem EC2_USER=ec2-user bash scripts/initial_setup.sh"
  exit 1
fi

if [[ ! -f "${PEM_KEY}" ]]; then
  echo "ERROR: PEM key no encontrada en ${PEM_KEY}"
  exit 1
fi

chmod 400 "${PEM_KEY}"

SSH_OPTS=(-i "${PEM_KEY}" -o StrictHostKeyChecking=no)
SSH_TARGET="${EC2_USER}@${INSTANCE_IP}"

echo "==> [1/3] Instalando Docker en ${INSTANCE_IP}..."
ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" << 'REMOTE'
set -euo pipefail

sudo rm -f /etc/yum.repos.d/docker-ce.repo

if command -v dnf > /dev/null 2>&1; then
  sudo dnf install -y docker
elif command -v apt-get > /dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y docker.io curl
else
  echo "ERROR: no se encontró dnf ni apt-get."
  exit 1
fi

sudo mkdir -p /usr/local/lib/docker/cli-plugins

COMPOSE_ARCH=$(uname -m)
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${COMPOSE_ARCH}" \
  -o /tmp/docker-compose

BUILDX_VERSION=$(curl -fsSL https://api.github.com/repos/docker/buildx/releases/latest \
  | grep '"tag_name"' | sed 's/.*"tag_name": "\(.*\)".*/\1/')
BUILDX_ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
curl -fsSL "https://github.com/docker/buildx/releases/download/${BUILDX_VERSION}/buildx-${BUILDX_VERSION}.linux-${BUILDX_ARCH}" \
  -o /tmp/docker-buildx

sudo mv /tmp/docker-compose /tmp/docker-buildx /usr/local/lib/docker/cli-plugins/
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose \
              /usr/local/lib/docker/cli-plugins/docker-buildx

sudo systemctl enable docker
sudo systemctl start docker

sudo usermod -aG docker "$USER" || true

echo "Docker $(docker --version) instalado correctamente."
echo "Docker Compose $(docker compose version) instalado correctamente."
echo "Docker Buildx $(docker buildx version) instalado correctamente."
REMOTE

echo "==> [2/3] Copiando archivos a ${INSTANCE_IP}:${APP_REMOTE_DIR}..."
rsync -az --progress \
  --exclude '.git' \
  --exclude '.github' \
  --exclude '.claude' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache' \
  --exclude '.ruff_cache' \
  --exclude '.mypy_cache' \
  --exclude '.coverage' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude '*.pem' \
  --exclude '*.key' \
  --exclude '*.crt' \
  --exclude '.aws' \
  --exclude '.ssh' \
  --exclude '*.zip' \
  -e "ssh ${SSH_OPTS[*]}" \
  . "${SSH_TARGET}:${APP_REMOTE_DIR}"

echo "==> [3/3] Levantando API inicial en EC2..."
ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" << REMOTE
set -euo pipefail
cd "${APP_REMOTE_DIR}"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

if docker compose ps --quiet 2>/dev/null | grep -q .; then
  echo "Bajando contenedores existentes..."
  docker compose down
fi

docker compose up -d --build api

echo ""
echo "Estado del contenedor:"
docker compose ps api
REMOTE

echo ""
echo "Bootstrap terminado."
echo "API:  http://${INSTANCE_IP}:8000/docs"
echo "Logs: ssh -i ${PEM_KEY} ${SSH_TARGET} 'cd ${APP_REMOTE_DIR} && docker compose logs -f api'"
