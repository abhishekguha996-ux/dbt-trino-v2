{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/dateadd.sql
-#}

{% macro trino__dateadd(datepart, interval, from_date_or_timestamp) -%}
    date_add('{{ datepart }}', {{ interval }}, {{ from_date_or_timestamp }})
{%- endmacro %}
