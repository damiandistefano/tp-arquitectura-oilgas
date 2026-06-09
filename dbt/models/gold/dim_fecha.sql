select distinct
    fecha_mes,
    extract(year from fecha_mes)::int as anio,
    extract(month from fecha_mes)::int as mes,
    to_char(fecha_mes, 'YYYY-MM') as periodo
from {{ ref('produccion_no_convencional') }}
where fecha_mes is not null
