{{ config(materialized='ephemeral') }}
select * from (
  {% if var('batch', 1) == 1 %}
    values (1, 10), (2, 20)
  {% else %}
    values (2, 200), (3, 30)
  {% endif %}
) as data(event_id, amount)
