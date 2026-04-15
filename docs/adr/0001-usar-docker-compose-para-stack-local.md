# ADR-0001: Usar Docker Compose para levantar el stack local

## Estado
Aceptado

## Contexto
La Fase 1 requiere que la API mock y los servicios de monitoreo puedan ejecutarse de forma reproducible. El stack incluye la API, Prometheus, Grafana y Alertmanager.

Levantar cada servicio manualmente aumentaría la complejidad accidental y haría más difícil que cualquier integrante del equipo pueda probar el sistema completo.

## Decisión
Se usará Docker Compose para definir y levantar el stack local completo.

## Consecuencias
Docker Compose permite ejecutar todos los servicios con un único comando y mantener una configuración versionada dentro del repo.

Como trade-off, esta solución no ofrece las capacidades de orquestación avanzada de Kubernetes, como escalado automático o rolling updates. Para esta fase se considera suficiente porque el sistema es un mock técnico y no requiere alta disponibilidad real.