---
title: "Connect Trino to dbt v2"
sidebar_label: "Trino"
description: "Read this guide to learn how to connect dbt v2 to Trino with the ADBC Trino driver."
meta:
  maintained_by: Community
  github_repo: 'dbt-labs/dbt'
  platform_name: 'Trino'
  min_supported_version: 'Trino 4xx (tested with 483)'
  config_page: '/reference/resource-configs/trino-configs'
---

<!-- Draft for docs.getdbt.com. Submit after the adapter is merged into dbt-labs/dbt. -->

The Trino adapter is **experimental**. Set `DBT_ALLOW_EXPERIMENTAL_ADAPTERS=yes` before you run dbt.

## Install the ADBC Trino driver

dbt v2 connects to Trino through the Apache-2.0 [ADBC Trino driver](https://github.com/adbc-drivers/trino).
dbt does not download it. Install it yourself, then dbt loads it by name.

1. Download the archive for your platform from the
   [driver releases](https://github.com/adbc-drivers/trino/releases) (tested: `go/v0.5.3`),
   for example `trino_linux_amd64_v0.5.3.tar.gz`.
2. Extract the library and put it where dbt looks for it:

| Platform | Library file | Where dbt finds it |
|---|---|---|
| Linux | `libadbc_driver_trino.so` | a directory on `LD_LIBRARY_PATH`, `/usr/local/lib`, or a `lib/` directory next to (or up to five levels above) the `dbt` executable |
| macOS | `libadbc_driver_trino.dylib` | `DYLD_LIBRARY_PATH`, `/opt/homebrew/lib`, or a `lib/` directory next to the `dbt` executable |

If dbt cannot find the library, `dbt debug` fails with an error that names `adbc_driver_trino`.

## Configure `profiles.yml`

`database` is the Trino catalog; `catalog` is accepted as an alias. dbt-trino v1 profiles load
unchanged except for the options listed under [Not supported](#not-supported).

<File name='profiles.yml'>

```yaml
trino:
  target: dev
  outputs:
    dev:
      type: trino
      method: ldap                     # none | ldap | jwt | kerberos
      host: trino.example.com
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
| `kerberos` | `user`, `keytab`, `principal` (`name@REALM`) | Optional `krb5_config` (default `KRB5_CONFIG` or `/etc/krb5.conf`) and `service_name` |

### Optional fields

| Field | Description |
|---|---|
| `http_scheme` | `http` or `https`. Authenticated methods require `https` |
| `cert` | Path to a CA bundle, `true` (system trust, the default) or `false` (no certificate verification; logs a warning unless `suppress_cert_warning: true`) |
| `roles` | Catalog roles, for example `{hive: analyst, system: ALL}` |
| `session_properties` | Trino session properties, for example `{query_max_run_time: 2h}` |
| `client_tags` | List of client tags for resource groups |
| `timezone` | Session time zone |
| `query_timeout` | Client-side timeout, for example `30m` |
| `prepared_statements_enabled` | Driver prepared-statement mode (default `true`) |

dbt sends `X-Trino-Source: dbt-trino-<version>`, the same prefix as dbt-trino v1.

### Not supported

The ADBC Trino driver does not support these dbt-trino v1 options. dbt stops with an error that
names the option:
- methods `certificate`, `oauth`, `oauth_console` and `gssapi` (use `jwt` with a token instead of OAuth)
- `impersonation_user`
- `http_headers`
- per-model `client_tags` / `http_headers` routing

`retries` is accepted and ignored, with a warning.

## Trino specifics

- **Catalogs and connectors.** Features depend on the connector:
  - `merge`, `delete+insert`, `microbatch` and snapshots need Iceberg or Delta Lake.
  - Hive tables support `append` and `insert_overwrite` (partition overwrite).
  - Materialized views need the Iceberg connector.
- **Delta Lake on a Hive metastore** cannot rename tables. Set `on_table_exists: replace` for Delta models.
- **Identifiers** are lowercase in Trino. Quoted identifiers preserve case in SQL, but most connectors store them in lowercase.
- **Model configs** match dbt-trino v1: `properties`, `on_table_exists`, `view_security`,
  `views_enabled`, `sync_nested_columns`, `grace_period`, `file_format` and `table_format`.
