select order_date, count(*) as order_count,
       sum(gross_cents) as gross_cents, sum(net_cents) as net_cents
from {{ ref('fct_orders') }}
group by order_date
