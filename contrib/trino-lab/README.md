# Trino adapter for dbt v2 OSS — lab, tests and docs

This fork adds an **experimental Trino adapter** to the dbt v2 OSS CLI. It targets
open-source Trino with Hive, Iceberg and Delta Lake catalogs on S3, and aims for feature
parity with [dbt-trino](https://github.com/starburstdata/dbt-trino) v1.10.5. It uses the
Apache-2.0 [ADBC Trino driver](https://github.com/adbc-drivers/trino) and runs behind
`DBT_ALLOW_EXPERIMENTAL_ADAPTERS=yes`.

It is **not an official dbt Labs release** and has not been proposed upstream yet; see
[UPSTREAM.md](UPSTREAM.md).

| Document | For |
|---|---|
| [INSTALL.md](INSTALL.md) | Installing a build on Linux/Coder or macOS, and how dbt finds the driver |
| [MIGRATION.md](MIGRATION.md) | Moving a dbt 1.7 + dbt-trino project to v2 |
| [FEATURES.md](FEATURES.md) | Feature-by-feature status versus dbt-trino v1 and per connector |
| [TEST-RESULTS.md](TEST-RESULTS.md) | What was tested, how, and the results |
| [UPSTREAM.md](UPSTREAM.md) | The CLA, the PR plan and the PR texts for dbt-labs/dbt |
| [DRIVER-ISSUES.md](DRIVER-ISSUES.md) | Issue texts for adbc-drivers/trino and their issue numbers (#127 to #133, and a comment on #19) |

## Layout

```
stack/        Trino 483 + Hive metastore (Postgres) + RustFS (S3) compose stack
scripts/      stack.py (start/stop, TLS/JWT material), compare_schemas.py, fixture oracles
functional/   end-to-end tests that run the dbt binary against the stack
acceptance/   jaffle-shop-classic build, the dbt Labs acceptance bar for community adapters
projects/     retail and TPC-H example projects checked against Python-computed results
tests/        unit tests for the retail fixture generator
docs-site/    draft v2 section for the docs.getdbt.com Trino setup page
```

The adapter code itself lives in `crates/` (see [UPSTREAM.md](UPSTREAM.md#the-pr-series)).

## Run it locally (macOS or Linux)

Prerequisites: Docker, Python 3.11+, OpenSSL, `htpasswd`, Rust via `rustup` and `protoc`.

```sh
# 1. build dbt and place the ADBC Trino driver in lib/ (from adbc-drivers/trino releases)
cargo build -p dbt-sa-cli --bin dbt
mkdir -p lib && cp /path/to/libadbc_driver_trino.* lib/
export ADBC_DRIVER_PATH="$PWD/lib"

# 2. start Trino (HTTP :8080 unauthenticated, HTTPS :8443 password + JWT), metastore and S3
python3 contrib/trino-lab/scripts/stack.py up

# 3. run the functional suite; TRINO_CATALOGS narrows the catalog matrix
cd contrib/trino-lab/functional
python3 -m unittest -v
TRINO_CATALOGS=iceberg python3 -m unittest test_incremental -v

# 4. run the jaffle-shop-classic acceptance build; it keeps its logs in the results folder
../acceptance/run_jaffle_shop.sh ../../../target/debug/dbt /tmp/jaffle-results

# 5. stop (keeps data) or reset (deletes this stack's volumes)
python3 ../scripts/stack.py down
```

dbt finds a `lib/dbt/` folder near its executable by itself, so `ADBC_DRIVER_PATH` is a safeguard.
It matters for a debug build that sits below an `arrow-adbc` checkout: that build loads drivers
from the checkout instead of `lib/` and runs `make` there first.
[INSTALL.md](INSTALL.md#how-dbt-finds-the-driver) lists every place where dbt looks for the
driver.

The stack binds only to `127.0.0.1` and uses synthetic credentials generated under
`stack/.generated/` (git-ignored). Docker needs about 6 GB of memory for it. The tests need
internet access: `dbt deps` downloads `dbt_utils` from hub.getdbt.com, and the acceptance
build clones jaffle-shop-classic from GitHub.

| Variable | Default | Use |
|---|---|---|
| `DBT_BIN` | `target/debug/dbt` | the dbt binary under test |
| `TRINO_HOST`, `TRINO_PORT` | `127.0.0.1`, `8080` | the Trino HTTP endpoint for profiles and checks |
| `TRINO_CATALOGS` | `memory,hive,iceberg,delta` | the catalogs to test |
| `SCHEMA_PREFIX` | `ft_` | the prefix of the test schemas |
| `KEEP_SCHEMAS` | unset | `1` keeps test schemas and project folders for inspection |

The fork's GitHub Actions workflow (`.github/workflows/trino-fork-build.yml`) runs the Rust
checks below, builds the release archives, and runs the functional suite and the acceptance
build with the Linux x86_64 archive against this stack.

Rust checks for the crates that the series touches:

```sh
CRATES="-p dbt-adbc -p dbt-auth -p dbt-schemas -p dbt-adapter-sql -p dbt-adapter -p dbt-agate \
  -p dbt-df-providers -p dbt-loader -p dbt-tasks-sa -p dbt-profile-schemas -p dbt-init"
cargo fmt --all --check
cargo clippy $CRATES --all-targets -- -D warnings
cargo nextest run $CRATES
```

## Note on the metastore image

The stack uses `starburstdata/hive:3.1.3-e.15`, the same metastore image dbt-trino v1's own CI
uses. It is published by Starburst under a proprietary license. It's fine for local testing,
but swap in an Apache Hive standalone metastore image if that matters for your use. Nothing
in `crates/` depends on it.
