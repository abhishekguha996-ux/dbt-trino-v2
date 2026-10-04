select coalesce(cast(a.order_date as varchar),cast(e.order_date as varchar)) as order_date
from {{ ref('daily_sales') }} a
full outer join {{ ref('expected_daily') }} e on cast(a.order_date as date)=cast(e.order_date as date)
where a.order_date is null or e.order_date is null
   or a.order_count is distinct from e.order_count
   or a.gross_cents is distinct from e.gross_cents
   or a.net_cents is distinct from e.net_cents
