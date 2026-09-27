# Migrating a dbt 1.7 + dbt-trino project to dbt v2

This guide covers moving an existing project from **dbt-core 1.7.x with dbt-trino** to the
experimental **dbt v2 OSS Trino adapter** in this fork. It targets open-source Trino with Hive,
Iceberg and Delta Lake catalogs on object storage, and HTTPS authentication.

Do it in two steps. Each step can be rolled back independently.

1. **Upgrade to the latest dbt v1** (dbt-core 1.10/1.11 with dbt-trino 1.10.x) and clear every
   deprecation warning. v2 turns most of those warnings into errors.
2. **Run the same project on dbt v2**, side by side with v1 on a separate schema, compare the
   outputs, then switch.

---

## Step 1 — dbt 1.7.19 → latest dbt v1

```sh
python -m pip install "dbt-core~=1.10" "dbt-trino~=1.10"
dbt deps && dbt parse --show-all-deprecations
```

Since 1.8, adapters install separately from dbt-core. Changes that affect most 1.7 projects:

| Change (version) | What to do |
|---|---|
| Generic test `tests:` key → `data_tests:` (1.8) | Rename in YAML (both still load in v1) |
| Unit tests (1.8) | Optional; they run on v2 too |
| Snapshots in YAML, `hard_deletes`, `snapshot_meta_column_names`, `dbt_valid_to_current` (1.9) | Optional; existing Jinja snapshots keep working |
| Generic test arguments under `arguments:` (1.10) | **Required in v2** (`DbtYamlValidationError dbt1159`) |
| Source `freshness` / `loaded_at_field` under `config:` (1.10) | **Required in v2** (`UnusedConfigKey dbt1060`) |
| Custom top-level keys in YAML/config (1.10) | Move under `meta:`; v2 rejects unknown config keys |
| `require_certificate_validation` flag (dbt-trino 1.9) | Set `cert:` explicitly now; see below |

dbt Labs' [dbt-autofix](https://github.com/dbt-labs/dbt-autofix) rewrites most of the YAML
deprecations automatically. Upgrade packages to versions that support v2, for example
`dbt_utils >= 1.3`. Run `dbt build` on v1 until it's clean with no deprecation warnings.

## Step 2 — dbt v2

Install the build ([INSTALL.md](INSTALL.md)), set `DBT_ALLOW_EXPERIMENTAL_ADAPTERS=yes`, and point
a **separate target** at a scratch schema:

```yaml
    v2_check:
      type: trino
      # ... same connection settings as prod ...
      schema: analytics_v2_check
```

```sh
dbt debug --target v2_check
dbt parse --target v2_check          # fixes most project-level differences first
dbt build --target v2_check --full-refresh
python3 contrib/trino-lab/scripts/compare_schemas.py \
  --host trino.internal.example.com --user "$TRINO_USER" --password-env TRINO_PASSWORD \
  --catalog hive --left analytics --right analytics_v2_check
```

`compare_schemas.py` compares relation types, column types, row counts and an
order-independent checksum of every relation present in both schemas. It only reads data.

### Profile differences

| dbt-trino v1 profile option | dbt v2 |
|---|---|
| `method: none / ldap / jwt` | Supported |
| `method: kerberos` | Supported with `keytab` + `principal` (`user@REALM`); `krb5_config` or `KRB5_CONFIG` for the config file. `hostname_override`, `force_preemptive`, `delegate` and mutual authentication are not supported by the driver |
| `method: certificate`, `oauth`, `oauth_console`, `gssapi` | **Not supported** by the ADBC Trino driver; use `jwt` with a token instead of OAuth |
| `http_headers`, `impersonation_user` | **Not supported** by the driver; the profile fails with a clear error |
| `cert` | **Default changed:** v2 verifies TLS certificates when `cert` is unset (v1 skipped verification unless `require_certificate_validation` was on). Set `cert: /path/to/ca.pem` for internal CAs, or `cert: false` to keep v1's behavior |
| `roles`, `session_properties`, `client_tags`, `timezone`, `catalog` alias | Supported |
| `prepared_statements_enabled` | Accepted; v2 always renders seed values as literals, and the option only controls the driver's prepared-statement mode |
| `retries` | Accepted and ignored (no client-side retry in the driver) |
| New: `query_timeout` | Client-side timeout, for example `2h` |
| `X-Trino-Source` | Still `dbt-trino-<version>`, so resource-group selectors keep matching |

Per-model `client_tags` / `http_headers` query routing (dbt-trino 1.10) and `catalogs.yml`
catalog integrations are not available yet.

### Project and behavior differences

| Area | dbt v2 behavior |
|---|---|
| Unknown config keys | Errors (`dbt1060`). All dbt-trino keys are recognised: `properties`, `on_table_exists`, `view_security`, `views_enabled`, `sync_nested_columns`, `grace_period`, `file_format`, `table_format` |
| `dbt docs generate` | Produces a static site in `target/`; use `dbt compile --write-catalog` for `catalog.json` |
| Unit tests | Same YAML; a failing unit test is recorded as `error` in `run_results.json` |
| Static analysis / column lineage | Not part of the dbt v2 OSS build for any adapter; disabled for Trino |
| Python models | Not supported (as in dbt-trino v1) |
| Seeds | Same types as v1 (`INTEGER`, `DOUBLE`, `VARCHAR`, `DATE`, `TIMESTAMP`, `BOOLEAN`); whole numbers beyond 32 bits become `BIGINT` instead of failing |
| New: `incremental_strategy: insert_overwrite` | Partition overwrite on Hive connector catalogs |
| `sql_header` | Now applied to tables and views (statements are split on `;`) |

### Connector limits (same as dbt-trino v1)

These come from Trino itself, not the adapter:

- **Delta Lake on a Hive metastore can't rename managed tables or views.** Use
  `on_table_exists: replace` for Delta models (Trino supports `CREATE OR REPLACE TABLE` there).
- **Delta Lake drops or renames columns only with column mapping**
  (`properties: {column_mapping_mode: "'name'"}`), which `on_schema_change: sync_all_columns`
  needs.
- **Plain Hive tables don't support `MERGE` or row-level `DELETE`.** Use `append` or the new
  `insert_overwrite`; `merge`, `delete+insert`, `microbatch` and snapshots need Iceberg or
  Delta.
- **Materialized views** exist only on the Iceberg connector in OSS Trino.
- **Grants** need a connector with access-control support (Hive `sql-standard` security).

### Operational notes

- **Interrupting a run:** with ADBC Trino driver go/v0.5.3, Ctrl-C stops dbt, but a query
  already running keeps running until Trino abandons it after `query.client.timeout` (5 minutes
  by default). Set `session_properties: {query_max_run_time: ...}` as a guardrail. This is a
  driver issue, tracked in [UPSTREAM.md](UPSTREAM.md#driver-issues).
- **Microbatch** batches run sequentially. `concurrent_batches: true` logs a warning and is
  ignored: concurrent `DELETE` + `INSERT` batches conflict in Iceberg and Delta Lake commits
  ("Found new conflicting delete files"), even for non-overlapping time ranges.
- Keep dbt v1 installed until the v2 target has run cleanly for a full release cycle.

## Rollback

v1 and v2 read the same project and write the same relations. To roll back, run the v1 command
again with `--full-refresh` on any model whose table was created or altered by v2.
