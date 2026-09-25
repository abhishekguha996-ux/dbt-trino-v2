{% macro trino__catalog_sql(information_schema) -%}
  select t.table_catalog as table_database, t.table_schema, t.table_name,
         t.table_type, cast(null as varchar) as table_owner,
         cast(null as varchar) as table_comment,
         c.column_name, c.data_type as column_type,
         cast(c.ordinal_position as decimal(38,0)) as column_index,
         c.comment as column_comment
  from {{ adapter.quote(information_schema.database) }}.information_schema.tables t
  join {{ adapter.quote(information_schema.database) }}.information_schema.columns c
    on t.table_catalog = c.table_catalog
   and t.table_schema = c.table_schema
   and t.table_name = c.table_name
{%- endmacro %}

{% macro trino__get_catalog(information_schema, schemas) -%}
  {% set query %}
    {{ trino__catalog_sql(information_schema) }}
    where false
    {% for schema in schemas %}
      or t.table_schema = {{ dbt.string_literal(schema) }}
    {% endfor %}
    order by t.table_schema, t.table_name, c.ordinal_position
  {% endset %}
  {{ return(run_query(query)) }}
{%- endmacro %}

{% macro trino__get_catalog_relations(information_schema, relations) -%}
  {% set query %}
    {{ trino__catalog_sql(information_schema) }}
    where false
    {% for relation in relations %}
      {% if not relation.schema %}
        {{ exceptions.raise_compiler_error('Trino catalog relations require a schema') }}
      {% endif %}
      or (t.table_schema = {{ dbt.string_literal(relation.schema) }}
          {% if relation.identifier %}
            and t.table_name = {{ dbt.string_literal(relation.identifier) }}
          {% endif %})
    {% endfor %}
    order by t.table_schema, t.table_name, c.ordinal_position
  {% endset %}
  {{ return(run_query(query)) }}
{%- endmacro %}
