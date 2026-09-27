# Feature status

Compared with dbt-trino v1.10.5 on open-source Trino 483. **Tested** means covered by the
functional suite in `functional/` against a live stack; the test module is named in brackets.
In the matrices, ✓ = tested and passing, – = not supported by that Trino connector, n/t = expected
to work (connector-independent) but not in the test matrix.

## Connection and profile

| Feature | Status |
|---|---|
| `method: none` over HTTP/HTTPS | Tested [auth, all] |
| `method: ldap` (password) over HTTPS, CA bundle via `cert` | Tested [auth] |
| `method: jwt` | Tested [auth] |
| `method: kerberos` (keytab) | Unit-tested DSN mapping; not tested against a KDC |
| `method: certificate`, `oauth`, `oauth_console`, `gssapi` | Not supported by the ADBC driver: clear error |
| `cert: false` / TLS verification on by default | Tested [auth]; default differs from v1 (see MIGRATION.md) |
| `roles`, `session_properties`, `client_tags`, `timezone` | Tested [auth, more, features] |
| `catalog` alias for `database` | Tested [all projects] |
| `prepared_statements_enabled`, `retries` | Accepted (see MIGRATION.md) |
| `http_headers`, `impersonation_user` | Not supported by the driver: clear error |
| `X-Trino-Source: dbt-trino-<version>` | Tested [auth] |
| Password / JWT redaction in logs | Tested [auth], unit-tested in `dbt-adbc` |
| `dbt init` wizard | Implemented |

## Materializations

| Feature | Memory | Hive | Iceberg | Delta | Tests |
|---|---|---|---|---|---|
| table, view, ephemeral, seed | ✓ | ✓ | ✓ | ✓ | basic |
| `on_table_exists: rename` (default) | ✓ | ✓ | ✓ | ✗¹ | basic |
| `on_table_exists: drop / skip` | ✓ | ✓ | ✓ | ✓ | basic |
| `on_table_exists: replace` | – | – | ✓ | ✓ | basic |
| `view_security: definer / invoker` | ✓ | ✓ | ✓ | ✓ | basic |
| `properties`, `file_format`, `table_format` | – | ✓ | ✓ | ✓ | basic |
| view ↔ table switch | ✓ | ✓ | ✓ | ✓ | basic |
| materialized view (create, refresh, full refresh, `grace_period`) | – | – | ✓ | – | features |
| snapshots: timestamp, check, `hard_deletes` invalidate / new_record | – | – | ✓ | ✓ | features, more |
| contracts with `not_null` | ✓ | – | ✓ | ✓ | features |

¹ Trino can't rename managed Delta tables on a Hive metastore; use `replace`.

## Incremental

| Strategy / option | Memory | Hive | Iceberg | Delta | Tests |
|---|---|---|---|---|---|
| append (default) | ✓ | ✓ | ✓ | ✓ | incremental |
| merge (`unique_key`, composite keys, `merge_update_columns`, `merge_exclude_columns`, `incremental_predicates`) | – | – | ✓ | ✓ | incremental |
| delete+insert | – | – | ✓ | ✓ | incremental |
| microbatch (sequential batches, reruns replace batches) | – | – | ✓ | ✓ | incremental |
| **insert_overwrite** (new, Hive partition overwrite) | – | ✓ | error² | error² | incremental |
| `on_schema_change`: append_new_columns | ✓ | ✓ | ✓ | ✓ | incremental |
| `on_schema_change`: sync_all_columns (incl. type change on Iceberg/Delta) | n/t | ✓ | ✓ | ✓³ | incremental |
| `on_schema_change`: fail, ignore | ✓ | n/t | ✓ | n/t | incremental |
| `sync_nested_columns` (nested ROW fields) | – | – | ✓ | – | incremental |
| `views_enabled: false` | ✓ | n/t | ✓ | n/t | incremental |
| full refresh | ✓ | ✓ | ✓ | ✓ | incremental |

² Clear compile error pointing to `merge` / `delete+insert`.
³ Delta needs `column_mapping_mode = 'name'` to drop or rename columns.

## Other dbt features

| Feature | Status |
|---|---|
| Generic and singular data tests, `store_failures` | Tested [features, more, projects] |
| `sql_header` (e.g. `set session`) on tables and views | Tested on Memory [basic] |
| Unit tests | Tested [features] |
| Grants (Hive `sql-standard`) with revoke on change | Tested [features] |
| `persist_docs` (relation + column comments) | Tested on Hive, Iceberg, Delta [features] |
| Hooks, `on-run-start` / `on-run-end`, `set session` in pre-hooks | Tested [features] |
| Query comments (default and custom, `append`) | Tested [more] |
| Custom schemas | Tested on all catalogs [more] |
| `dbt debug`, `parse`, `compile`, `list`, `show` (incl. `--inline`), `retry`, `--empty` | Tested [features] |
| `dbt clone` (views over the source) | Tested on Iceberg [features] |
| `dbt docs generate` / `compile --write-catalog` | Tested [features] |
| Source freshness (`loaded_at_field`) | Tested [features] |
| Cross-database macros (`datediff`, `dateadd`, `listagg`, `split_part`, `hash`, `date_spine`, …) | Tested [features] |
| Packages (`dbt_utils` 1.3) | Tested [more] |
| Seeds: type inference (v1-compatible), `column_types`, JSON, Unicode, quotes, `%s`, nulls, 2,500-row batches | Tested [features] |
| `dbt init` | Implemented |
| Python models | Not supported (as in v1) |
| `catalogs.yml` catalog integrations (dbt-trino 1.10) | Not yet: clear error when `catalog_name` is set |
| Per-model `client_tags` / `http_headers` routing (dbt-trino 1.10) | Not supported (driver) |
| Static analysis / column-level lineage | Not in the dbt v2 OSS build for any adapter |
| Ctrl-C cancelling server queries | Known driver limitation [more, expected failure] |
| Microbatch `concurrent_batches` | Sequential, with dbt's warning (Iceberg/Delta commit conflicts) |
