with a(id, amount) as (
    values (1, 10), (2, 20), (2, 30), (cast(null as integer), 40), (4, cast(null as integer))
)
select 'counts_and_totals' as test_name,
    count(*) = 5 and count(amount) = 4 and count(distinct id) = 3
    and sum(amount) = 100 and avg(amount) = 25 and min(amount) = 10 and max(amount) = 40 as passed
from a
union all
select 'empty', count(*) = 0 and sum(amount) is null from a where false
union all
select 'all_null', count(amount) = 0 and sum(amount) is null from a where id = 4
union all
select 'filter', sum(amount) filter (where id = 2) = 50 from a
union all
select 'having', count(*) = 1 from (select id from a group by id having count(*) > 1)
union all
select 'rollup', count(*) = 5 and sum(total) = 200
from (select id, sum(amount) as total from a group by rollup(id))
union all
select 'grouping_sets', count(*) = 5 and sum(total) = 200
from (select id, sum(amount) as total from a group by grouping sets ((id), ()))
union all
select 'decimal', sum(v) = decimal '0.30' and avg(v) = decimal '0.15'
from (values decimal '0.10', decimal '0.20') t(v)
