{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/array_concat.sql
-#}

{% macro trino__array_concat(array_1, array_2) -%}
    concat({{ array_1 }}, {{ array_2 }})
{%- endmacro %}
