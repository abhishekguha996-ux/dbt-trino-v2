{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/any_value.sql
-#}

{% macro trino__any_value(expression) -%}
    min({{ expression }})
{%- endmacro %}
