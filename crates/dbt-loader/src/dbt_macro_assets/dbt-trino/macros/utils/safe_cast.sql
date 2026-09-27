{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/safe_cast.sql
-#}

{% macro trino__safe_cast(field, type) -%}
    try_cast({{field}} as {{type}})
{%- endmacro %}
