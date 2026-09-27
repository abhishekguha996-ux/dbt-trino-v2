{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/listagg.sql
-#}

{% macro trino__listagg(measure, delimiter_text, order_by_clause, limit_num) -%}
    {% set collect_list %} array_agg({{ measure }} {% if order_by_clause -%}{{ order_by_clause }}{%- endif %}) {% endset %}
    {% set limited %} slice({{ collect_list }}, 1, {{ limit_num }}) {% endset %}
    {% set collected = limited if limit_num else collect_list %}
    {% set final %} array_join({{ collected }}, {{ delimiter_text }}) {% endset %}
    {% do return(final) %}
{%- endmacro %}
