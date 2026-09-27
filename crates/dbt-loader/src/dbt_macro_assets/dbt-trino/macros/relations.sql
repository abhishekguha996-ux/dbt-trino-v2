{#-
  Relation rename macros used by the dbt v2 relation framework (get_replace_sql, backup and
  intermediate swaps). Not part of dbt-trino v1, whose materializations issued renames directly.

  Trino resolves an unqualified `RENAME TO` target against the session catalog and schema,
  not the renamed relation's, so the new name is always fully qualified.
-#}

{% macro trino__renamed_relation(relation, new_name) -%}
  {%- if new_name is string -%}
    {{ return(relation.incorporate(path={"identifier": new_name})) }}
  {%- else -%}
    {{ return(new_name) }}
  {%- endif -%}
{%- endmacro %}

{% macro trino__get_rename_table_sql(relation, new_name) -%}
  alter table {{ relation }} rename to {{ trino__renamed_relation(relation, new_name) }}
{%- endmacro %}

{% macro trino__get_rename_view_sql(relation, new_name) -%}
  alter view {{ relation }} rename to {{ trino__renamed_relation(relation, new_name) }}
{%- endmacro %}

{% macro trino__get_rename_materialized_view_sql(relation, new_name) -%}
  alter materialized view {{ relation }} rename to {{ trino__renamed_relation(relation, new_name) }}
{%- endmacro %}

{% macro trino__get_replace_materialized_view_sql(relation, sql) -%}
  {{ trino__get_create_materialized_view_as_sql(relation, sql, or_replace=true) }}
{%- endmacro %}
