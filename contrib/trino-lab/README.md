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
| [INSTALL.md](INSTALL.md) | Installing a build on Linux/Coder or macOS |
| [MIGRATION.md](MIGRATION.md) | Moving a dbt 1.7 + dbt-trino project to v2 |
| [FEATURES.md](FEATURES.md) | Feature-by-feature status versus dbt-trino v1 and per connector |
| [TEST-RESULTS.md](TEST-RESULTS.md) | What was tested, how, and the results |
| [UPSTREAM.md](UPSTREAM.md) | PR series, maintainer decisions and driver issues for later |

## Layout

```
stack/        Trino 483 + Hive metastore (Postgres) + RustFS (S3) compose stack
scripts/      stack.py (start/stop, TLS/JWT material), compare_schemas.py, fixture oracles
functional/   end-to-end tests that run the dbt binary against the stack
projects/     retail and TPC-H example projects checked against Python-computed results
tests/        unit tests for the retail fixture generator
```

The adapter code itself lives in `crates/` (see [UPSTREAM.md](UPSTREAM.md#suggested-pr-series)).

## Run it locally (macOS or Linux)

Prerequisites: Docker, Python 3.11+, OpenSSL, `htpasswd`, Rust via `rustup` and `protoc`.

```sh
# 1. build dbt and place the ADBC Trino driver next to it (from adbc-drivers/trino releases)
cargo build -p dbt-sa-cli --bin dbt
mkdir -p lib && cp /path/to/libadbc_driver_trino.* lib/

# 2. start Trino (HTTP :8080 unauthenticated, HTTPS :8443 password + JWT), metastore and S3
python3 contrib/trino-lab/scripts/stack.py up

# 3. run the functional suite (about 5 minutes); TRINO_CATALOGS narrows the catalog matrix
cd contrib/trino-lab/functional
python3 -m unittest -v
TRINO_CATALOGS=iceberg python3 -m unittest test_incremental -v

# 4. stop (keeps data) or reset (deletes this stack's volumes)
python3 ../scripts/stack.py down
```

The stack binds only to `127.0.0.1` and uses synthetic credentials generated under
`stack/.generated/` (git-ignored). Docker needs about 6 GB of memory for it. `KEEP_SCHEMAS=1`
keeps test schemas and project directories for inspection.

Rust checks for the touched crates:

```sh
cargo nextest run -p dbt-auth -p dbt-adbc -p dbt-adapter-sql -p dbt-adapter -p dbt-adapter-core \
  -p dbt-schemas -p dbt-loader -p dbt-profile-schemas -p dbt-init -p dbt-df-providers
cargo clippy -p dbt-adapter -p dbt-auth -p dbt-loader --all-targets -- -D warnings
```

## Note on the metastore image

The stack uses `starburstdata/hive:3.1.3-e.15`, the same metastore image dbt-trino v1's own CI
uses. It is published by Starburst under a proprietary license. It's fine for local testing,
but swap in an Apache Hive standalone metastore image if that matters for your use. Nothing
in `crates/` depends on it.
