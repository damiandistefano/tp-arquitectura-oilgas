# ADR-0001: Usar Docker Compose para levantar el stack local

## Estado

Aceptado

## Contexto

La Fase 1 requiere que la API mock y los servicios de monitoreo puedan ejecutarse de forma reproducible por cualquier integrante del equipo.

El stack incluye:

- API mock;
- Prometheus;
- Grafana;
- Alertmanager;
- cAdvisor.

Levantar cada servicio manualmente aumentaría la complejidad accidental y haría más difícil validar el sistema completo de forma consistente.

También se evaluó Kubernetes, pero para esta fase el sistema no necesita orquestación avanzada, alta disponibilidad real ni múltiples réplicas productivas.

## Decisión

Se usará Docker Compose para definir y levantar el stack local completo.

El archivo principal será `docker-compose.yml`, que permite ejecutar el stack con:

```bash
cp .env.example .env
docker compose up --build
```

## Consecuencias

Docker Compose permite:

- levantar todos los servicios con un único comando;
- versionar la configuración junto al código;
- reducir diferencias entre entornos locales;
- simplificar la validación del dashboard y de las métricas;
- facilitar el onboarding de nuevos integrantes.

Como trade-off, Docker Compose no ofrece las capacidades avanzadas de Kubernetes, como rolling updates, auto-scaling, service discovery avanzado o tolerancia a fallos a nivel cluster.

Para esta fase se considera suficiente porque el sistema es un mock técnico y no requiere alta disponibilidad productiva. Kubernetes queda como posible evolución futura si el proyecto avanza hacia múltiples servicios, escalabilidad horizontal o ambientes productivos más exigentes.
