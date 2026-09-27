# Upstream contribution plan (not submitted)

Nothing in this fork has been proposed to `dbt-labs/dbt`. This file prepares that step for
when the owner decides to open it. The `upstream` remote in the local clone has its push URL
disabled on purpose.

## Context to check first

- Tracking issue: [dbt-labs/dbt#13131](https://github.com/dbt-labs/dbt/issues/13131) (open,
  unassigned; in June 2026 a maintainer invited a community implementation).
- Related open work: the Athena series (umbrella [#16252](https://github.com/dbt-labs/dbt/issues/16252),
  Parts 0–9). Athena runs Trino SQL and fills the same parse-path `todo!()` arms
  (`relation/factory.rs`, `column_builder.rs`, `seed_io.rs`, `schema_name` listing column).
  Whichever series merges second rebases; nothing here depends on Athena.
- Inline UDF PR [#15345](https://github.com/dbt-labs/dbt/pull/15345) (Trino functions);
  independent of this work.
- Refresh all three immediately before opening anything.

## Suggested PR series

Each PR builds and passes its own tests. Only `crates/` and `.changes/` go upstream; the
`contrib/trino-lab/` directory and `.github/workflows/trino-fork-build.yml` stay in the fork.

| # | Scope | Main files |
|---|---|---|
| 0 | Issue comment on #13131 announcing the series, linking the fork's test evidence | — |
| 1 | Profile schema + auth: `TrinoDbConfig` v1 fields, target context, `dbt-auth` Trino module, `accessToken` redaction in `Builder` Debug | `dbt-schemas/profiles.rs`, `dbt-auth/src/trino`, `dbt-adbc/database/builder.rs` |
| 2 | Parse-path `todo!()` arms: relations, columns, seed column-name inference, microbatch `TIMESTAMP` literals, type parsing/rendering (`ROW`, `ARRAY`, `MAP`, `VARBINARY`, `DECIMAL`) | `relation/factory.rs`, `column/*`, `dbt-adapter-sql/types`, `relations/base.rs`, `seed_io.rs` |
| 3 | Metadata: `GenericMetadataAdapter` (Exasol rename), shared `information_schema` listing with materialized-view detection, `get_relation` | `metadata/generic.rs`, `metadata/get_relation.rs`, `metadata/duckdb/mod.rs` |
| 4 | Vendored dbt-trino v1.10.5 macro package with v2 changes + loader tests | `dbt_macro_assets/dbt-trino`, `dbt-loader/tests/macros/trino.rs` |
| 5 | Adapter behavior: constraints, grants, incremental strategies (+ Hive `insert_overwrite`), seed `convert_type`, literal formatting, `diff_nested_column_types`, Trino config keys | `adapter_impl.rs`, `adapter/mod.rs`, `formatter.rs`, `configs/*` |
| 6 | `dbt init` wizard | `dbt-profile-schemas/trino_config.rs`, `dbt-init` |

Each PR needs a `changie` entry (the fork has one combined entry in `.changes/unreleased/`) and
a "manually verified against a real project" note, which the fork's functional suite covers.

## Decisions for maintainers

1. **Driver distribution.** The fork loads `adbc_driver_trino` from the system or a `lib/`
   directory through `Backend::Generic`, the same mechanism Athena and Exasol use. Upstream may
   want the adbc-drivers/trino release in `drivers.toml` and its CDN instead. A June 2026
   comment on #13131 mentioned a Starburst driver effort, so ask which driver they intend to
   support.
2. **`Backend::Generic` vs a dedicated `Backend::Trino`.** The fork avoids new `dbt-adbc`
   variants, following `.agents/adapters.md`.
3. **Experimental gate.** Trino stays behind `DBT_ALLOW_EXPERIMENTAL_ADAPTERS`.
4. **`accessToken` redaction** touches `dbt-adbc` (debug output only). It's needed because
   trino-go-client accepts JWTs only as a URI parameter.
5. **Config keys.** `properties`, `view_security`, `on_table_exists`, `sync_nested_columns`,
   `views_enabled` and `grace_period` are added to `WarehouseSpecificNodeConfig` with dbt-trino's
   names, as Exasol did.
6. **Microbatch concurrency.** dbt-trino v1 declares `MicrobatchConcurrency` as Full, but concurrent
   batches conflict in Iceberg/Delta commits on Trino 483, so the fork leaves Trino out of
   `MICROBATCH_SUPPORTED_ADAPTERS` (batches run sequentially, with dbt's warning).

## Driver issues

Report these to [adbc-drivers/trino](https://github.com/adbc-drivers/trino) (after the owner
decides), not the dbt repository.

- **Cancellation.** `AdbcStatementCancel` (generated `TrinoStatementCancel` →
  `cancellableContext.cancelContext()`) only cancels a call that is still executing. Trino
  queries are polled while the result stream is read after `ExecuteQuery` returns, and
  driverbase's `FinishContext` stops tracking that context, so cancel is a no-op. dbt v2 calls
  cancel on every tracked statement on Ctrl-C. Repro: `functional/test_more.py::
  TestSessionLimits::test_ctrl_c_stops_server_query` (marked `expectedFailure`).
- **Not exposed by the driver**, needed for full dbt-trino profile parity: client-certificate
  (mTLS) auth, custom HTTP headers, impersonation (`X-Trino-User` different from the
  authenticated principal), Kerberos ticket cache / GSSAPI, and interactive OAuth2.

## Draft issue comment for #13131 (do not post without the owner's approval)

> I've been working on a Trino adapter for dbt v2 OSS in a fork:
> https://github.com/abhishekguha996-ux/dbt-trino-v2 (branch `trino-v2-adapter`). It uses the
> adbc-drivers/trino driver through `Backend::Generic`, vendors the dbt-trino v1.10.5 macro
> package, and keeps dbt-trino v1 profile fields. It's covered by crate tests plus a functional
> suite against Trino 483 with Hive, Iceberg and Delta Lake on S3-compatible storage (auth, all
> materializations, incremental strategies, snapshots, MVs, grants, docs, unit tests). Before
> opening PRs I'd like to align on driver distribution and on splitting the work into a series
> like the Athena one (#16252). Would a maintainer be open to reviewing that?
