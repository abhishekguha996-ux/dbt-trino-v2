{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/utils/hash.sql
-#}

{% macro trino__hash(field) -%}
    lower(to_hex(md5(to_utf8(cast({{field}} as varchar)))))
{%- endmacro %}
