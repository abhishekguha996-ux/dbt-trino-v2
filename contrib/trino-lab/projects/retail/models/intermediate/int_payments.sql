select order_id, sum(amount_cents) as paid_cents
from {{ ref('stg_payments') }}
group by order_id
