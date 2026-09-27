{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/materializations/models/incremental/on_schema_change.sql
  Changes for dbt v2 are marked "v2:".
-#}

{# Trino-specific schema change handling with nested ROW column synchronization.
   Plain-named sync_column_schemas overrides dbt-core's version in the adapter package. #}

{% macro sync_column_schemas(on_schema_change, target_relation, schema_changes_dict) %}

  {% set row_sync_dict = schema_changes_dict %}
  {% set sync_nested_columns = config.get('sync_nested_columns', false) %}

  {% if sync_nested_columns %}
    {#- v2: nested ROW sync is implemented in Jinja over adapter.diff_nested_column_types. -#}
    {% set row_sync_result = trino__sync_row_columns(
        on_schema_change,
        target_relation,
        schema_changes_dict,
      ) %}
    {% if row_sync_result is not none %}
      {% set row_sync_dict = row_sync_result %}
    {% endif %}
  {% endif %}

  {%- set add_to_target_arr = row_sync_dict['source_not_in_target'] -%}
  {%- set remove_from_target_arr = row_sync_dict['target_not_in_source'] -%}
  {%- set new_target_types = row_sync_dict['new_target_types'] -%}

  {%- if on_schema_change == 'append_new_columns' -%}
    {%- if add_to_target_arr | length > 0 -%}
      {%- do alter_relation_add_remove_columns(target_relation, add_to_target_arr, none) -%}
    {%- endif -%}

  {% elif on_schema_change == 'sync_all_columns' %}

    {% if add_to_target_arr | length > 0 or remove_from_target_arr | length > 0 %}
      {%- do alter_relation_add_remove_columns(target_relation, add_to_target_arr, remove_from_target_arr) -%}
    {% endif %}

    {% if new_target_types != [] %}
      {% for ntt in new_target_types %}
        {% set column_name = ntt['column_name'] %}
        {% set new_type = ntt['new_type'] %}
        {% do alter_column_type(target_relation, column_name, new_type) %}
      {% endfor %}
    {% endif %}

  {% endif %}

  {% set schema_change_message %}
    In {{ target_relation }}:
        Schema change approach: {{ on_schema_change }}
        Columns added: {{ add_to_target_arr }}
        Columns removed: {{ remove_from_target_arr }}
        Data types changed: {{ new_target_types }}
  {% endset %}

  {% do log(schema_change_message) %}

{% endmacro %}


{#- v2: port of TrinoAdapter.sync_row_columns (dbt-trino v1.10.5 impl.py). Applies nested ROW
    field additions (and, for sync_all_columns, removals and type changes) with
    ALTER TABLE ... {ADD|DROP|ALTER} COLUMN a.b, then removes the handled root columns from
    the schema change set so the flat column logic does not touch them. -#}
{% macro trino__sync_row_columns(on_schema_change, target_relation, schema_changes_dict) %}
  {% if on_schema_change not in ('append_new_columns', 'sync_all_columns') %}
    {{ return(schema_changes_dict) }}
  {% endif %}

  {% set source_types = {} %}
  {% for column in schema_changes_dict.get('source_columns', []) %}
    {% do source_types.update({column.name: column.data_type}) %}
  {% endfor %}
  {% set target_types = {} %}
  {% for column in schema_changes_dict.get('target_columns', []) %}
    {% do target_types.update({column.name: column.data_type}) %}
  {% endfor %}

  {% set additions = [] %}
  {% set removals = [] %}
  {% set type_changes = [] %}
  {% set handled = [] %}
  {% for name, source_type in source_types.items() if name in target_types %}
    {% set diff = adapter.diff_nested_column_types(source_type, target_types[name], name) %}
    {% if diff is not none %}
      {% do handled.append(name) %}
      {% do additions.extend(diff['additions']) %}
      {% if on_schema_change == 'sync_all_columns' %}
        {% do removals.extend(diff['removals']) %}
        {% do type_changes.extend(diff['type_changes']) %}
      {% endif %}
    {% endif %}
  {% endfor %}

  {% if not handled or not (additions or removals or type_changes) %}
    {{ return(schema_changes_dict) }}
  {% endif %}

  {% set relation_type = target_relation.type | replace('_', ' ') %}
  {% for path, _ in removals %}
    {% do run_query('alter ' ~ relation_type ~ ' ' ~ target_relation ~ ' drop column ' ~ trino__nested_column_path(path)) %}
  {% endfor %}
  {% for path, new_type in type_changes %}
    {% do run_query('alter ' ~ relation_type ~ ' ' ~ target_relation ~ ' alter column ' ~ trino__nested_column_path(path) ~ ' set data type ' ~ new_type) %}
  {% endfor %}
  {% for path, field_type in additions %}
    {% do run_query('alter ' ~ relation_type ~ ' ' ~ target_relation ~ ' add column ' ~ trino__nested_column_path(path) ~ ' ' ~ field_type) %}
  {% endfor %}

  {% set result = {} %}
  {% do result.update(schema_changes_dict) %}
  {% do result.update({
      'source_not_in_target': schema_changes_dict.get('source_not_in_target', []) | rejectattr('name', 'in', handled) | list,
      'target_not_in_source': schema_changes_dict.get('target_not_in_source', []) | rejectattr('name', 'in', handled) | list,
      'new_target_types': schema_changes_dict.get('new_target_types', []) | rejectattr('column_name', 'in', handled) | list,
      'target_columns': adapter.get_columns_in_relation(target_relation),
  }) %}
  {% if not (result['source_not_in_target'] or result['target_not_in_source'] or result['new_target_types']) %}
    {% do result.update({'schema_changed': false}) %}
  {% endif %}
  {{ return(result) }}
{% endmacro %}

{% macro trino__nested_column_path(path) -%}
  {%- set parts = [] -%}
  {%- for segment in path.split('.') -%}
    {%- do parts.append(adapter.quote(segment)) -%}
  {%- endfor -%}
  {{ parts | join('.') }}
{%- endmacro %}
