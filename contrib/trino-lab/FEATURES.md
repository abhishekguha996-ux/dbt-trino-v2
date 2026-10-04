# Feature status

Compared with dbt-trino v1.10.5 on open-source Trino 483. **Tested** means that a test of the
functional suite in `functional/` covers it against a live stack; the test module is named in
brackets. [TEST-RESULTS.md](TEST-RESULTS.md) records the latest results. **Unit-tested** means
Rust tests only. In the matrices, ✓ = tested, – = not supported by that Trino connector,
n/t = expected to work (connector-independent) but not in the test matrix.

## Connection and profile

| Feature | Status |
|---|---|
| `method: none` over HTTP | Tested [all modules] |
| `method: none` over HTTPS (`http_scheme: https`) | Unit-tested |
| `method: ldap` (password) over HTTPS, CA bundle via `cert` | Tested [auth] |
| Password with URL-special characters (`p@ss:w/rd%+#?&`) | Tested [auth] |
| `method: jwt` | Tested [auth] |
| `method: kerberos` (keytab) | Unit-tested; not tested against a KDC |
| `method: certificate`, `oauth`, `oauth_console`, `gssapi` | Not supported by the ADBC driver: clear error (unit-tested) |
| `cert: false` / TLS verification on by default | Tested [auth]; default differs from v1 (see MIGRATION.md) |
| `host` must be a host name; `query_timeout` as seconds or a duration; `starburst_*` keys; `role` | Tested [auth] |
| `session_properties` | Tested [features, more] |
| `roles` | Unit-tested; every lab profile sets `roles: {hive: admin}`, but no test checks the role |
| `client_tags` | Unit-tested; sent in [auth], but no test checks the tags |
| `timezone` | Accepted; driver go/v0.5.3 does not send it (see MIGRATION.md) |
| `catalog` alias for `database` | Unit-tested (`profiles.rs`) |
| `prepared_statements_enabled`, `retries` | Accepted (see MIGRATION.md) |
| `http_headers`, `impersonation_user` | Not supported by the driver: clear error (unit-tested) |
| `X-Trino-Source: dbt-trino-<version>` | Tested [auth] |
| Password / JWT redaction in logs | Tested [auth], unit-tested in `dbt-adbc` |
| `dbt init` wizard | Unit-tested (headless setup for each method); not in the functional suite |

## Materializations

| Feature | Memory | Hive | Iceberg | Delta | Tests |
|---|---|---|---|---|---|
| table, view, ephemeral, seed | ✓ | ✓ | ✓ | ✓ | basic |
| mixed-case profile schema, custom schema, model name and alias, built twice | ✓ | ✓ | ✓ | ✓ | basic |
| `on_table_exists: rename` (default) | ✓ | ✓ | ✓ | ✗¹ | basic |
| `on_table_exists: drop / skip` | ✓ | ✓ | ✓ | ✓ | basic |
| `on_table_exists: replace` | – | – | ✓ | ✓ | basic |
| `view_security: definer / invoker` | ✓ | ✓ | ✓ | ✓ | basic |
| `properties`, `file_format`, `table_format` | – | ✓ | ✓ | ✓ | basic |
| `storage_uri` sets `location` | – | –² | ✓ | ✓ | basic |
| view ↔ table switch | ✓ | ✓ | ✓ | ✓ | basic |
| a failed view → table switch keeps the view (`rename`, `skip`) | ✓ | ✓ | ✓ | ✗¹ | basic |
| materialized view (create, refresh, full refresh, `grace_period`, mixed-case names) | – | – | ✓ | – | features |
| a failed materialized-view full refresh keeps the view | – | – | ✓ | – | features |
| snapshots: timestamp, check, `hard_deletes` invalidate / new_record | – | – | ✓ | ✓ | features, more |
| contracts with `not_null` | ✓ | – | ✓ | ✓ | features |

¹ Trino can't rename managed Delta tables on a Hive metastore; use `replace`.
² The Hive connector calls this property `external_location`, so `location` does not apply
(the same in dbt-trino v1).

## Incremental

