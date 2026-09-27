{#-
  Vendored from dbt-trino v1.10.5 (Apache-2.0):
  https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/materializations/seeds/helpers.sql
  Changes for dbt v2 are marked "v2:".
-#}

{% macro trino__get_batch_size() %}
  {{ return(1000) }}
{% endmacro %}


{#- Returns (placeholder, value) pairs for one seed row. A placeholder of none means the value
    is already a SQL expression.

    v2: bindings are rendered as SQL literals by the adapter, so non-string values are cast to
    the declared column type (a DATE literal cannot be inserted into a TIMESTAMP column), and
    typed literals such as JSON '...' take their text from a binding so it is escaped and
    never scanned for placeholders. -#}
{% macro create_bindings(row, types) %}
  {% set values = [] %}
  {% set re = modules.re %}

  {%- for item in row -%}
      {%- set type = types[loop.index0] -%}
      {%- set match_type = re.match("(\w+)(\(.*\))?", type) -%}
      {%- set base_type = match_type.group(1).upper() -%}
      {%- if item is none -%}
        {%- do values.append((none, "NULL")) -%}
      {%- elif item is string and 'INTERVAL' in base_type -%}
        {%- do values.append((none, base_type ~ " " ~ item)) -%}
      {%- elif item is string and 'varchar' not in type.lower() -%}
        {%- do values.append((base_type ~ " " ~ get_binding_char(), item)) -%}
      {%- elif item is string -%}
        {%- do values.append((get_binding_char(), item | string)) -%}
      {%- else -%}
        {%- do values.append(("cast(" ~ get_binding_char() ~ " as " ~ type ~ ")", item)) -%}
      {% endif -%}
  {%- endfor -%}
  {{ return(values) }}
{% endmacro %}


{#
  We need to override the default__load_csv_rows macro as Trino requires values to be typed according to the column type
  as in following example:

  create table "memory"."default"."string_type" ("varchar_example" varchar,"varchar_n_example" varchar(10),"char_example" char,"char_n_example" char(10),"varbinary_example" varbinary,"json_example" json)

  insert into "memory"."default"."string_type" ("varchar_example", "varchar_n_example", "char_example", "char_n_example", "varbinary_example", "json_example") values
          ('test','abc',CHAR 'd',CHAR 'ghi',VARBINARY '65683F',JSON '{"k1":1,"k2":23,"k3":456}'),(NULL,NULL,NULL,NULL,NULL,NULL)
#}

{% macro trino__load_csv_rows(model, agate_table) %}
  {% set column_override = model['config'].get('column_types', {}) %}
  {% set types = [] %}

  {%- for col_name in agate_table.column_names -%}
      {%- set inferred_type = adapter.convert_type(agate_table, loop.index0) -%}
      {%- set type = column_override.get(col_name, inferred_type) -%}
      {%- do types.append(type) -%}
  {%- endfor -%}

  {#- v2: values are inlined, so keep each statement well below Trino's default
      query.max-length of 1,000,000 characters for wide seeds. -#}
  {% set columns = [agate_table.column_names | length, 1] | max %}
  {% set batch_size = [get_batch_size(), [20000 // columns, 1] | max] | min %}

  {% set cols_sql = get_seed_column_quoted_csv(model, agate_table.column_names) %}

  {% set statements = [] %}

  {% for chunk in agate_table.rows | batch(batch_size) %}
      {% set bindings = [] %}

      {% set sql %}
          insert into {{ this.render() }} ({{ cols_sql }}) values
          {% for row in chunk -%}
              ({%- for tuple in create_bindings(row, types) -%}
                  {%- if tuple.0 is not none  -%}
                  {{ tuple.0 }}
                  {%- do bindings.append(tuple.1) -%}
                  {%- else -%}
                  {{ tuple.1 }}
                  {%- endif -%}
                  {%- if not loop.last%},{%- endif %}
              {%- endfor -%})
              {%- if not loop.last%},{%- endif %}
          {%- endfor %}
      {% endset %}

      {% do adapter.add_query(sql, bindings=bindings, abridge_sql_log=True) %}

      {% if loop.index0 == 0 %}
          {% do statements.append(sql) %}
      {% endif %}
  {% endfor %}

  {# Return SQL so we can render it out into the compiled files #}
  {{ return(statements[0]) }}
{% endmacro %}
