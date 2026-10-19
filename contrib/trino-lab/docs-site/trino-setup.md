<!--
Draft for docs.getdbt.com. This is not a new page. It is a v2 section for the existing page
website/docs/docs/local/connect-data-platform/trino-setup.md (id "trino-setup", maintained by
Starburst Data, Inc.), in the same pattern as clickhouse-setup.md and duckdb-setup.md:

1. Keep the front matter. Put the <VersionBlock firstVersion="2.0"> block below directly
   after it.
2. Wrap the existing page body (from <Snippet path="warehouse-setups-cloud-callout" /> to the
   end) in a v1 block that starts with a link to this section:

   <VersionBlock lastVersion="1.99">

   <ProductCard text="dbt v2 compatible" url="/docs/local/connect-data-platform/trino-setup?version=2" />

   ... the existing page body ...

   </VersionBlock>
3. Agree on the page title (today "Connect Starburst/Trino to dbt v1") and the Lifecycle status
   with Starburst and the dbt Labs docs team. Lifecycle has no "experimental" status.

Open the docs PR after the adapter is merged and available in a dbt release, and delete this
comment in it.
-->

<VersionBlock firstVersion="2.0">

# Connect Starburst/Trino to <Constant name="fusion" /> <Lifecycle status="beta" />

The Trino adapter for <Constant name="fusion" /> connects to open-source Trino through the
Apache-2.0 [ADBC Trino driver](https://github.com/adbc-drivers/trino). It was tested with
Trino 483 and the Hive, Iceberg and Delta Lake connectors.

The adapter is **experimental**. Set `DBT_ALLOW_EXPERIMENTAL_ADAPTERS=yes` before you run dbt.

## Install the ADBC Trino driver

dbt does not download this driver. Install it yourself; dbt then loads it by its name,
`adbc_driver_trino`. dbt does not verify the driver file, so you are responsible for trusting
the file that you install.

1. Download the archive for your platform from the
   [driver releases](https://github.com/adbc-drivers/trino/releases) (tested: `go/v0.6.1`),
   for example `trino_linux_amd64_v0.6.1.tar.gz`. Archives exist for `linux_amd64`,
   `linux_arm64`, `macos_arm64` and `windows_amd64`; this page covers Linux and macOS.
2. Compare the archive's SHA-256 checksum with the digest that the release page shows for it.
3. Extract the library and put it in a folder where dbt looks for it:

| Platform | Library file |
|---|---|
| Linux | `libadbc_driver_trino.so` |
| macOS (Apple silicon) | `libadbc_driver_trino.dylib` |

dbt looks in these places, in this order:

1. Each folder in the `ADBC_DRIVER_PATH` environment variable.
2. The `dbt/` folder in the first `lib/` folder in the folder of the `dbt` executable or up to
   five folders above it (for example `lib/dbt/` next to `bin/`).
3. `/opt/homebrew/lib` (macOS on Apple silicon).
4. Your ADBC driver folder: `~/.config/adbc/drivers` on Linux,
   `~/Library/Application Support/ADBC/Drivers` on macOS.
5. The system ADBC driver folder: `/etc/adbc/drivers` on Linux,
   `/Library/Application Support/ADBC/Drivers` on macOS.
6. The operating system's library search (for example `LD_LIBRARY_PATH` or
   `DYLD_LIBRARY_PATH`).

In the folders of steps 1–5, dbt first looks for a driver manifest named
`adbc_driver_trino.toml`, then for the library file.

A manifest lets you keep the library in another folder:

<File name='adbc_driver_trino.toml'>

```toml
manifest_version = 1

[Driver]
shared = "/opt/adbc/trino/libadbc_driver_trino.so"
```

</File>

:::note dbc installs
`dbc install trino` writes a manifest named `trino.toml`, which dbt does not find. Copy it in
the same folder as `adbc_driver_trino.toml`. With a Python virtual environment active, `dbc`
installs into `$VIRTUAL_ENV/etc/adbc/drivers`; add that folder to `ADBC_DRIVER_PATH` as well.
:::

If dbt cannot load the driver, `dbt debug` fails with `Driver not found: adbc_driver_trino`.
dbt reports this as an authentication failure and asks you to check your credentials; check
the driver location instead.

## Configure `profiles.yml`

`database` is the Trino catalog; `catalog` is accepted as an alias. dbt-trino profiles load
unchanged, except for the options under [Not supported](#not-supported).

<File name='profiles.yml'>

```yaml
trino:
  target: dev
  outputs:
    dev:
      type: trino
      method: ldap                     # none | ldap | jwt | kerberos
      host: trino.example.com          # host name only: no scheme, port or path
      port: 443
      user: "{{ env_var('TRINO_USER') }}"
      password: "{{ env_var('TRINO_PASSWORD') }}"
      catalog: iceberg
      schema: analytics
      threads: 8
```

</File>

### Authentication methods

| `method` | Required fields | Notes |
|---|---|---|
| `none` (default) | `user` | Plain HTTP unless `http_scheme: https` |
| `ldap` | `user`, `password` | Password authentication; always HTTPS |
| `jwt` | `jwt_token` | `user` is optional; always HTTPS |
| `kerberos` | `user`, `keytab`, `principal` (`name@REALM`) | Optional `krb5_config` (default: `KRB5_CONFIG`, then `/etc/krb5.conf`) and `service_name`. A keytab is required |

### Optional fields

| Field | Description |
|---|---|
| `http_scheme` | `http` or `https`. Authenticated methods require `https` |
| `cert` | Path to a CA bundle, `true` (the system trust store, the default) or `false` (no certificate verification; not recommended). Only with `https` |
| `roles` | Catalog roles, for example `{hive: analyst, system: ALL}` |
| `session_properties` | Trino session properties, for example `{query_max_run_time: 2h}` |
| `client_tags` | List of client tags for resource groups |
| `query_timeout` | Client-side timeout: a positive number of seconds, such as `300` or `1.5`, or a duration such as `300s`, `30m` or `1h`. Without it, the driver stops a query after 10 hours |
| `timezone` | Session time zone. Without it, the session uses the time zone of the machine that runs dbt. Needs driver `go/v0.6.1` or later; older drivers use the server's time zone |
| `prepared_statements_enabled` | Accepted for dbt-trino compatibility; it has no visible effect |
| `retries` | Accepted for dbt-trino compatibility and ignored |

dbt sends `X-Trino-Source: dbt-trino-<version>`, the same prefix as dbt-trino, so
resource-group selectors keep matching.

### Not supported

These dbt-trino options are not supported, most of them because the ADBC Trino driver does not
support them. dbt stops with an error that names the option:

- methods `certificate`, `oauth`, `oauth_console` and `gssapi` (use `jwt` with a token instead
  of OAuth)
- Kerberos ticket caches, and the Kerberos options `hostname_override`, `force_preemptive`,
  `delegate` and `mutual_authentication`
- `impersonation_user`
- `http_headers`
- `starburst_url` (Starburst Data Discovery sync); the other `starburst_*` keys are accepted
- a URL in `host`, such as `https://trino.example.com:8443`; put the scheme in `http_scheme`
  and the port in `port`

## Trino specifics

- **Catalogs and connectors.** Features depend on the connector:
  - `merge`, `delete+insert`, `microbatch` and snapshots need Iceberg or Delta Lake.
  - Hive tables support `append`.
  - Materialized views need the Iceberg connector.
  - Changes to the fields of `ROW` columns (`sync_nested_columns`) need the Iceberg connector.
- **Delta Lake on a Hive metastore** cannot rename tables or views, so the default
  `on_table_exists: rename` fails there. Set `on_table_exists: replace` or `drop` for Delta
  models. `skip` also works: it never renames, keeps an existing table as it is, and drops a
  view before it creates the table.
- **Identifiers.** Trino stores catalog, schema and table names in lowercase, even when they are
  quoted. dbt matches relation names without regard to case.
- **Model configs** match dbt-trino: `properties`, `on_table_exists`, `view_security`,
  `views_enabled`, `sync_nested_columns`, `grace_period`, `file_format` and `table_format`.
- **Nested `ROW` columns.** With `sync_nested_columns: true`, an incremental model adds new
  `ROW` fields in the model's order. Trino matches `ROW` fields by position, so if the table's
  fields are then in another order than the model's, for example after a new field in the
  middle of a `ROW`, dbt stops and asks for `--full-refresh`. With
  `on_schema_change: sync_all_columns`, Iceberg applies a new field order in the `ROW` elements
  of an `ARRAY` or `MAP` field as a type change of that field and keeps each value in its
  field; Delta Lake and Hive refuse it, and the run fails. If the same change also removes a
  field and needs a type change that Iceberg cannot make, Iceberg removes the field and then
  fails: run the model with `--full-refresh`.

## Limitations

The Trino adapter for <Constant name="fusion" /> is experimental. Some features of the
`dbt-trino` adapter for <Constant name="core" /> are not supported yet. If you find an issue,
[open it in dbt-labs/dbt](https://github.com/dbt-labs/dbt/issues/new) and add the
`adapter:trino` label.

### What works today

- Materializations: table, view, ephemeral, incremental (`append`, `merge`, `delete+insert`,
  `microbatch`, all `on_schema_change` modes, nested `ROW` columns), materialized view
  (Iceberg), snapshot and seed
- Data tests, unit tests, contracts (`not_null`), grants, `persist_docs`, hooks
- `dbt docs generate`, source freshness, `dbt clone`

### Not yet supported

- The options listed under [Not supported](#not-supported)
- Per-model `client_tags` and `http_headers` routing, and `catalogs.yml` catalog integrations
  (`catalog_name`)
- Python models
- Ctrl-C stops dbt, but a query that is already running continues on Trino until Trino abandons
  it (`query.client.timeout`, 5 minutes by default)
- SQL comprehension features (static analysis and the rest of dbt's SQL intelligence)

</VersionBlock>
