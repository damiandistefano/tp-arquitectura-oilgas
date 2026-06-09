with yacimientos as (
    select distinct
        idareayacimiento,
        areayacimiento,
        idareapermisoconcesion
    from {{ ref('produccion_no_convencional') }}
    where idareayacimiento is not null

    union

    select distinct
        idareayacimiento,
        areayacimiento,
        idareapermisoconcesion
    from {{ ref('pozos_operadoras') }}
    where idareayacimiento is not null
)

select
    md5(coalesce(idareayacimiento, '')) as yacimiento_id,
    idareayacimiento,
    max(areayacimiento) as areayacimiento,
    max(idareapermisoconcesion) as idareapermisoconcesion
from yacimientos
group by idareayacimiento
