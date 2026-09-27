{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/datatypes.sql
-#}

{% macro trino__type_float() -%}
    double
{%- endmacro %}

{% macro trino__type_string() -%}
    varchar
{%- endmacro %}

{% macro trino__type_numeric() -%}
    decimal(28, 6)
{%- endmacro %}

{%- macro trino__type_int() -%}
    integer
{%- endmacro -%}
