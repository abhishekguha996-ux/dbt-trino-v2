{{ config(materialized='incremental', incremental_strategy='merge', unique_key='event_id') }}
select * from {{ ref('incoming') }}
