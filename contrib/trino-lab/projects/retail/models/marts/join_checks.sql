with a(id, amount) as (
    values (1, 10), (2, 20), (2, 30), (cast(null as integer), 40), (4, cast(null as integer))
), b(id, units) as (
    values (2, 3), (2, 4), (3, 5), (cast(null as integer), 6)
)
select 'inner' as test_name, count(*) as actual_count, 4 as expected_count from a inner join b on a.id = b.id
union all select 'left', count(*), 7 from a left join b on a.id = b.id
union all select 'right', count(*), 6 from a right join b on a.id = b.id
union all select 'full', count(*), 9 from a full outer join b on a.id = b.id
union all select 'cross', count(*), 20 from a cross join b
union all select 'self', count(*), 6 from a x join a y on x.id = y.id
union all select 'non_equality', count(*), 5 from a join b on a.id < b.id
union all select 'exists', count(*), 2 from a where exists (select 1 from b where a.id = b.id)
union all select 'not_exists', count(*), 3 from a where not exists (select 1 from b where a.id = b.id)
