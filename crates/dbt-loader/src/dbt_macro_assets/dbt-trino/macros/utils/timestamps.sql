{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/timestamps.sql
-#}

{% macro trino__current_timestamp() -%}
    current_timestamp
{%- endmacro %}

{% macro trino__snapshot_string_as_time(timestamp) %}
    {%- set result = "timestamp '" ~ timestamp ~ "'" -%}
    {{ return(result) }}
{% endmacro %}
