{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/apply_grants.sql
  Changes for dbt v2 are marked "v2:".
-#}

{#- v2: read the relation's own catalog instead of the session catalog, match the lowercase names
    Trino stores, and leave out the current user's own privileges so that dbt never revokes
    them (dbt-postgres excludes the current role the same way). Only user grantees are read,
    because trino__get_grant_sql grants to users: dbt would otherwise revoke a role grantee as a
    user on every run, which leaves the role's grant in place. -#}
{% macro trino__get_show_grant_sql(relation) -%}
    select
        grantee,
        lower(privilege_type) as privilege_type
    from {{ relation.information_schema('table_privileges') }}
    where table_catalog = {{ trino_quoted_literal(relation.database | lower) }}
    and table_schema = {{ trino_quoted_literal(relation.schema | lower) }}
    and table_name = {{ trino_quoted_literal(relation.identifier | lower) }}
    and grantee_type = 'USER'
    and grantee != current_user
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
