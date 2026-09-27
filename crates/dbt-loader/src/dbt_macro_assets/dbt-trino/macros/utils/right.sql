{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/right.sql
-#}

{% macro trino__right(string_text, length_expression) %}
    case when {{ length_expression }} = 0
        then ''
    else
        substr({{ string_text }}, -1 * ({{ length_expression }}))
    end
{%- endmacro -%}