| Strategy / option | Memory | Hive | Iceberg | Delta | Tests |
|---|---|---|---|---|---|
| append (default) | ✓ | ✓ | ✓ | ✓ | incremental |
| merge (`unique_key`, composite keys, `merge_update_columns`, `merge_exclude_columns`, `incremental_predicates`) | – | – | ✓ | ✓ | incremental |
| delete+insert | – | – | ✓ | ✓ | incremental |
| microbatch (sequential batches, reruns replace batches) | – | – | ✓ | ✓ | incremental |
| `on_schema_change`: append_new_columns | ✓ | ✓ | ✓ | ✓ | incremental |
| `on_schema_change`: sync_all_columns (incl. type change on Iceberg/Delta) | n/t | ✓ | ✓ | ✓³ | incremental |
| `on_schema_change`: fail, ignore | ✓ | n/t | ✓ | n/t | incremental |
| `sync_nested_columns` (new fields keep the model's order; a missing nested ROW is added whole; a field in the middle of a ROW asks for `--full-refresh`) | – | – | ✓ | – | incremental |
| `views_enabled: false` | ✓ | n/t | ✓ | n/t | incremental |
| full refresh | ✓ | ✓ | ✓ | ✓ | incremental |

³ Delta needs `column_mapping_mode = 'name'` to drop or rename columns.

`insert_overwrite` is not a valid strategy, as in dbt-trino v1: dbt stops before it creates
anything [incremental].

## Other dbt features

| Feature | Status |
|---|---|
| Generic and singular data tests, `store_failures` | Tested [features, more, projects] |
| `sql_header` (e.g. `set session`) on tables and views | Tested on Memory [basic] |
| Unit tests | Tested [features] |
| Unit-test fixture types: dbt-trino v1's type cases (integer, varchar, boolean, date, timestamp, timestamp with time zone, decimal) and `decimal(10,2)` | Tested on Memory and Iceberg [features] |
| `uuid` values in `run_query`, enforced contracts and unit tests | Tested on Memory and Iceberg [features]. `dbt show` prints a uuid as 32 hex digits (the Arrow display of `FixedSizeBinary(16)`); these paths show the canonical text |
| Grants (Hive `sql-standard`) with revoke on change, also in a mixed-case schema; the user that runs dbt keeps its own privileges | Tested [features] |
| `persist_docs` (relation + column comments) | Tested on Hive, Iceberg, Delta; materialized views on Iceberg [features] |
| Hooks, `on-run-start` / `on-run-end`, `set session` in pre-hooks | Tested [features] |
| Query comments (default and custom, `append`) | Tested [more] |
| Custom schemas | Tested on all catalogs [more] |
| `dbt debug`, `parse`, `compile`, `list`, `show` (incl. `--inline`), `retry`, `--empty` | Tested [features] |
| `dbt clone` (views over the source) | Tested on Iceberg [features] |
| `--defer` without `--favor-state` | Tested on Memory and Iceberg [features] |
| `dbt docs generate` / `compile --write-catalog` | Tested [features] |
| Source freshness (`loaded_at_field`) | Tested [features] |
| Cross-database macros (`datediff`, `dateadd`, `listagg`, `split_part`, `hash`, `date_spine`, …); `dbt.string_literal` keeps dbt's default | Tested [features] |
| Packages (`dbt_utils` 1.3) | Tested [more] |
| Seeds: type inference (v1-compatible), `column_types`, JSON, Unicode, quotes, `%s`, nulls, a 2,500-row seed (inserted in batches of up to 1,000 rows) | Tested [features] |
| Python models | Not supported (as in v1) |
| `catalogs.yml` catalog integrations (dbt-trino 1.10) | Not yet: clear error when `catalog_name` is set [more] |
| Per-model `client_tags` / `http_headers` routing (dbt-trino 1.10) | Not supported yet |
| `map`, `row`, `time with time zone` and HyperLogLog values in `run_query` | Differ from v1: Go-formatted text, and HyperLogLog fails (driver: adbc-drivers/trino#19 for `map` and `row`; see [DRIVER-ISSUES.md](DRIVER-ISSUES.md)). Arrays become one column per element (dbt v2) |
| Static analysis / column-level lineage | Not in the dbt v2 OSS build for any adapter |
| Ctrl-C cancelling server queries | Known driver limitation [more, expected failure]; see [DRIVER-ISSUES.md](DRIVER-ISSUES.md) |
| Microbatch `concurrent_batches` | Sequential, with dbt's warning (Iceberg/Delta commit conflicts) |
