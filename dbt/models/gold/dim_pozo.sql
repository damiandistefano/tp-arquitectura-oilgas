with pozos as (
    select
        idpozo,
        sigla,
        formprod,
        idempresa,
        idareapermisoconcesion,
        idareayacimiento,
        cuenca,
        provincia,
        codigopropio,
        nombrepropio,
        coordenadax,
        coordenaday,
        cota,
        profundidad,
        clasificacion,
        subclasificacion,
        tipo_reservorio,
        subtipo_reservorio
    from {{ ref('pozos_operadoras') }}
    where idpozo is not null
),

produccion as (
    select
        idpozo,
        sigla,
        formprod,
        idempresa,
        idareapermisoconcesion,
        idareayacimiento,
        cuenca,
        provincia,
        coordenadax,
        coordenaday,
        profundidad,
        clasificacion,
        subclasificacion,
        tipopozo,
        tipoextraccion,
        tipoestado,
        tipo_de_recurso,
        sub_tipo_recurso
    from {{ ref('produccion_no_convencional') }}
    where idpozo is not null
),

unioned as (
    select
        idpozo,
        sigla,
        formprod,
        idempresa,
        idareapermisoconcesion,
        idareayacimiento,
        cuenca,
        provincia,
        codigopropio,
        nombrepropio,
        coordenadax,
        coordenaday,
        cota,
        profundidad,
        clasificacion,
        subclasificacion,
        tipo_reservorio,
        subtipo_reservorio,
        null::text as tipopozo,
        null::text as tipoextraccion,
        null::text as tipoestado,
        null::text as tipo_de_recurso,
        null::text as sub_tipo_recurso
    from pozos

    union all

    select
        idpozo,
        sigla,
        formprod,
        idempresa,
        idareapermisoconcesion,
        idareayacimiento,
        cuenca,
        provincia,
        null::text as codigopropio,
        null::text as nombrepropio,
        coordenadax,
        coordenaday,
        null::numeric as cota,
        profundidad,
        clasificacion,
        subclasificacion,
        null::text as tipo_reservorio,
        null::text as subtipo_reservorio,
        tipopozo,
        tipoextraccion,
        tipoestado,
        tipo_de_recurso,
        sub_tipo_recurso
    from produccion
)

select
    md5(coalesce(idpozo, '')) as pozo_id,
    idpozo,
    max(sigla) as sigla,
    max(formprod) as formprod,
    max(idempresa) as idempresa,
    max(idareapermisoconcesion) as idareapermisoconcesion,
    max(idareayacimiento) as idareayacimiento,
    max(cuenca) as cuenca,
    max(provincia) as provincia,
    max(codigopropio) as codigopropio,
    max(nombrepropio) as nombrepropio,
    max(coordenadax) as coordenadax,
    max(coordenaday) as coordenaday,
    max(cota) as cota,
    max(profundidad) as profundidad,
    max(clasificacion) as clasificacion,
    max(subclasificacion) as subclasificacion,
    max(tipo_reservorio) as tipo_reservorio,
    max(subtipo_reservorio) as subtipo_reservorio,
    max(tipopozo) as tipopozo,
    max(tipoextraccion) as tipoextraccion,
    max(tipoestado) as tipoestado,
    max(tipo_de_recurso) as tipo_de_recurso,
    max(sub_tipo_recurso) as sub_tipo_recurso
from unioned
group by idpozo
