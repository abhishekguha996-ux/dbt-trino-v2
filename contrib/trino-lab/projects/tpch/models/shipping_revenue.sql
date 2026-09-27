select o.o_orderkey as orderkey, o.o_orderdate as orderdate, o.o_shippriority as shippriority,
       sum(cast(l.l_extendedprice as decimal(18,2)) *
           (decimal '1.00' - cast(l.l_discount as decimal(4,2)))) as revenue
from {{ source('tpch', 'customer') }} c
inner join {{ source('tpch', 'orders') }} o on c.c_custkey=o.o_custkey
inner join {{ source('tpch', 'lineitem') }} l on o.o_orderkey=l.l_orderkey
where c.c_mktsegment='BUILDING'
  and o.o_orderdate < date '1995-03-15'
  and l.l_shipdate > date '1995-03-15'
group by o.o_orderkey, o.o_orderdate, o.o_shippriority
