{% macro trino__load_csv_rows(model, agate_table) -%}
  {% set overrides = model['config'].get('column_types', {}) %}
  {% set column_types = [] %}
  {% for name in agate_table.column_names %}
    {% set inferred_type = adapter.convert_type(agate_table, loop.index0) %}
    {% do column_types.append(overrides.get(name, inferred_type)) %}
  {% endfor %}
  {{ return(default__load_csv_rows(model, agate_table, column_types=column_types)) }}
{%- endmacro %}
