with areas as (
    select distinct
        idareapermisoconcesion,
        areapermisoconcesion,
        provincia,
        cuenca
    from {{ ref('produccion_no_convencional') }}
    where idareapermisoconcesion is not null

    union

    select distinct
        idareapermisoconcesion,
        areapermisoconcesion,
        provincia,
        cuenca
    from {{ ref('pozos_operadoras') }}
    where idareapermisoconcesion is not null
)

select
    md5(coalesce(idareapermisoconcesion, '')) as area_id,
    idareapermisoconcesion,
    max(areapermisoconcesion) as areapermisoconcesion,
    max(provincia) as provincia,
    max(cuenca) as cuenca
from areas
group by idareapermisoconcesion
