{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/array_construct.sql
-#}

{% macro trino__array_construct(inputs, data_type) -%}
    {%- if not inputs -%}
    null
    {%- else -%}
    array[ {{ inputs|join(' , ') }} ]
    {%- endif -%}
{%- endmacro %}
