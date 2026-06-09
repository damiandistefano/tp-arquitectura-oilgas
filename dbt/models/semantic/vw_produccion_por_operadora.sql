select
    f.fecha_mes,
    d.periodo,
    f.operadora_id,
    o.idempresa,
    o.empresa,
    count(*) as registros_produccion,
    count(distinct f.idpozo) as pozos_con_produccion,
    sum(f.prod_pet) as prod_pet_total,
    sum(f.prod_gas) as prod_gas_total,
    sum(f.prod_agua) as prod_agua_total,
    sum(f.iny_agua) as iny_agua_total,
    sum(f.iny_gas) as iny_gas_total,
    avg(f.tef) as tef_promedio
from {{ ref('fact_produccion_pozo') }} f
left join {{ ref('dim_fecha') }} d
    on f.fecha_mes = d.fecha_mes
left join {{ ref('dim_operadora') }} o
    on f.operadora_id = o.operadora_id
group by
    f.fecha_mes,
    d.periodo,
    f.operadora_id,
    o.idempresa,
    o.empresa
