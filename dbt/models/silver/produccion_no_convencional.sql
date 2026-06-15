with typed as (
    select
        {{ to_int('anio') }} as anio,
        {{ to_int('mes') }} as mes,
        {{ clean_text('idpozo') }} as idpozo,
        {{ clean_text('idempresa') }} as idempresa,
        {{ clean_text('empresa') }} as empresa,
        {{ clean_text('sigla') }} as sigla,
        {{ clean_text('formprod') }} as formprod,
        {{ clean_text('cuenca') }} as cuenca,
        {{ clean_text('provincia') }} as provincia,
        {{ clean_text('idareapermisoconcesion') }} as idareapermisoconcesion,
        {{ clean_text('areapermisoconcesion') }} as areapermisoconcesion,
        {{ clean_text('idareayacimiento') }} as idareayacimiento,
        {{ clean_text('areayacimiento') }} as areayacimiento,
        {{ clean_text('formacion') }} as formacion,
        {{ clean_text('tipo_de_recurso') }} as tipo_de_recurso,
        {{ clean_text('sub_tipo_recurso') }} as sub_tipo_recurso,
        {{ clean_text('clasificacion') }} as clasificacion,
        {{ clean_text('subclasificacion') }} as subclasificacion,
        {{ clean_text('tipoextraccion') }} as tipoextraccion,
        {{ clean_text('tipoestado') }} as tipoestado,
        {{ clean_text('tipopozo') }} as tipopozo,
        {{ clean_text('proyecto') }} as proyecto,
        {{ to_numeric('prod_pet') }} as prod_pet,
        {{ to_numeric('prod_gas') }} as prod_gas,
        {{ to_numeric('prod_agua') }} as prod_agua,
        {{ to_numeric('iny_agua') }} as iny_agua,
        {{ to_numeric('iny_gas') }} as iny_gas,
        {{ to_numeric('iny_co2') }} as iny_co2,
        {{ to_numeric('iny_otro') }} as iny_otro,
        {{ to_numeric('tef') }} as tef,
        {{ to_numeric('vida_util') }} as vida_util,
        {{ to_numeric('profundidad') }} as profundidad,
        {{ to_numeric('coordenadax') }} as coordenadax,
        {{ to_numeric('coordenaday') }} as coordenaday,
        {{ to_date('fecha_data') }} as fecha_data,
        {{ to_bool('habilitado') }} as habilitado,
        {{ to_bool('rectificado') }} as rectificado,
        {{ clean_text('observaciones') }} as observaciones,
        {{ clean_text('idusuario') }} as idusuario,
        _run_id,
        _source_name,
        _source_url,
        _source_file_hash,
        _ingested_at,
        _raw_row_number
    from {{ ref('stg_produccion_no_convencional') }}
)

select
    md5(
        coalesce(idpozo, '') || '|' ||
        coalesce(anio::text, '') || '|' ||
        coalesce(mes::text, '') || '|' ||
        coalesce(_source_file_hash, '') || '|' ||
        coalesce(_raw_row_number::text, '')
    ) as produccion_id,
    case
        when anio is not null and mes between 1 and 12
            then make_date(anio, mes, 1)
        else null
    end as fecha_mes,
    *
from typed
