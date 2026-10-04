select * from {{ ref('aggregate_checks') }} where passed is distinct from true
