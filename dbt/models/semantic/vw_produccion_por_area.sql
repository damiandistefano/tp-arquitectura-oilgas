select
    f.fecha_mes,
    d.periodo,
    f.area_id,
    a.idareapermisoconcesion,
    a.areapermisoconcesion,
    a.provincia,
    a.cuenca,
    f.yacimiento_id,
    y.idareayacimiento,
    y.areayacimiento,
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
left join {{ ref('dim_area') }} a
    on f.area_id = a.area_id
left join {{ ref('dim_yacimiento') }} y
    on f.yacimiento_id = y.yacimiento_id
group by
    f.fecha_mes,
    d.periodo,
    f.area_id,
    a.idareapermisoconcesion,
    a.areapermisoconcesion,
    a.provincia,
    a.cuenca,
    f.yacimiento_id,
    y.idareayacimiento,
    y.areayacimiento
