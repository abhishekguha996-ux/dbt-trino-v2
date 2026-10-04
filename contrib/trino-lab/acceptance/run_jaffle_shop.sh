#!/usr/bin/env bash
# dbt Labs' acceptance bar for community adapters: a clean `dbt build` of jaffle-shop-classic
# (https://docs.getdbt.com/docs/contribute-dbt-adapters-v2). The catalogs share one Hive
# metastore, so each uses its own schema. The patch applies dbt-autofix's
# v2 YAML changes and adds one incremental model and one snapshot so table, view, incremental,
# snapshot, seeds and tests are all covered. Each catalog is built twice (create, then update).
#
#   python3 ../scripts/stack.py up && ./run_jaffle_shop.sh [path/to/dbt]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dbt="${1:-$here/../../../target/debug/dbt}"
work="$(mktemp -d)"
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
      host: localhost
      port: 8080
      user: admin
      database: $catalog
      schema: jaffle_acceptance_$catalog
      threads: 4
      roles: {hive: admin}
YML
  args=()
  if [ "$catalog" = hive ]; then
    # Plain Hive tables support neither MERGE nor snapshots in Trino.
    sed -i.bak "s/incremental_strategy='merge'/incremental_strategy='append'/" models/orders_incremental.sql
    args=(--exclude customers_snapshot)
  fi
  for run in 1 2; do
    echo "== $catalog, run $run"
    "$dbt" build --profiles-dir "profiles_$catalog" ${args[@]+"${args[@]}"} | grep -E '^Summary|Processed'
  done
done
