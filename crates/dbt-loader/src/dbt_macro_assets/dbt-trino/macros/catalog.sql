{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/catalog.sql
  Changes for dbt v2 are marked "v2:".
-#}

{#- v2: the first argument is the catalog.schema relation being documented; the information
    schema views are derived from it with `information_schema('<view>')`. -#}
{% macro trino__get_catalog(information_schema, schemas) -%}

    {% set query %}
        with tables as (
            {{ trino__get_catalog_tables_sql(information_schema) }}
            {{ trino__get_catalog_schemas_where_clause_sql(schemas) }}
        ),
        columns as (
            {{ trino__get_catalog_columns_sql(information_schema) }}
            {{ trino__get_catalog_schemas_where_clause_sql(schemas) }}
        ),
        table_comment as (
            {{ trino__get_catalog_table_comment_schemas_sql(information_schema, schemas) }}
        )
        {{ trino__get_catalog_results_sql() }}
    {%- endset -%}

    {{ return(run_query(query)) }}

{%- endmacro %}


{% macro trino__get_catalog_relations(information_schema, relations) -%}

    {% set query %}
        with tables as (
            {{ trino__get_catalog_tables_sql(information_schema) }}
            {{ trino__get_catalog_relations_where_clause_sql(relations) }}
        ),
        columns as (
            {{ trino__get_catalog_columns_sql(information_schema) }}
            {{ trino__get_catalog_relations_where_clause_sql(relations) }}
        ),
        table_comment as (
            {{ trino__get_catalog_table_comment_relations_sql(information_schema, relations) }}
        )
        {{ trino__get_catalog_results_sql() }}
    {%- endset -%}

    {{ return(run_query(query)) }}

{%- endmacro %}


{% macro trino__get_catalog_tables_sql(information_schema) -%}
    select
        table_catalog as "table_database",
        table_schema as "table_schema",
        table_name as "table_name",
        table_type as "table_type",
        cast(null as varchar) as "table_owner"
    from {{ information_schema.information_schema('tables') }}
{%- endmacro %}


{% macro trino__get_catalog_columns_sql(information_schema) -%}
    select
        table_catalog as "table_database",
        table_schema as "table_schema",
        table_name as "table_name",
        column_name as "column_name",
        {#- v2: the catalog reader expects DECIMAL(38, 0) column indexes. #}
        cast(ordinal_position as decimal(38, 0)) as "column_index",
        data_type as "column_type",
        comment as "column_comment"
    from {{ information_schema.information_schema('columns') }}
{%- endmacro %}


{% macro trino__get_catalog_table_comment_schemas_sql(information_schema, schemas) -%}
    select
        catalog_name as "table_database",
        schema_name as "table_schema",
        table_name as "table_name",
        comment as "table_comment"
    from system.metadata.table_comments
    where
        catalog_name = {{ trino__string_literal(information_schema.database) }}
        and
        schema_name != 'information_schema'
        and
        schema_name in ({%- for schema in schemas -%}{{ trino__string_literal(schema | lower) }}{{ ', ' if not loop.last }}{%- endfor -%})
{%- endmacro %}


{% macro trino__get_catalog_table_comment_relations_sql(information_schema, relations) -%}
    {%- for relation in relations %}
    select
        catalog_name as "table_database",
        schema_name as "table_schema",
        table_name as "table_name",
        comment as "table_comment"
    from system.metadata.table_comments
    where
        catalog_name = {{ trino__string_literal(information_schema.database) }}
        and
        schema_name != 'information_schema'
        and
        {% if relation.schema and relation.identifier %}
                (
                    schema_name = {{ trino__string_literal(relation.schema | lower) }}
                    and table_name = {{ trino__string_literal(relation.identifier | lower) }}
                )
            {% elif relation.schema %}
                (
                    schema_name = {{ trino__string_literal(relation.schema | lower) }}
                )
            {% else %}
                {% do exceptions.raise_compiler_error(
                    '`get_catalog_relations` requires a list of relations, each with a schema'
                ) %}
        {% endif %}
    {%- if not loop.last %}
    union all
    {% endif -%}
    {%- endfor -%}
{%- endmacro %}


{% macro trino__get_catalog_results_sql() -%}
        select
            table_database,
            table_schema,
            table_name,
            table_type,
            table_owner,
            column_name,
            column_index,
            column_type,
            column_comment,
            table_comment
        from tables
        join columns using ("table_database", "table_schema", "table_name")
        {#- v2: keep relations missing from system.metadata.table_comments. #}
        left join table_comment using ("table_database", "table_schema", "table_name")
        order by "column_index"
{%- endmacro %}


{% macro trino__get_catalog_schemas_where_clause_sql(schemas) -%}
    where
        table_schema != 'information_schema'
        and
        table_schema in ({%- for schema in schemas -%}{{ trino__string_literal(schema | lower) }}{{ ', ' if not loop.last }}{%- endfor -%})
{%- endmacro %}


{% macro trino__get_catalog_relations_where_clause_sql(relations) -%}
    where
        table_schema != 'information_schema'
        and
        (
            {%- for relation in relations -%}
                {% if relation.schema and relation.identifier %}
                    (
                        table_schema = {{ trino__string_literal(relation.schema | lower) }}
                        and table_name = {{ trino__string_literal(relation.identifier | lower) }}
                    )
                {% elif relation.schema %}
                    (
                        table_schema = {{ trino__string_literal(relation.schema | lower) }}
                    )
                {% else %}
                    {% do exceptions.raise_compiler_error(
                        '`get_catalog_relations` requires a list of relations, each with a schema'
                    ) %}
                {% endif %}

                {%- if not loop.last %} or {% endif -%}
            {%- endfor -%}
        )
{%- endmacro %}
