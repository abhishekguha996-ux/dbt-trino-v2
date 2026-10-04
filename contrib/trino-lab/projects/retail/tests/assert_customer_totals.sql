select coalesce(a.customer_id,e.customer_id) as customer_id
from {{ ref('customer_lifetime_value') }} a
full outer join {{ ref('expected_customers') }} e on a.customer_id=e.customer_id
where a.customer_id is null or e.customer_id is null
   or a.order_count is distinct from e.order_count
   or a.gross_cents is distinct from e.gross_cents
   or a.net_cents is distinct from e.net_cents
