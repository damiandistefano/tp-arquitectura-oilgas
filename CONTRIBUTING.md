# Contribución al proyecto

Este documento define cómo trabajar en el repositorio para mantener un flujo ordenado, trazable y fácil de revisar.

## Flujo de ramas

El proyecto usa un GitFlow simplificado:

```text
feature/* -> develop -> main
```

- `main`: rama estable y entregable.
- `develop`: rama de integración del equipo.
- `feature/*`: ramas de trabajo para cambios específicos.

No se deben hacer commits directos sobre `main`.

## Crear una nueva tarea

Antes de empezar una tarea nueva:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/nombre-de-la-tarea
```

Ejemplo:

```bash
git checkout -b feature/update-ci
```

La rama debe tener un objetivo concreto. Evitar ramas gigantes que mezclen API, CI, documentación y operación en un solo cambio.

## Tamaño de los cambios

Se recomienda trabajar en cambios chicos y revisables:

- una rama por tarea;
- commits con una intención clara;
- evitar mezclar refactors con cambios funcionales;
- actualizar documentación cuando cambia el uso, el deploy o la operación.

Ejemplo de buen flujo:

```text
feature/fase1-api-contract-tests
  - Improve API mock behavior
  - Expand API contract tests
```

## Antes de commitear

Se recomienda verificar que el proyecto funcione localmente.

### Instalar dependencias

```bash
pip install -r requirements-dev.txt
```

### Correr análisis estático

```bash
ruff check .
```

### Correr tests

```bash
pytest -q
```

### Validar scripts

```bash
bash -n scripts/deploy.sh
bash -n scripts/rollback.sh
bash -n scripts/sandbox-smoke.sh
bash -n scripts/generate_traffic.sh
bash -n scripts/initial_setup.sh
```

### Validar Docker Compose

```bash
cp .env.example .env
docker compose config
docker compose build api
```

### Levantar el stack completo

```bash
cp .env.example .env
docker compose up --build
```

Servicios principales:

- API: `http://localhost:8000/docs`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Alertmanager: `http://localhost:9093`
- cAdvisor: `http://localhost:8080`

## Commits

Los commits deben describir claramente el cambio realizado.

Ejemplos:

```text
Harden Docker build and secret exclusions
Improve API mock behavior
Expand API contract tests
Fix sandbox smoke test endpoints
Harden CI validation workflow
Finalize Phase 1 documentation
```

Evitar mensajes genéricos como:

```text
changes
fix
update
```

## Pull Requests

Todo cambio debe entrar mediante Pull Request.

Para una feature:

```text
base: develop
compare: feature/nombre-de-la-tarea
```

Antes de mergear, el PR debe cumplir:

- CI en verde.
- Cambios revisados por al menos otro integrante.
- README o documentación actualizada si el cambio afecta el uso del sistema.
- Sin archivos sensibles commiteados.
- Sin cambios no relacionados con el objetivo de la rama.

## Definition of Done

Una tarea se considera terminada cuando:

- el código está commiteado en una branch `feature/*`;
- se abrió un PR hacia `develop`;
- el CI pasó correctamente;
- el cambio fue revisado;
- la documentación relevante fue actualizada;
- el PR fue mergeado a `develop`.

## Archivos sensibles

No se deben subir al repositorio:

- `.env`
- archivos `.pem`
- credenciales de AWS
- claves privadas
- tokens
- contraseñas
- archivos `.pyc`
- carpetas `__pycache__`
- configuración local de AWS o SSH (`.aws/`, `.ssh/`)

Para variables de entorno, usar `.env.example` o `.env.sandbox.example` como referencia.

## Validación de sandbox

Para validar el sandbox desplegado en EC2:

```bash
bash scripts/sandbox-smoke.sh <EC2_PUBLIC_IP>
```

También se puede ejecutar el workflow manual:

```text
GitHub Actions -> AWS Smoke Test -> Run workflow
```

## Limpieza de branches

Después de mergear un PR, se puede borrar la branch de feature.

Localmente:

```bash
git branch -d feature/nombre-de-la-tarea
```

En GitHub, usar el botón `Delete branch` o:

```bash
git push origin --delete feature/nombre-de-la-tarea
```
