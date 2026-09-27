{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/array_append.sql
-#}

{% macro trino__array_append(array, new_element) -%}
    {{ array_concat(array, array_construct([new_element])) }}
{%- endmacro %}
