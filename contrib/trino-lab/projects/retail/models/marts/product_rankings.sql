with sales as (
    select p.product_id, p.product_name, p.category,
           sum(l.quantity) as units_sold, sum(l.quantity * l.unit_cents) as gross_cents
    from {{ ref('stg_products') }} p
    inner join {{ ref('stg_order_lines') }} l on p.product_id = l.product_id
    inner join {{ ref('stg_orders') }} o on l.order_id = o.order_id
    where o.status = 'complete'
    group by p.product_id, p.product_name, p.category
)
select *, dense_rank() over (partition by category order by gross_cents desc) as category_rank
from sales
