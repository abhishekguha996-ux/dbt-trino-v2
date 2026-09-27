select 'shipping' as model_name, cast(orderkey as varchar) as row_key
from {{ ref('shipping_revenue') }} where revenue <= 0
union all
select 'regional' as model_name, nation as row_key
from {{ ref('regional_revenue') }} where revenue <= 0
