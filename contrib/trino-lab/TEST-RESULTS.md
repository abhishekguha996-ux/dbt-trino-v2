# Test results — 27 September 2026

Experimental adapter; this is a test record, not a production-readiness claim.

| Component | Version |
|---|---|
| dbt | v2 OSS CLI (`dbt-sa-cli`) from this fork, rebased on dbt-labs/dbt `main` (2.0.7) |
| Build | Native macOS ARM64, Rust 1.96, debug profile |
| Trino | 483 (single node) |
| Metastore / storage | Hive metastore 3.1.3 on Postgres 18; RustFS (S3 API) |
| Catalogs | `memory`, `hive` (`sql-standard` security), `iceberg`, `delta`, `tpch` |
| ADBC driver | adbc-drivers/trino `go/v0.5.3` |
| Auth | HTTP unauthenticated; HTTPS with password file and JWT (RS256), lab CA |

## Rust

| Check | Result |
|---|---|
| `cargo nextest` on dbt-adapter, dbt-adapter-sql, dbt-adapter-core, dbt-auth, dbt-adbc, dbt-schemas, dbt-loader, dbt-init, dbt-profile-schemas, dbt-df-providers | **2,891 passed**, 0 failed, 22 skipped |
| `cargo clippy --all-targets -D warnings` on the same crates | clean |
| `cargo fmt --check` | clean |

New Trino tests include:
- **dbt-auth**: 12 tests covering every v1 profile field, TLS options, injection resistance and unsupported methods.
- **dbt-loader**: 12 macro tests covering CTAS modes, properties, view security, rename/drop per relation type, catalog SQL, merge, delete+insert, seed bindings and nested paths.
- **dbt-adapter**: literal formatting, `TIMESTAMP` microbatch filters, column type labels and predicates, `from_description` for nested types, and materialized-view listing SQL.
- **dbt-adapter-sql**: nested `ROW` diffing and type round-trips.
- **dbt-adbc**: `accessToken` redaction.

## Functional suite (`functional/`, live stack)

`python3 -m unittest test_basic test_incremental test_features test_more test_auth test_projects`

**72 tests, all passed (1 expected failure), 4 min 53 s.** Most tests loop over the catalogs as
subtests.

| Module | Tests | Covers |
|---|---|---|
| test_basic | 12 | seeds/tables/views/ephemeral, reruns, relation-type switches, `on_table_exists` (4 modes + Delta limitation), `view_security`, `properties`, `file_format` conflicts, `sql_header` |
| test_incremental | 21 | append, merge (keys, update/exclude columns, predicates), delete+insert, microbatch (reruns, 7 daily batches), Hive `insert_overwrite`, all `on_schema_change` modes incl. type changes, nested ROW sync, `views_enabled`, full refresh |
| test_features | 21 | snapshots (timestamp, check, hard deletes), materialized views (create, refresh, full refresh, replace a table), grants and revokes, persist_docs, contracts, seeds (types, escaping, JSON, overrides, 2,500 rows, v1 integer inference), unit tests, hooks, session properties, cross-database macros, debug/parse/compile/list/show, docs + catalog.json, `--empty`, retry, source freshness, clone |
| test_more | 9 | query comments, custom schemas, `store_failures`, snapshot `new_record`, enforced `query_max_run_time`, `dbt_utils`, `catalog_name` error, Python model rejection, Ctrl-C (**expected failure**) |
| test_auth | 7 | LDAP-style password + CA bundle, wrong password (redacted), JWT, `cert: false`, untrusted certificate, password over HTTP refused, `dbt-trino-*` source header |
| test_projects | 2 | retail (36 nodes) on all four catalogs against Python-generated expectations; TPC-H Q3/Q5-style marts on all four catalogs against a Python/Decimal oracle |

Fixture unit tests (`tests/`): 2 passed.

## Known limits found by testing

- **Ctrl-C cancellation.** Queries keep running on Trino until `query.client.timeout` because
  the ADBC driver's cancel doesn't reach queries whose results are being read. Test:
  `test_more.TestSessionLimits.test_ctrl_c_stops_server_query`.
- **Microbatch `concurrent_batches`.** Iceberg rejects concurrent batch commits ("Found new
  conflicting delete files"), so batches stay sequential.
- **Delta on a Hive metastore.** No managed-table or view renames (use `on_table_exists:
  replace`); dropping columns needs `column_mapping_mode='name'`. These are Trino behaviors,
  shared with dbt-trino v1.
- **Lab only.** Kerberos is unit-tested only (no KDC in the stack). No multi-node Trino, AWS
  S3, AWS Glue or production metastore was tested. The Linux x86_64 binary is built by the
  fork's GitHub Actions workflow; the functional suite ran on the macOS ARM64 build.

## Reproduce

See [README.md](README.md#run-it-locally-macos-or-linux).
