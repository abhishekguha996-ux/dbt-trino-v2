select * from {{ ref('join_checks') }} where actual_count <> expected_count
