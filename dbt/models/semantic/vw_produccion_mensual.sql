select
    f.fecha_mes,
    d.anio,
    d.mes,
    d.periodo,
    count(*) as registros_produccion,
    count(distinct f.idpozo) as pozos_con_produccion,
    sum(f.prod_pet) as prod_pet_total,
    sum(f.prod_gas) as prod_gas_total,
    sum(f.prod_agua) as prod_agua_total,
    sum(f.iny_agua) as iny_agua_total,
    sum(f.iny_gas) as iny_gas_total,
    sum(f.iny_co2) as iny_co2_total,
    sum(f.iny_otro) as iny_otro_total,
    avg(f.tef) as tef_promedio
from {{ ref('fact_produccion_pozo') }} f
left join {{ ref('dim_fecha') }} d
    on f.fecha_mes = d.fecha_mes
group by
    f.fecha_mes,
    d.anio,
    d.mes,
    d.periodo
