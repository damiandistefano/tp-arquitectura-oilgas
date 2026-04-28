# ADR-0005: Usar Trivy para escaneo de vulnerabilidades de imágenes Docker

## Estado

Aceptado

## Contexto

La consigna de Fase 1 indica que las imágenes Docker deberían ser escaneadas por vulnerabilidades como parte del pipeline de CI.

El proyecto publica una imagen Docker de la API en GitHub Container Registry (GHCR), por lo que resulta necesario validar esa imagen antes de considerarla apta para despliegue.

El escaneo debe integrarse con GitHub Actions, ser simple de mantener y no requerir infraestructura adicional.

## Alternativas consideradas

### Trivy

Trivy es una herramienta open-source de Aqua Security para escanear imágenes Docker, dependencias, sistemas de archivos y configuraciones.

Ventajas:

- integración directa con GitHub Actions;
- soporte para imágenes Docker;
- salida simple en formato tabla;
- bajo costo operativo;
- no requiere servidor propio;
- ampliamente usada en pipelines CI/CD.

Desventajas:

- puede reportar vulnerabilidades que no afectan al runtime real de la aplicación;
- requiere criterio para interpretar severidades y falsos positivos;
- en esta fase se usa como validación informativa y no como bloqueo estricto.

### Grype

Grype, de Anchore, también permite escanear imágenes y dependencias.

Ventajas:

- buena integración con ecosistema de contenedores;
- open-source;
- útil para generar reportes de vulnerabilidades.

Desventajas:

- menor integración directa en este repo respecto de Trivy;
- no aporta una ventaja clara para el alcance actual.

### Docker Scout

Docker Scout se integra con Docker Desktop y Docker Hub.

Ventajas:

- buena experiencia para desarrolladores que usan Docker Desktop;
- integración con el ecosistema Docker;
- análisis visual de vulnerabilidades.

Desventajas:

- más acoplado al ecosistema Docker;
- puede requerir login/configuración adicional;
- menos conveniente para una validación simple dentro de GitHub Actions.

## Decisión

Se usará **Trivy** dentro del pipeline de GitHub Actions para escanear la imagen Docker de la API.

El pipeline ejecuta el escaneo sobre la imagen `oilgas-api` después del build.

En Fase 1, el escaneo se configura con `exit-code: 0`, por lo que funciona como control informativo y evidencia de validación de seguridad, sin bloquear la entrega por falsos positivos o vulnerabilidades heredadas de imágenes base.

## Consecuencias

Consecuencias positivas:

- se cumple el requerimiento de escaneo de imágenes en CI;
- se agrega visibilidad temprana sobre vulnerabilidades;
- se mantiene bajo el costo operativo;
- no se requiere infraestructura adicional;
- el equipo puede endurecer la política más adelante cambiando `exit-code` a `1`.

Trade-offs:

- no reemplaza una auditoría de seguridad completa;
- no cubre pentesting ni análisis manual profundo;
- puede generar falsos positivos;
- no bloquea releases en Fase 1.

## Evolución futura

En una fase productiva se recomienda:

- bloquear el pipeline ante vulnerabilidades críticas explotables;
- definir excepciones documentadas;
- fijar una política de actualización de imágenes base;
- generar SBOM;
- complementar con análisis de secretos, dependencias y configuración IaC.
