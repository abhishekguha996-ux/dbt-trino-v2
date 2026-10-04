#!/usr/bin/env bash
# dbt Labs' acceptance bar for community adapters: a clean `dbt build` of jaffle-shop-classic
# (https://docs.getdbt.com/docs/contribute-dbt-adapters-v2). The catalogs share one Hive
# metastore, so each uses its own schema. The patch applies dbt-autofix's
# v2 YAML changes and adds one incremental model (with a uniqueness test) and one snapshot so
# table, view, incremental, snapshot, seeds and tests are all covered. Each catalog is built
# twice (create, then update).
#
#   python3 ../scripts/stack.py up && ./run_jaffle_shop.sh [path/to/dbt] [results-dir]
#
# Every build keeps its console output, dbt.log, query_log.sql and run_results.json in
# results-dir/<catalog>/run<n>/ (default results-dir: a new temporary directory).
# TRINO_HOST and TRINO_PORT select the Trino endpoint (default 127.0.0.1:8080).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dbt="${1:-$here/../../../target/debug/dbt}"
work="$(mktemp -d)"
results="${2:-$work/results}"
mkdir -p "$results"
results="$(cd "$results" && pwd)"
{
  echo "dbt --version: $("$dbt" --version)"
  echo "lab commit: $(git -C "$here" rev-parse HEAD)"
  echo "jaffle-shop-classic commit: fd7bfac"
} | tee "$results/versions.txt"
git clone -q https://github.com/dbt-labs/jaffle-shop-classic.git "$work/jaffle"
cd "$work/jaffle"
git checkout -q fd7bfac   # 2024-04-18, pinned
git apply "$here/jaffle-shop-classic-v2.patch"
export DBT_ALLOW_EXPERIMENTAL_ADAPTERS=yes
for catalog in iceberg delta hive; do
  mkdir -p "profiles_$catalog"
  cat > "profiles_$catalog/profiles.yml" <<YML
jaffle_shop:
  target: t
  outputs:
    t:
      type: trino
      method: none
      host: ${TRINO_HOST:-127.0.0.1}
      port: ${TRINO_PORT:-8080}
      user: admin
      database: $catalog
      schema: jaffle_acceptance_$catalog
      threads: 4
      roles: {hive: admin}
YML
  args=()
  if [ "$catalog" = hive ]; then
    # Plain Hive tables support neither MERGE nor snapshots in Trino. An append must not
    # select the last loaded day again, or every rebuild duplicates its orders.
    sed -i.bak -e "s/incremental_strategy='merge'/incremental_strategy='append'/" \
      -e "s/order_date >= /order_date > /" models/orders_incremental.sql
    args=(--exclude customers_snapshot)
  fi
  for run in 1 2; do
    echo "== $catalog, run $run"
    out="$results/$catalog/run$run"
    mkdir -p "$out"
    status=0
    rm -f target/run_results.json
    "$dbt" build --profiles-dir "profiles_$catalog" --log-path "$out" ${args[@]+"${args[@]}"} \
      > "$out/console.log" 2>&1 || status=$?
    if [ -f target/run_results.json ]; then
      cp target/run_results.json "$out/run_results.json"
    fi
    grep -E '^Summary|Processed' "$out/console.log" || true
    if [ "$status" -ne 0 ]; then
      tail -n 40 "$out/console.log"
      echo "dbt build failed for $catalog (run $run); logs: $out"
      exit "$status"
    fi
  done
done
echo "Logs and run_results.json: $results"
