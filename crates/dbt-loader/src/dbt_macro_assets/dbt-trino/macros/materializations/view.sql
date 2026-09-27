{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/materializations/view.sql
-#}

{% materialization view, adapter='trino' -%}
    {% set to_return = create_or_replace_view() %}
    {% set target_relation = this.incorporate(type='view') %}

    {% do persist_docs(target_relation, model) %}

    {% do return(to_return) %}
{%- endmaterialization %}
