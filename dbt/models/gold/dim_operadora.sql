select
    md5(coalesce(idempresa, '')) as operadora_id,
    idempresa,
    max(empresa) as empresa
from {{ ref('produccion_no_convencional') }}
where idempresa is not null
group by idempresa
