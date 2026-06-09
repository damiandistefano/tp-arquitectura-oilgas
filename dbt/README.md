# dbt analytics

Modelos analíticos para transformar datos desde Bronze hacia Silver, Gold y vistas Semantic.

## Capas

- staging: lectura inicial desde tablas Bronze.
- silver: tablas limpias y tipadas.
- gold: dimensiones y hechos para análisis.
- semantic: vistas finales para consumo BI.

## Perfil local

Copiar el perfil de ejemplo:

    mkdir -p ~/.dbt
    cp dbt/profiles.example.yml ~/.dbt/profiles.yml

Después correr dbt desde la carpeta dbt:

    cd dbt
    dbt debug
    dbt run
    dbt test
