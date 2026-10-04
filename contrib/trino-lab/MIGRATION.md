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
python3 compare_schemas.py \
  --host trino.internal.example.com --user "$TRINO_USER" --password-env TRINO_PASSWORD \
  --catalog hive --left analytics --right analytics_v2_check
```

`compare_schemas.py` compares relation types, column types, row counts and an
order-independent checksum of every relation present in both schemas. It only reads data. It
is not in the release archive; get it from
[contrib/trino-lab/scripts](https://github.com/abhishekguha996-ux/dbt-trino-v2/blob/trino-v2-adapter/contrib/trino-lab/scripts/compare_schemas.py).
Its limits:

- It logs in with a user name and password only (HTTP Basic). It has no JWT, Kerberos or
  role options.
- Columns that hold the build time differ on every build, for example the snapshot columns
  `dbt_valid_from`, `dbt_valid_to` and `dbt_updated_at`.

### Profile differences

| dbt-trino v1 profile option | dbt v2 |
|---|---|
| `method: none / ldap / jwt` | Supported |
| `method: kerberos` | Supported with `keytab` + `principal` (`user@REALM`); `krb5_config`, then `KRB5_CONFIG`, then `/etc/krb5.conf` for the config file. No ticket cache: `keytab` is required. `hostname_override`, `force_preemptive`, `delegate` and `mutual_authentication` are not supported by the driver: dbt stops with an error unless they are unset, `false` or `disabled` |
| `method: certificate`, `oauth`, `oauth_console`, `gssapi` | **Not supported** by the ADBC Trino driver; dbt stops with an error. Use `jwt` with a token instead of OAuth |
| `http_headers`, `impersonation_user` | **Not supported** by the driver; dbt stops with an error that names the option (an empty value counts as unset, as in v1) |
| `host` | **Host name only**, for example `trino.example.com`. A scheme, a port or a path (`https://trino.example.com`, `trino.example.com:8443`, `trino.example.com/x`) stops dbt with an error. Put the port in `port` and the scheme in `http_scheme` |
| `cert` | **Default changed:** v2 verifies TLS certificates when `cert` is unset (v1 skipped verification unless `require_certificate_validation` was on). Set `cert: /path/to/ca.pem` for internal CAs, or `cert: false` to keep v1's behavior |
| `cert` with `http_scheme: http` | **Now an error** ("Trino 'cert' requires http_scheme: https"), also for `cert: true` on a `method: none` profile. Remove `cert` from HTTP profiles |
| `starburst_url`, `starburst_client_id`, `starburst_secret_key`, `starburst_metadata_failure_strategy`, `starburst_max_column_batch_size` (dbt-trino 1.10.3+) | Accepted. The Starburst Data Discovery sync is not supported: if `starburst_url` is set, dbt stops with an error that asks you to remove the `starburst_*` keys |
| `role` | Not a dbt-trino field. dbt stops with an error that points to `roles: {system: <role>}` or `roles: {<catalog>: <role>}` |
| `roles`, `session_properties`, `client_tags`, `catalog` alias | Supported |
| `timezone` | Accepted, but the ADBC Trino driver go/v0.5.3 does not send it: the session uses the Trino server's time zone. trino-go-client sends it from v0.336.0 on, which the driver's `main` branch already uses |
| `prepared_statements_enabled` | Accepted; no visible effect, because v2 always renders bindings (for example seed values) as SQL literals |
| `retries` | Accepted and ignored. dbt v2 does not show a warning for it yet. The driver itself retries HTTP 502, 503 and 504 responses with a growing delay, but it does not retry connection errors |
| New: `query_timeout` | Client-side timeout: a number of seconds (`300`) or a duration (`300s`, `30m`, `1h30m`). Any other value stops dbt with an error |
| `X-Trino-Source` | Still `dbt-trino-<version>`, so resource-group selectors keep matching |

Per-model `client_tags` / `http_headers` query routing (dbt-trino 1.10) and `catalogs.yml`
catalog integrations are not available yet. A model with `catalog_name` stops with an error
that says so; without `catalog_name`, `storage_uri` sets the table `location`, as in v1.

Two YAML details apply to `profiles.yml` and `dbt_project.yml`:

