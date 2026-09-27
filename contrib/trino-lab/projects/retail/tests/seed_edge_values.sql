select 'seed edge values mismatch' as failure
where (select count(*) from {{ ref('edge_values') }}) <> 4
   or (select sum(amount) from {{ ref('edge_values') }}) <> decimal '-12.04'
   or (select note from {{ ref('edge_values') }} where id = 1) is distinct from 'O''Brien'
   or (select note from {{ ref('edge_values') }} where id = 2) is distinct from 'café 東京'
   or (select event_date from {{ ref('edge_values') }} where id = 3) is distinct from date '2026-01-03'
   or (select count(*) from {{ ref('edge_values') }} where id = 4 and note is null and amount is null and flag is null and event_date is null) <> 1
