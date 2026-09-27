{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/adapters.sql
  Changes for dbt v2 are marked "v2:".
-#}

{#- v2: identifiers and literals below are escaped; v1 interpolated them verbatim.
    v2: `relation.information_schema('<view>')` renders the qualified view; without a view name
    the v2 relation renders a trailing '.', so the view is always passed. -#}
{% macro trino__string_literal(value) -%}
  '{{ value | replace("'", "''") }}'
{%- endmacro %}

{% macro trino__get_columns_in_relation(relation) -%}
  {%- set sql -%}
    select column_name, data_type
    from {{ relation.information_schema('columns') }}
    where
      table_catalog = {{ trino__string_literal(relation.database | lower) }}
      and table_schema = {{ trino__string_literal(relation.schema | lower) }}
      and table_name = {{ trino__string_literal(relation.identifier | lower) }}
    order by ordinal_position
  {%- endset -%}
  {%- set result = run_query(sql) -%}

  {% set maximum = 10000 %}
  {% if (result | length) >= maximum %}
    {% set msg %}
      Too many columns in relation {{ relation }}! dbt can only get
      information about relations with fewer than {{ maximum }} columns.
    {% endset %}
    {% do exceptions.raise_compiler_error(msg) %}
  {% endif %}

  {% set columns = [] %}
  {% for row in result %}
    {% do columns.append(api.Column.from_description(row['column_name'].lower(), row['data_type'])) %}
  {% endfor %}
  {% do return(columns) %}
{% endmacro %}


{% macro trino__list_relations_without_caching(relation) %}
  {% call statement('list_relations_without_caching', fetch_result=True) -%}
    select
      t.table_catalog as database,
      t.table_name as name,
      t.table_schema as schema,
      case when mv.name is not null then 'materialized_view'
           when t.table_type = 'BASE TABLE' then 'table'
           when t.table_type = 'VIEW' then 'view'
           else t.table_type
      end as table_type
    from {{ relation.information_schema('tables') }} t
    left join (
            select * from system.metadata.materialized_views
            where catalog_name = {{ trino__string_literal(relation.database | lower) }}
              and schema_name = {{ trino__string_literal(relation.schema | lower) }}) mv
          on mv.catalog_name = t.table_catalog and mv.schema_name = t.table_schema and mv.name = t.table_name
    where t.table_schema = {{ trino__string_literal(relation.schema | lower) }}
  {% endcall %}
  {{ return(load_result('list_relations_without_caching').table) }}
{% endmacro %}


{% macro trino__reset_csv_table(model, full_refresh, old_relation, agate_table) %}
    {{ adapter.drop_relation(old_relation) }}
    {{ return(create_csv_table(model, agate_table)) }}
{% endmacro %}


{% macro trino__create_csv_table(model, agate_table) %}
  {%- set column_override = model['config'].get('column_types', {}) -%}
  {%- set quote_seed_column = model['config'].get('quote_columns', None) -%}

  {% set sql %}
    create table {{ this.render() }} (
        {%- for col_name in agate_table.column_names -%}
            {%- set inferred_type = adapter.convert_type(agate_table, loop.index0) -%}
            {%- set type = column_override.get(col_name, inferred_type) -%}
            {%- set column_name = (col_name | string) -%}
            {{ adapter.quote_seed_column(column_name, quote_seed_column) }} {{ type }} {%- if not loop.last -%}, {%- endif -%}
        {%- endfor -%}
    ) {{ properties() }}
  {% endset %}

  {% call statement('_') -%}
    {{ sql }}
  {%- endcall %}

  {{ return(sql) }}
{% endmacro %}

{#- v2: rewritten without mutating the model config. Semantics match v1: `file_format` and
    `table_format` fill `properties.format` / `properties.type`, a catalog integration
    (`catalog_name`) supplies defaults, and temporary relations get a `__dbt_tmp` location. -#}
{% macro properties(temporary=False) %}
  {%- set configured = config.get('properties') or {} -%}
  {%- set _properties = {} -%}
  {%- for key, value in configured.items() -%}
    {%- do _properties.update({key: value}) -%}
  {%- endfor -%}
  {%- set table_format = config.get('table_format') -%}
  {%- set file_format = config.get('file_format') -%}
  {%- set catalog_relation = adapter.build_catalog_relation(config.model) if config.get('catalog_name') else none -%}
  {%- set catalog_table_format = catalog_relation.table_format if catalog_relation else none -%}
  {%- set catalog_file_format = catalog_relation.file_format if catalog_relation else none -%}
  {%- set catalog_storage_uri = catalog_relation.storage_uri if catalog_relation else none -%}

  {%- if file_format -%}
    {%- if 'format' in _properties -%}
      {% do exceptions.raise_compiler_error("You can specify either 'file_format' or 'properties.format' configurations, but not both.") %}
    {%- endif -%}
    {%- do _properties.update({'format': "'" ~ file_format ~ "'"}) -%}
  {%- elif 'format' not in _properties and catalog_file_format -%}
    {%- do _properties.update({'format': "'" ~ catalog_file_format ~ "'"}) -%}
  {%- endif -%}

  {%- if table_format -%}
    {%- if 'type' in _properties -%}
      {% do exceptions.raise_compiler_error("You can specify either 'table_format' or 'properties.type' configurations, but not both.") %}
    {%- endif -%}
    {%- do _properties.update({'type': "'" ~ table_format ~ "'"}) -%}
  {%- elif 'type' not in _properties and catalog_table_format -%}
    {%- do _properties.update({'type': "'" ~ catalog_table_format ~ "'"}) -%}
  {%- endif -%}

  {%- if 'location' not in _properties and catalog_storage_uri -%}
    {%- do _properties.update({'location': "'" ~ catalog_storage_uri ~ "'"}) -%}
  {%- endif -%}

  {%- if temporary and _properties.get('location') -%}
    {%- do _properties.update({'location': _properties['location'][:-1] ~ "__dbt_tmp'"}) -%}
  {%- endif -%}

  {%- if _properties -%}
      WITH (
          {%- for key, value in _properties.items() -%}
            {{ key }} = {{ value }}
            {%- if not loop.last -%}{{ ',\n  ' }}{%- endif -%}
          {%- endfor -%}
      )
  {%- endif -%}
{%- endmacro -%}

{% macro comment(comment) %}
  {%- set persist_docs = model.get('config', {}).get('persist_docs') -%}
  {%- if persist_docs -%}
    {%- set persist_relation = persist_docs.get('relation') -%}
    {%- if persist_relation and comment is not none and comment|length > 0 -%}
        comment '{{ comment | replace("'", "''") }}'
    {%- endif -%}
  {%- endif -%}
{%- endmacro -%}

{% macro trino__create_table_as(temporary, relation, sql, on_exists=None) -%}

  {%- set or_replace = ' or replace' if on_exists == 'replace' else '' -%}
  {%- set if_not_exists = ' if not exists' if on_exists == 'skip' else '' -%}
  {#- v2: statements are split on ';', so a `sql_header` such as `set session ...;` runs first. -#}
  {%- set sql_header = config.get('sql_header', none) -%}
  {{ sql_header if sql_header is not none }}

  {%- set contract_config = config.get('contract') -%}
  {%- if contract_config.enforced -%}

  create{{ or_replace }} table{{ if_not_exists }}
    {{ relation }}
    {{ get_table_columns_and_constraints() }}
    {{ get_assert_columns_equivalent(sql) }}
    {%- set sql = get_select_subquery(sql) %}
    {{ comment(model.get('description')) }}
    {{ properties(temporary) }}
  ;

  insert into {{ relation }}
    (
      {{ sql }}
    )
  ;

  {%- else %}

    create{{ or_replace }} table{{ if_not_exists }} {{ relation }}
      {{ comment(model.get('description')) }}
      {{ properties(temporary) }}
    as (
      {{ sql }}
    );

  {%- endif %}
{% endmacro %}


{% macro trino__create_view_as(relation, sql) -%}
  {%- set view_security = config.get('view_security', 'definer') -%}
  {%- if view_security not in ['definer', 'invoker'] -%}
      {%- set log_message = 'Invalid value for view_security (%s) specified. Setting default value (%s).' % (view_security, 'definer') -%}
      {% do log(log_message) %}
      {#- v2: v1 assigned the fallback to an unused variable. -#}
      {%- set view_security = 'definer' -%}
  {% endif %}
  {%- set sql_header = config.get('sql_header', none) -%}
  {{ sql_header if sql_header is not none }}
  create or replace view
    {{ relation }}
  {%- set contract_config = config.get('contract') -%}
  {%- if contract_config.enforced -%}
    {{ get_assert_columns_equivalent(sql) }}
  {%- endif %}
  security {{ view_security }}
  as
    {{ sql }}
  ;
{% endmacro %}


{%- macro trino__get_drop_sql(relation) -%}
  {% set relation_type = relation.type|replace("_", " ") %}
    drop {{ relation_type }} if exists {{ relation }}
{% endmacro %}


{# see this issue: https://github.com/dbt-labs/dbt/issues/2267 #}
{% macro trino__information_schema_name(database) -%}
  {%- if database -%}
    {{ database }}.INFORMATION_SCHEMA
  {%- else -%}
    INFORMATION_SCHEMA
  {%- endif -%}
{%- endmacro %}


{# On Trino, 'cascade' is not supported so we have to manually cascade. #}
{% macro trino__drop_schema(relation) -%}
  {% for row in list_relations_without_caching(relation) %}
    {% set rel_db = row[0] %}
    {% set rel_identifier = row[1] %}
    {% set rel_schema = row[2] %}
    {#- v2: the listing already returns dbt relation type names. -#}
    {% set existing = api.Relation.create(database=rel_db, schema=rel_schema, identifier=rel_identifier, type=row[3]) %}
    {% do drop_relation(existing) %}
  {% endfor %}
  {%- call statement('drop_schema') -%}
    drop schema if exists {{ relation }}
  {% endcall %}
{% endmacro %}


{% macro trino__rename_relation(from_relation, to_relation) -%}
  {% set from_relation_type = from_relation.type|replace("_", " ") %}
  {% call statement('rename_relation') -%}
    alter {{ from_relation_type }} {{ from_relation }} rename to {{ to_relation }}
  {%- endcall %}
{% endmacro %}


{% macro trino__alter_relation_comment(relation, relation_comment) -%}
  comment on {{ relation.type | replace("_", " ") }} {{ relation }} is '{{ relation_comment | replace("'", "''") }}';
{% endmacro %}


{% macro trino__alter_column_comment(relation, column_dict) %}
  {% set existing_columns = adapter.get_columns_in_relation(relation) | map(attribute="name") | list %}
  {% for column_name in column_dict if (column_name in existing_columns) %}
    {% set comment = column_dict[column_name]['description'] %}
    {%- if comment|length -%}
      comment on column {{ relation }}.{{ adapter.quote(column_name) if column_dict[column_name]['quote'] else column_name }} is '{{ comment | replace("'", "''") }}';
    {%- else -%}
      comment on column {{ relation }}.{{ adapter.quote(column_name) if column_dict[column_name]['quote'] else column_name }} is null;
    {%- endif -%}
  {% endfor %}
{% endmacro %}


{% macro trino__list_schemas(database) -%}
  {% call statement('list_schemas', fetch_result=True, auto_begin=False) %}
    select schema_name
    from {{ information_schema_name(database) }}.schemata
  {% endcall %}
  {{ return(load_result('list_schemas').table) }}
{% endmacro %}


{% macro trino__check_schema_exists(information_schema, schema) -%}
  {% call statement('check_schema_exists', fetch_result=True, auto_begin=False) -%}
        select count(*)
        from {{ information_schema }}.schemata
        where catalog_name = {{ trino__string_literal(information_schema.database) }}
          and schema_name = {{ trino__string_literal(schema | lower) }}
  {%- endcall %}
  {{ return(load_result('check_schema_exists').table) }}
{% endmacro %}

{#- v2: `adapter.add_query(bindings=...)` renders bindings as SQL literals in place of `%s`,
    so `prepared_statements_enabled` only controls the driver's explicit-prepare mode. -#}
{% macro trino__get_binding_char() %}
  {{ return('%s') }}
{% endmacro %}


{% macro trino__alter_relation_add_remove_columns(relation, add_columns, remove_columns) %}
  {% if add_columns is none %}
    {% set add_columns = [] %}
  {% endif %}
  {% if remove_columns is none %}
    {% set remove_columns = [] %}
  {% endif %}

  {#- v2: drop before add. Adding first shifts later columns into the dropped column's position,
      which Hive metastores reject (hive.metastore.disallow.incompatible.col.type.changes). -#}
  {% for column in remove_columns %}
    {% set sql -%}
      alter {{ relation.type }} {{ relation }} drop column {{ adapter.quote(column.name) }}
    {%- endset -%}
    {% do run_query(sql) %}
  {% endfor %}

  {% for column in add_columns %}
    {% set sql -%}
      alter {{ relation.type }} {{ relation }} add column {{ adapter.quote(column.name) }} {{ column.data_type }}
    {%- endset -%}
    {% do run_query(sql) %}
  {% endfor %}
{% endmacro %}


{% macro create_or_replace_view() %}
  {%- set identifier = model['alias'] -%}

  {%- set old_relation = adapter.get_relation(database=database, schema=schema, identifier=identifier) -%}
  {%- set exists_as_view = (old_relation is not none and old_relation.is_view) -%}

  {%- set target_relation = api.Relation.create(
      identifier=identifier, schema=schema, database=database,
      type='view') -%}
  {% set grant_config = config.get('grants') %}

  {{ run_hooks(pre_hooks) }}

  -- If there is another object delete it
  {%- if old_relation is not none and not old_relation.is_view -%}
    {{ handle_existing_table(should_full_refresh(), old_relation) }}
  {%- endif -%}

  -- build model
  {% call statement('main') -%}
    {{ get_create_view_as_sql(target_relation, sql) }}
  {%- endcall %}

  {% set should_revoke = should_revoke(exists_as_view, full_refresh_mode=True) %}
  {% do apply_grants(target_relation, grant_config, should_revoke=True) %}

  {{ run_hooks(post_hooks) }}

  {{ return({'relations': [target_relation]}) }}
{% endmacro %}

{% macro trino__alter_column_type(relation, column_name, new_column_type) %}
  {%- if config.get('sync_nested_columns', false) and (new_column_type | lower).startswith('row(') -%}
    {% call statement('alter_column_type') %}
      alter table {{ relation }} alter column {{ adapter.quote(column_name) }} set data type {{ new_column_type }}
    {% endcall %}
  {%- else -%}
  {#
    1. Create a new column (w/ temp name and correct type)
    2. Copy data over to it
    3. Drop the existing column
    4. Rename the new column to existing column
  #}
  {%- set tmp_column = column_name + "__dbt_alter" -%}

  {% call statement('alter_column_type') %}
    alter table {{ relation }} add column {{ adapter.quote(tmp_column) }} {{ new_column_type }};
    update {{ relation }} set {{ adapter.quote(tmp_column) }} = CAST({{ adapter.quote(column_name) }} AS {{ new_column_type }});
    alter table {{ relation }} drop column {{ adapter.quote(column_name) }};
    alter table {{ relation }} rename column {{ adapter.quote(tmp_column) }} to {{ adapter.quote(column_name) }}
  {% endcall %}
  {%- endif -%}
{% endmacro %}
