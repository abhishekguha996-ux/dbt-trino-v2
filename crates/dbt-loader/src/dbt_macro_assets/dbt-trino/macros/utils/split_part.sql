{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/split_part.sql
-#}

{% macro trino__split_part(string_text, delimiter_text, part_number) %}
  {% if part_number >= 0 %}
    {{ dbt.default__split_part(string_text, delimiter_text, part_number) }}
  {% else %}
    {{ dbt._split_part_negative(string_text, delimiter_text, part_number) }}
  {% endif %}
{% endmacro %}
