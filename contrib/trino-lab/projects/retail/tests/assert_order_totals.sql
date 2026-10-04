select coalesce(a.order_id,e.order_id) as order_id
from {{ ref('fct_orders') }} a
full outer join {{ ref('expected_orders') }} e on a.order_id=e.order_id
where a.order_id is null or e.order_id is null
   or a.gross_cents is distinct from e.gross_cents
   or a.paid_cents is distinct from e.paid_cents
   or a.refund_cents is distinct from e.refund_cents
   or a.net_cents is distinct from e.net_cents
