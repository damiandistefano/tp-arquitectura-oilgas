
# Contribución al proyecto

Este documento define cómo trabajar en el repositorio para mantener un flujo ordenado, trazable y fácil de revisar.

## Flujo de ramas

El proyecto usa un flujo basado en GitFlow simplificado:

- `main`: rama estable y entregable.
- `develop`: rama de integración del equipo.
- `feature/*`: ramas de trabajo para tareas específicas.

El flujo normal es:

```text
feature/* -> develop -> main
```

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

## Antes de commitear

Se recomienda verificar que el proyecto funcione localmente.

### Correr tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

### Correr análisis estático

```bash
ruff check .
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

## Commits

Los commits deben describir claramente el cambio realizado.

Ejemplos:

```text
Add Docker vulnerability scan to CI
Add deployment strategy documentation
Fix Docker entrypoint
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

Para variables de entorno, usar `.env.example` como referencia.

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

