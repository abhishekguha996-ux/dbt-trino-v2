select n.n_name as nation,
       sum(cast(l.l_extendedprice as decimal(18,2)) *
           (decimal '1.00' - cast(l.l_discount as decimal(4,2)))) as revenue
from {{ source('tpch', 'customer') }} c
inner join {{ source('tpch', 'orders') }} o on c.c_custkey=o.o_custkey
inner join {{ source('tpch', 'lineitem') }} l on o.o_orderkey=l.l_orderkey
inner join {{ source('tpch', 'supplier') }} s on l.l_suppkey=s.s_suppkey
inner join {{ source('tpch', 'nation') }} n on c.c_nationkey=n.n_nationkey and s.s_nationkey=n.n_nationkey
inner join {{ source('tpch', 'region') }} r on n.n_regionkey=r.r_regionkey
where r.r_name='ASIA'
  and o.o_orderdate >= date '1994-01-01'
  and o.o_orderdate < date '1995-01-01'
group by n.n_name
