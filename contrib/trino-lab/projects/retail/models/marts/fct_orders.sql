with lines as (
    select order_id, sum(quantity * unit_cents) as gross_cents
    from {{ ref('stg_order_lines') }}
    group by order_id
)
select o.order_id, o.customer_id, o.order_date, o.status,
       coalesce(l.gross_cents, 0) as gross_cents,
       coalesce(p.paid_cents, 0) as paid_cents,
       coalesce(r.refund_cents, 0) as refund_cents,
       coalesce(p.paid_cents, 0) - coalesce(r.refund_cents, 0) as net_cents
from {{ ref('stg_orders') }} o
left join lines l on o.order_id = l.order_id
left join {{ ref('int_payments') }} p on o.order_id = p.order_id
left join {{ ref('int_refunds') }} r on o.order_id = r.order_id
