{{ config(materialized='incremental', incremental_strategy='append') }}
select * from {{ ref('incoming') }}
{% if is_incremental() %}
where event_id > (select coalesce(max(event_id), 0) from {{ this }})
{% endif %}
