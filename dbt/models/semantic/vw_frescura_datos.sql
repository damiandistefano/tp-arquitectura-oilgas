select
    max(fecha_mes) as ultimo_periodo_disponible,
    max(_ingested_at) as ultima_ingesta,
    count(*) as registros_totales,
    count(distinct idpozo) as pozos_distintos,
    count(distinct _source_file_hash) as archivos_fuente,
    current_date - max(fecha_mes)::date as dias_desde_ultimo_periodo
from {{ ref('fact_produccion_pozo') }}
