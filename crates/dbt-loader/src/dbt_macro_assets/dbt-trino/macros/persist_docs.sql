{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/persist_docs.sql
  Changes for dbt v2 are marked "v2:".
-#}

{% macro trino__persist_docs(relation, model, for_relation, for_columns) -%}
  {% set do_relation = for_relation and config.persist_relation_docs() %}
  {% set do_columns = for_columns and config.persist_column_docs() %}

  {% if do_relation and model.description %}
    {% do run_query(alter_relation_comment(relation, model.description)) %}
  {% endif %}

  {% if do_columns and model.columns %}
    {% do run_query(alter_column_comment(relation, model.columns)) %}
  {% endif %}

  {#- v2: Starburst Data Discovery sync (target.starburst_url) is not part of OSS Trino. -#}
{%- endmacro %}
