select c.customer_id, c.customer_name, c.region,
       count(o.order_id) as order_count,
       coalesce(sum(o.gross_cents), 0) as gross_cents,
       coalesce(sum(o.net_cents), 0) as net_cents
from {{ ref('stg_customers') }} c
left join {{ ref('fct_orders') }} o on c.customer_id = o.customer_id
group by c.customer_id, c.customer_name, c.region
