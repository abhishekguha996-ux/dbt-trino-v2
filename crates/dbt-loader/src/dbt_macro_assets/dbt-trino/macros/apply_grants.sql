{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/apply_grants.sql
  Changes for dbt v2 are marked "v2:".
-#}

{% macro trino__get_show_grant_sql(relation) -%}
    select
        grantee,
        lower(privilege_type) as privilege_type
    {#- v2: read the relation's own catalog instead of the session catalog. #}
    from {{ relation.information_schema('table_privileges') }}
    where table_catalog = {{ trino__string_literal(relation.database) }}
    and table_schema = {{ trino__string_literal(relation.schema) }}
    and table_name = {{ trino__string_literal(relation.identifier) }}
{%- endmacro %}

{% macro trino__copy_grants() %}
    {#
        -- This macro should return true or false depending on the answer to
        -- following question:
        -- when an object is fully replaced on your database, do grants copy over?
        -- e.g. on Postgres this is never true,
        -- on Spark this is different for views vs. non-Delta tables vs. Delta tables,
        -- on Snowflake it depends on the user-supplied copy_grants configuration.
        -- true by default, which means “play it safe”: grants MIGHT have copied over,
        -- so dbt will run an extra query to check them + calculate diffs.
    #}
    {{ return(False) }}
{% endmacro %}

{%- macro trino__get_grant_sql(relation, privilege, grantees) -%}
    grant {{ privilege }} on {{ relation }} to {{ adapter.quote(grantees[0]) }}
{%- endmacro %}

{%- macro trino__support_multiple_grantees_per_dcl_statement() -%}
    {#
        -- This macro should return true or false depending on the answer to
        -- following question:
        -- does this database support grant {privilege} to user_a, user_b, ...?
        -- or do user_a + user_b need their own separate grant statements?
    #}
    {{ return(False) }}
{%- endmacro -%}

{% macro trino__call_dcl_statements(dcl_statement_list) %}
    {% for dcl_statement in dcl_statement_list %}
        {% call statement('grant_or_revoke') %}
            {{ dcl_statement }}
        {% endcall %}
    {% endfor %}
{% endmacro %}
