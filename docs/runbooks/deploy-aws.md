# Runbook: Deploy en AWS (EC2 / Sandbox)

Este documento describe el proceso para desplegar el stack de Oil & Gas Forecast API en una instancia EC2 de AWS (o cualquier sandbox basado en Linux). 

> **Nota Estratégica (Deployment Strategy):** 
> Para la Fase 1 (Mock) se utiliza un enfoque de **Big Bang Deployment** debido a la naturaleza estática de los datos, el bajo riesgo y la simplicidad requerida en esta etapa inicial.

## 1. Prerrequisitos en la Instancia (Initial Setup)
La instancia (ej. Ubuntu 22.04 o Amazon Linux 2023) debe tener instalado **Docker** y **Docker Compose**.
Además, el **Security Group** de AWS debe permitir tráfico entrante (Inbound Rules) en los siguientes puertos:
* `22` (SSH)
* `8000` (API REST)
* `3000` (Grafana)
* `9090` (Prometheus - Opcional, recomendado restringir IP)
* `9093` (Alertmanager - Opcional, recomendado restringir IP)

## 2. Preparación del Entorno
1. Conectarse por SSH a la instancia:
   ```bash
   ssh -i tu-llave.pem ubuntu@IP_PUBLICA
   ```
2. Clonar el repositorio (o descargar los archivos vía artefacto de CI):
   ```bash
   git clone https://github.com/damiandistefano/tp-arquitectura-oilgas.git
   cd tp-arquitectura-oilgas
   ```
3. Crear el archivo `.env` con las variables de entorno productivas (API Keys, Webhooks de Slack, contraseñas SMTP):
   ```bash
   nano .env
   ```
   *(No commitear nunca este archivo, las llaves deben mantenerse seguras en el servidor).*

## 3. Despliegue (Deploy)
Para levantar los servicios, ejecutar:
```bash
sudo docker-compose up -d --build
```
Esto descargará las imágenes base, construirá la API y levantará todo el stack de monitoreo (Grafana, Prometheus, cAdvisor, Alertmanager).

## 4. Verificación Post-Deploy (Health Checks)
1. **Verificar API:** Navegar a `http://IP_PUBLICA:8000/docs` o `http://IP_PUBLICA:8000/health`.
2. **Verificar Grafana:** Navegar a `http://IP_PUBLICA:3000`.
3. **Validar logs de arranque:**
   ```bash
   sudo docker-compose logs -f api
   ```

## 5. Actualización Continua (Redeploy)
Dado el enfoque Big Bang, el proceso de actualización de código en el servidor es manual o automatizado vía CI/CD:
1. Bajar los últimos cambios estables (idealmente desde `main`): 
   ```bash
   git checkout main && git pull origin main
   ```
2. Reconstruir y reiniciar contenedores: 
   ```bash
   sudo docker-compose up -d --build
   ```
        
### Estrategia de Rollback
Si la nueva versión falla tras el redeploy (API devuelve 500s o el health check falla), se debe volver al commit de la versión anterior:
```bash
git checkout <COMMIT_SHA_ANTERIOR>
sudo docker-compose up -d --build
```