- **YAML 1.1 booleans.** As in dbt v1 (PyYAML), unquoted `yes`, `no`, `on` and `off` (also
  `Yes`, `YES` and so on) are booleans, like `true` and `false`. Quote such a value when it must
  stay text, for example a schema named `on` or a password `yes`.
- **All-digit passwords from `env_var()`.** A password that has only digits and comes from
  `env_var()` becomes a number. dbt v2 then fails with "invalid type: integer", and the error
  message shows the value. This affects every adapter in dbt v2. Use a password with at least
  one other character.

### Project and behavior differences

| Area | dbt v2 behavior |
|---|---|
| Unknown config keys | Errors (`dbt1060`). All dbt-trino keys are recognised: `properties`, `on_table_exists`, `view_security`, `views_enabled`, `sync_nested_columns`, `grace_period`, `file_format`, `table_format` |
| `dbt docs generate` | Produces a static site in `target/`; use `dbt compile --write-catalog` for `catalog.json` |
| Unit tests | Same YAML; a failing unit test is recorded as `error` in `run_results.json` |
| Static analysis / column lineage | Not part of the dbt v2 OSS build for any adapter; disabled for Trino |
| Python models | Not supported (as in dbt-trino v1) |
| Seeds | Same types as v1 (`INTEGER`, `DOUBLE`, `VARCHAR`, `DATE`, `TIMESTAMP`, `BOOLEAN`); whole numbers beyond 32 bits become `BIGINT` instead of failing |
| `incremental_strategy: insert_overwrite` | Not available, as in dbt-trino v1: dbt stops with "The incremental strategy 'insert_overwrite' is not valid for this adapter". Use `append` on Hive, or `merge` / `delete+insert` on Iceberg and Delta Lake |
| `sync_nested_columns` | New nested `ROW` fields keep the order of the model's columns, and a missing nested `ROW` is added as one field. A new field in the middle of a `ROW` stops dbt with an error that asks for `--full-refresh`: Trino matches `ROW` fields by position, so v1 put such values into the wrong fields without an error |
| Grants | dbt never revokes the privileges of the user that runs it. v1 could revoke the schema owner's own privileges, and the next run then failed with Access Denied |
| Materialized views | A full refresh uses `CREATE OR REPLACE MATERIALIZED VIEW`, so the old view stays if the new definition fails (v1 drops it first). `persist_docs` works on materialized views (v1 fails, because Trino has no `COMMENT ON MATERIALIZED VIEW`) |
| `sql_header` | Now applied to tables and views (statements are split on `;`) |

### Connector limits (same as dbt-trino v1)

These come from Trino itself, not the adapter:

- **Delta Lake on a Hive metastore can't rename managed tables or views.** Use
  `on_table_exists: replace` for Delta models (Trino supports `CREATE OR REPLACE TABLE` there).
- **Delta Lake drops or renames columns only with column mapping**
  (`properties: {column_mapping_mode: "'name'"}`), which `on_schema_change: sync_all_columns`
  needs.
- **Plain Hive tables don't support `MERGE` or row-level `DELETE`.** Use `append`; `merge`,
  `delete+insert`, `microbatch` and snapshots need Iceberg or Delta Lake.
- **Materialized views** exist only on the Iceberg connector in OSS Trino.
- **Grants** need a connector with access-control support (Hive `sql-standard` security).

### Operational notes

- **Interrupting a run:** with ADBC Trino driver go/v0.5.3, Ctrl-C stops dbt, but a query
  already running keeps running until Trino abandons it after `query.client.timeout` (5 minutes
  by default). Set `session_properties: {query_max_run_time: ...}` as a guardrail. This is a
  driver issue; see [DRIVER-ISSUES.md](DRIVER-ISSUES.md#cancel-does-not-stop-a-running-query).
- **Microbatch** batches run sequentially. `concurrent_batches: true` logs a warning and is
  ignored: concurrent `DELETE` + `INSERT` batches conflict in Iceberg and Delta Lake commits
  ("Found new conflicting delete files"), even for non-overlapping time ranges.
- Keep dbt v1 installed until the v2 target has run cleanly for a full release cycle.

## Rollback

v1 and v2 read the same project and write the same relations. To roll back, run the v1 command
again with `--full-refresh` on any model whose table was created or altered by v2.
