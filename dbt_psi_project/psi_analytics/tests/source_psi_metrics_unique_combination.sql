-- This test checks for duplicate combinations of url, timestamp, and strategy
-- in the psi_metrics source table.
-- It will fail if any combination appears more than once.

SELECT
    url,
    timestamp,
    strategy,
    COUNT(*) AS occurrences
FROM {{ source('psi_data', 'psi_metrics') }}
GROUP BY
    url,
    timestamp,
    strategy
HAVING
    COUNT(*) > 1
