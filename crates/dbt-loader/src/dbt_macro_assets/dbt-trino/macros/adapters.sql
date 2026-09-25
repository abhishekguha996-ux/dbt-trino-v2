{% macro trino__string_literal(value) -%}
  '{{ value | replace("'", "''") }}'
{%- endmacro %}

{% macro trino__list_schemas(database) -%}
  {% call statement('list_schemas', fetch_result=True, auto_begin=False) -%}
    select schema_name from {{ adapter.quote(database) }}.information_schema.schemata
  {%- endcall %}
  {{ return(load_result('list_schemas').table) }}
{%- endmacro %}

{% macro trino__get_columns_in_relation(relation) -%}
  {% call statement('get_columns_in_relation', fetch_result=True, auto_begin=False) -%}
    select column_name, data_type
    from {{ adapter.quote(relation.database) }}.information_schema.columns
    where table_schema = {{ dbt.string_literal(relation.schema) }}
      and table_name = {{ dbt.string_literal(relation.identifier) }}
    order by ordinal_position
  {%- endcall %}
  {{ return(sql_convert_columns_in_relation(load_result('get_columns_in_relation').table)) }}
{%- endmacro %}

{% macro trino__list_relations_without_caching(schema_relation) -%}
  {% call statement('list_relations_without_caching', fetch_result=True, auto_begin=False) -%}
    select table_catalog as "database", table_name as "name", table_schema as "schema",
           case table_type when 'VIEW' then 'view' else 'table' end as "type"
    from {{ adapter.quote(schema_relation.database) }}.information_schema.tables
    where table_schema = {{ dbt.string_literal(schema_relation.schema) }}
  {%- endcall %}
  {{ return(load_result('list_relations_without_caching').table) }}
{%- endmacro %}

{% macro trino__create_table_as(temporary, relation, sql) -%}
  {%- set contract_config = config.get('contract') -%}
  {%- if contract_config.enforced -%}
    {{ exceptions.raise_compiler_error('Trino model contracts are not supported yet') }}
  {%- endif -%}
  {%- set sql_header = config.get('sql_header', none) -%}
  {{ sql_header if sql_header is not none }}
  create table {{ relation }} as (
    {{ sql }}
  )
{%- endmacro %}

{% macro trino__drop_relation(relation) -%}
  {% if relation.type not in ['table', 'view'] %}
    {{ exceptions.raise_compiler_error('Unsupported Trino relation type: ' ~ relation.type) }}
  {% endif %}
  {% call statement('drop_relation', auto_begin=False) -%}
    drop {{ relation.type }} if exists {{ relation }}
  {%- endcall %}
{%- endmacro %}

{% macro trino__rename_relation(from_relation, to_relation) -%}
  {% if from_relation.type not in ['table', 'view'] %}
    {{ exceptions.raise_compiler_error('Unsupported Trino relation type: ' ~ from_relation.type) }}
  {% endif %}
  {% call statement('rename_relation', auto_begin=False) -%}
    alter {{ from_relation.type }} {{ from_relation }} rename to {{ to_relation }}
  {%- endcall %}
{%- endmacro %}

{% macro trino__get_batch_size() -%}
  {{ return(500) }}
{%- endmacro %}

{% macro trino__get_incremental_default_sql(arg_dict) -%}
  {{ return(get_incremental_append_sql(arg_dict)) }}
{%- endmacro %}

{% macro trino__alter_column_type(relation, column_name, new_column_type) -%}
  {% call statement('alter_column_type', auto_begin=False) -%}
    alter table {{ relation }} alter column {{ adapter.quote(column_name) }} set data type {{ new_column_type }}
  {%- endcall %}
{%- endmacro %}
