select order_id, sum(amount_cents) as refund_cents
from {{ ref('stg_refunds') }}
group by order_id
