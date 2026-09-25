{% materialization incremental, adapter='trino' -%}
  {% set result = materialization_incremental_default() %}
  {% set temp_relation = make_temp_relation(this.incorporate(type='table')) %}
  {% do adapter.drop_relation(temp_relation) %}
  {{ return(result) }}
{%- endmaterialization %}

{% macro trino__get_merge_sql(target, source, unique_key, dest_columns, incremental_predicates=none) -%}
  {{ return(default__get_merge_sql(target, source, unique_key, dest_columns, incremental_predicates, qualify_insert_values=true)) }}
{%- endmacro %}
