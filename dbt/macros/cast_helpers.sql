{% macro clean_text(column_name) -%}
nullif(trim({{ column_name }}), '')
{%- endmacro %}

{% macro to_int(column_name) -%}
case
    when nullif(trim({{ column_name }}), '') ~ '^-?[0-9]+$'
        then nullif(trim({{ column_name }}), '')::integer
    else null
end
{%- endmacro %}

{% macro to_numeric(column_name) -%}
case
    when nullif(trim({{ column_name }}), '') ~ '^-?[0-9]+(\.[0-9]+)?$'
        then nullif(trim({{ column_name }}), '')::numeric
    else null
end
{%- endmacro %}

{% macro to_date(column_name) -%}
case
    when nullif(trim({{ column_name }}), '') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        then nullif(trim({{ column_name }}), '')::date
    else null
end
{%- endmacro %}

{% macro to_bool(column_name) -%}
case
    when lower(nullif(trim({{ column_name }}), '')) in ('t', 'true', '1', 'si', 'sí', 'yes') then true
    when lower(nullif(trim({{ column_name }}), '')) in ('f', 'false', '0', 'no') then false
    else null
end
{%- endmacro %}
