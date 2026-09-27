{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/date_trunc.sql
-#}

{% macro trino__date_trunc(datepart, date) -%}
    date_trunc('{{datepart}}', {{date}})
{%- endmacro %}
