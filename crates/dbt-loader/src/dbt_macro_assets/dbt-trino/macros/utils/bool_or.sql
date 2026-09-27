{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/bool_or.sql
-#}

{% macro trino__bool_or(expression) -%}
    bool_or({{ expression }})
{%- endmacro %}
