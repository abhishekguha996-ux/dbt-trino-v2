# Test results — 5 October 2026, with the gates on 112adf8 of 19 October

Experimental adapter; this is a test record, not a production-readiness claim. The current
record is the run of 5 October on `trino-pr/integration` 8809833: the series with the
follow-ups F1 and F2. F3 is left out, and 8809833 reverts it (see
[UPSTREAM.md](UPSTREAM.md#follow-ups)). The [earlier records](#earlier-records) below are the
run on e7a1675, with F3, and the run on 892256e, without the follow-ups. The 27 September
record (72 tests, before the rebase onto dbt-labs `main` 7bbd974 and the review fixes) is in the
git history of this file.

On 19 October the PR branches and `trino-pr/integration` were rebased onto dbt-labs `main`
112adf8. Only the Rust gates ran on that base (see [Gates on 112adf8](#gates-on-112adf8)). The
live records below are all on 7bbd974. Their commits (892256e, e7a1675, 8809833) are on the
local branch `trino-pr/integration-7bbd974`, the tip of `trino-pr/integration` before the
rebase.

## What was tested

| Item | Value |
|---|---|
| Base | dbt-labs/dbt `main` 7bbd974 (`7bbd974389dbd08da3ece92396ecdd0c8f99719c`, 2 October 2026) |
| Series | `trino-pr/series` 6f3a4a3: the nine parts of [UPSTREAM.md](UPSTREAM.md#the-pr-series) |
| Follow-ups | F1 a5767d1 (for S2) and F2 25a4eca (for Part 1), from `trino-pr/followups`. F3 135bdd0 (for Part 4) is left out |
| Tested commit | `trino-pr/integration` 8809833: the series, the fork-only `contrib/` and `.github/` commits, F1 and F2 as 99233a2 and 56e7e77, and F3 as e7a1675 with its revert 8809833. Its `crates/` and `.changes/` are the same as in `trino-pr/followups~1`, the series with F1 and F2. Later commits on `trino-pr/integration` change only documentation in `contrib/trino-lab/` |
| dbt binary | `cargo build -p dbt-sa-cli --bin dbt` (debug profile) at 8809833, native macOS ARM64, Rust 1.96.1; sha256 `45510155ae9c05023d3dee4efd7d313e39fd87c8e418b4b579c2b7006db7c267`. `dbt --version` prints `dbt-oss 2.0.5`, and every `dbt.log` shows the banner `dbt-oss 2.0.5 (8809833 2026-10-05 15:33:04)`. A debug build reads the macro files from its source tree at run time; that tree was clean at 8809833 during the run, and a macro probe confirmed that it has no F3 macro |
| ADBC driver | adbc-drivers/trino `go/v0.5.3` (`libadbc_driver_trino.dylib` from the macos_arm64 archive; sha256 `24767ddba8a6e3e49696a3fc16f052eb69cb9b8ac6ca6333a304415ffb6e2272`) |
| Trino | 483 (`trinodb/trino:483`, single node) |
| Catalogs | `memory`; `hive` (`sql-standard` security), `iceberg` and `delta` on one Hive metastore 3.1.3 (Postgres 18) with RustFS (S3 API); `tpch` |
| Auth | HTTP without authentication (port 8080); HTTPS (port 8443) with a password file and JWT (RS256), signed by the lab CA |
| Harness | Python 3.13.7; `SCHEMA_PREFIX=zz_f5_`, a private `HOME` and `TMPDIR`; 5 October 2026, 15:36–15:46 EDT |

## Gates on 112adf8

On 19 October 2026, with dbt Labs' CI gates (`.github/workflows/ci.yml`) on dbt-labs `main`
112adf8 (`112adf89c`, 18 October 2026), native macOS ARM64. The branches are listed in
[UPSTREAM.md](UPSTREAM.md#pr-branches-on-112adf8).

| Branch | Tip | `cargo fmt --all --check` | `cargo clippy --workspace --all-targets -- -D warnings` | `cargo nextest run --workspace`: run / passed / failed |
|---|---|---|---|---|
| `pr/p0` | 584285f | pass | pass | 7,208 / 7,182 / 26 |
| `pr/s1` | a0851b3 | pass | pass | 7,209 / 7,183 / 26 |
| `pr/s2` | 6fc4960 | pass | pass | 7,214 / 7,188 / 26 |
| `pr/p1` | 202707d | pass | pass | 7,234 / 7,208 / 26 |
| `pr/p2` | 97f9da5 | pass | pass | 7,249 / 7,223 / 26 |
| `pr/p3a` | 577d8e4 | pass | pass | 7,207 / 7,181 / 26 |
| `pr/p3b` | 73b7c86 | pass | pass | 7,244 / 7,218 / 26 |
| `pr/p4` | afb2785 | pass | pass | 7,287 / 7,261 / 26 |
| `pr/p5` | 06b7f01 | pass | pass | 7,241 / 7,215 / 26 |
| `pr/series` | 6480cf3 | pass | pass | 7,305 / 7,279 / 26 |
| `trino-pr/integration` | 8a1dde4 (its `crates/` are those of the tip) | pass | pass | 7,314 / 7,288 / 26 |
| `main` (no Trino code) | 112adf8 | pass | pass | 7,207 / 7,181 / 26 |

The 26 failures are the same tests on every branch and on `main`: the ClickHouse record/replay
tests `adapter::clickhouse::adapters_clickhouse_*` of `dbt-sa-adapter-tests` (upstream b6e966a,
14 October). Each fails with `[InvalidConfig (dbt1005)]: I/O error: No such file or directory`.
The cause is this host: `HydrateProfilesTask` (`crates/dbt-test-utils/src/task/profiles.rs`)
reads the `test` profile in `~/.dbt/profiles.yml` when the test project has no
`profiles.yml`, and this Mac has no `~/.dbt/profiles.yml`. dbt Labs' CI supplies that file.

## Rust checks (7bbd974)

On `trino-pr/series` 6f3a4a3, with dbt Labs' CI gates (`.github/workflows/ci.yml`):

| Check | Result |
|---|---|
| `cargo fmt --all --check` | clean |
| `cargo clippy --workspace --all-targets -- -D warnings` | clean |
| `RUST_MIN_STACK=8388608 cargo nextest run --workspace --no-fail-fast` | **7,019 passed**, 0 failed, 49 skipped |

Each part was also checked twice:

- **In the stack**, at its own commit: `cargo fmt --all --check`, `cargo check --all-targets` on
  the crates it changes, `cargo clippy -D warnings` on the twelve adapter crates, and
  `cargo nextest` on the crates it changes. 9 of 9 parts pass.
- **Alone**, on 7bbd974 with only its "Needs first" parts cherry-picked before it:
  `cargo fmt --all --check`, `cargo check --all-targets` and `cargo nextest` on its crates.
  9 of 9 parts apply cleanly and pass:

| Part | Commit | Alone on 7bbd974 with | `cargo nextest` alone |
|---|---|---|---|
| 0 | 1901220 | — | dbt-adbc: 50 passed, 15 skipped |
| S1 | 5ee10b4 | — | dbt-adapter, dbt-agate: 1,633 passed, 2 skipped |
| S2 | 5733d42 | — | dbt-tasks-sa: 190 passed |
| 1 | ab2948f | — | dbt-adapter, dbt-auth, dbt-schemas: 2,549 passed, 6 skipped |
| 2 | 8943170 | Part 1 | dbt-adapter, dbt-adapter-sql, dbt-df-providers, dbt-schemas, dbt-tasks-sa: 2,449 passed, 3 skipped |
| 3a | 7de6091 | — | dbt-adapter: 1,516 passed, 2 skipped |
| 3b | 10a13da | Parts 1 and 3a | dbt-adapter: 1,526 passed, 2 skipped |
| 4 | 8f0bf3b | Parts 1 and 2 | dbt-adapter, dbt-adapter-sql, dbt-loader, dbt-schemas: 2,540 passed, 3 skipped |
| 5 | 6f3a4a3 | Part 1 | dbt-init, dbt-profile-schemas: 14 passed |

The follow-ups F1 and F2:

- **At the tested commit** 8809833, whose `crates/` are those of `trino-pr/followups~1` (5
  October): `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` and
  `cargo nextest` on the four crates that the follow-ups and the revert of F3 change
  (dbt-tasks-sa, dbt-schemas, dbt-auth and dbt-loader) pass: 1,508 passed, 4 skipped. The
  workspace-wide gates have not run on this code.
- **Alone**, on 7bbd974 with only the parts in its "Needs first" column cherry-picked before
  it (4 October): `cargo fmt --all --check`, and `cargo check --all-targets`,
  `cargo clippy --all-targets -- -D warnings` and `cargo nextest` on its crates. Both
  follow-ups apply cleanly and pass:

| Follow-up | Commit | Alone on 7bbd974 with | `cargo nextest` alone |
|---|---|---|---|
| F1 | a5767d1 | S2 | dbt-tasks-sa: 194 passed |
| F2 | 25a4eca | Part 1 | dbt-schemas, dbt-auth: 1,033 passed, 4 skipped |

## Functional suite (`functional/`, live stack)

Each module ran alone: `python3 -m unittest -v <module>`, with `DBT_BIN` set to the binary
above. Most tests loop over the catalogs as subtests. The suite is the same as in the earlier
records.

**98 tests: 97 passed and 1 expected failure, with 0 failures, 0 errors and 0 skips.**

| Module | Tests | Result | Time | Covers |
|---|---|---|---|---|
| test_auth | 14 | 14 passed | 8.5 s | LDAP-style password with a CA bundle, a password with URL-special characters, wrong password (rejected and redacted), JWT (the token is not in the output or `dbt.log`), `cert: false`, untrusted certificate, password over HTTP refused, `dbt-trino-*` source header (client tags are set, not checked); profile checks: host name only, `query_timeout` values, `role`, `starburst_*` keys |
| test_basic | 18 | 18 passed | 63.6 s | seeds, tables, views, ephemeral models and reruns; mixed-case names; view ↔ table switches; `on_table_exists` (rename, drop, replace, skip; the Delta rename limit; a failed switch from a view keeps it in `rename` mode; `skip` switches a view to a table on Delta); `view_security`; `properties`, `file_format` conflicts, `storage_uri`; `sql_header` |
| test_incremental | 23 | 23 passed | 95.0 s | append (all catalogs, default strategy, full refresh, `views_enabled: false`); merge (single and composite keys, update and exclude columns, predicates); delete+insert; `insert_overwrite` rejected; microbatch (daily, seven daily batches rerun); every `on_schema_change` mode, with type changes; nested ROW sync (field order, nested ROWs, a field in the middle of a ROW asks for `--full-refresh`) |
| test_features | 32 | 32 passed | 84.7 s | snapshots (timestamp, check, hard deletes); materialized views (create, refresh, full refresh, a failed full refresh keeps the view, mixed-case names, replace a table); grants and revokes, also in a mixed-case schema; `persist_docs`; contracts; seeds (types, escaping, JSON, overrides, 2,500 rows, v1 integer inference); unit tests and fixture types; uuid in `run_query`, contracts and unit tests; hooks and session properties; cross-database macros; debug, parse, compile, list, show, docs and `catalog.json`, `--empty`, retry, source freshness, clone, `--defer` |
| test_more | 9 | 8 passed, 1 expected failure | 52.1 s | query comments, custom schemas, `store_failures` (audit schema), snapshot `new_record`, enforced `query_max_run_time`, `dbt_utils`, `catalog_name` error, Python model rejection, Ctrl-C (**expected failure**) |
| test_projects | 2 | 2 passed | 33.4 s | retail (36 nodes) on all four catalogs against Python-generated expectations; TPC-H Q3/Q5-style marts on all four catalogs against a Python/Decimal oracle |

Fixture unit tests (`tests/`, `python3 -m unittest discover -s tests`): 2 passed.

**The expected failure** is `test_more.TestSessionLimits.test_ctrl_c_stops_server_query`. After
SIGINT, `system.runtime.queries` showed the query `RUNNING` until the test's cleanup killed it
(`ADMINISTRATIVELY_KILLED`, 36.6 s after the query started). This is the driver limit
[Cancel does not stop a running query](DRIVER-ISSUES.md#cancel-does-not-stop-a-running-query).
No query was left running.

## jaffle-shop-classic acceptance build

`acceptance/run_jaffle_shop.sh` with `SCHEMA_PREFIX=zz_f5_`, unchanged: jaffle-shop-classic
`fd7bfac` with `acceptance/jaffle-shop-classic-v2.patch` (dbt-autofix's YAML changes, an
incremental model with a uniqueness test, and a snapshot). Each catalog is built twice. Delta
models use `on_table_exists: replace`, and Hive excludes the snapshot (plain Hive tables have
no `MERGE`).

| Catalog | Run | Processed | Result | `orders_incremental` |
|---|---|---|---|---|
| iceberg | 1 | 6 models, 22 tests, 1 snapshot, 3 seeds | 32 of 32 success | `create table` |
| iceberg | 2 | 6 models, 22 tests, 1 snapshot, 3 seeds | 32 of 32 success | `merge into` |
| delta | 1 | 6 models, 22 tests, 1 snapshot, 3 seeds | 32 of 32 success | `create table` |
| delta | 2 | 6 models, 22 tests, 1 snapshot, 3 seeds | 32 of 32 success | `merge into` |
| hive | 1 | 6 models, 22 tests, 3 seeds | 31 of 31 success | `create table` |
| hive | 2 | 6 models, 22 tests, 3 seeds | 31 of 31 success | `insert into` (append) |

Data checks after run 2, on each catalog: the seeds have 100, 99 and 113 rows;
`orders_incremental` has 99 rows with 99 distinct `order_id` values and equals `orders`
exactly; on Iceberg and Delta, `customers_snapshot` has 100 rows, all current. Every `dbt.log`
shows the 8809833 banner.

## Nested ROW order checks

These checks show what Part 4 does without F3: the cases that F3 changed, and the order check
after the `ALTER` statements, which Part 4 keeps. Each check ran in its own small project
(schema prefix `zz_f5_rg_`). Run 1 builds an incremental model with `sync_nested_columns: true`
and a ROW column `payload`, and run 2 changes the model. A macro probe confirmed that the binary
reads the macros of 8809833: F3's `trino__raise_row_order_error` is not defined.

| Change in run 2, inside `payload` | `on_schema_change` | Iceberg | Delta Lake and Hive |
|---|---|---|---|
| `items ARRAY(ROW(y, x))` becomes `ARRAY(ROW(x, y))` | `sync_all_columns` | `ALTER COLUMN … SET DATA TYPE` runs, and the run succeeds. Each value stays in its field: row 1 becomes `{"x":2,"y":1}` | the `SET DATA TYPE` fails with `NOT_SUPPORTED` ("This connector does not support setting field types"); the table does not change |
| `m MAP(varchar, ROW(y, x))` becomes `MAP(varchar, ROW(x, y))` | `sync_all_columns` | the same as for `ARRAY`: the run succeeds with each value in its field | the same as for `ARRAY` |
| the `ARRAY` reorder, and the field `gone` removed | `sync_all_columns` | the `DROP COLUMN` and the `SET DATA TYPE` run, and the run succeeds with each value in its field | the `DROP COLUMN` fails with `NOT_SUPPORTED` ("does not support dropping fields"); the table does not change |
| the `ARRAY` reorder, `x` changed from `integer` to `varchar`, and `gone` removed | `sync_all_columns` | the `DROP COLUMN` runs, then the `SET DATA TYPE` fails with `ICEBERG_COMMIT_ERROR` ("Cannot change column type: payload.items.element.x: int -> string"). The table is partly changed: `gone` is dropped | not run |
| the `ARRAY` reorder, and `gone` removed | `append_new_columns` | stops with the `--full-refresh` error; no `ALTER` runs, and the table does not change | the same as on Iceberg |
| `ROW(a, b)` becomes `ROW(a, m, b)`: a field added in the middle | `sync_all_columns`, and also `append_new_columns` | `ADD COLUMN` puts `m` at the end of the ROW. Then the order check stops the run with the `--full-refresh` error, before any `INSERT` or `MERGE`, and `a1` and `b1` stay in their fields | the nested `ADD COLUMN` fails with `NOT_SUPPORTED` ("does not support adding fields"), before the order check; the table does not change |

After each failed run 2, a `--full-refresh` rebuilt the table in the model's order on Iceberg
and Hive. On Delta, it fails in the default `rename` mode (the Delta rename limit under
[Known limits](#known-limits)), and it works with `on_table_exists: replace`.

With F3 (the [e7a1675 record](#e7a1675-5-october-with-f3)), each of the first four changes
stopped before any `ALTER` with the `--full-refresh` error. On Delta Lake and Hive, that changed
only the error text. On Iceberg, it also stopped the three changes that succeed above.

## Earlier records

### e7a1675 (5 October, with F3)

The run of 5 October, 14:35–14:51 EDT, tested `trino-pr/integration` e7a1675: the series, the
fork-only commits and the three follow-ups F1, F2 and F3. The binary banner was
`dbt-oss 2.0.5 (e7a1675 2026-10-04 23:06:36)` and the schema prefix `zz_r3_`. The functional
suite (98 tests: 97 passed and 1 expected failure, the Ctrl-C test) and the six jaffle-shop
builds passed as in the current record. At the tip of `trino-pr/followups`, 135bdd0, fmt,
check, clippy and nextest passed on the four crates that the follow-ups change (1,509 passed, 4
skipped), and F3 alone on 7bbd974, after Parts 1, 2 and 4, passed (dbt-loader: 279 passed).
Trino stopped once for lack of memory (`OOMKilled`, 4 GiB container limit) after the F2 checks.
It was started again with `docker start`, and the F3 checks ran again in full.

#### Red/green checks of the follow-ups

Each follow-up ran in its own small project (schema prefix `zz_r3_rg_`) on the e7a1675 binary
and on the 892256e binary. 8809833 has the same F1 and F2 code, so their checks also apply to
the current record. For F3, the 892256e baseline was a copy of that binary that reads the
892256e macro files.

| Item | Check | 892256e | e7a1675 |
|---|---|---|---|
| F1 | unit tests on a `decimal(20, 2)` column (memory), actual value against expected value: -0.50 against 0.50, 0.50 against -0.50, and -0.05 against 0.05 | all three pass | all three fail, with the sign in the diff, for example `0.50 -> -0.50` |
| F1 | 0.05 against 0.50 on the same column | fails; the diff shows `0.50 -> 0.5` | fails; the diff shows `0.50 -> 0.05` |
| F1 | equal values, and equal NULLs, in 25 columns from `tinyint` to `map` and `row` (memory) | pass | pass |
| F2 | profiles with an unquoted `query_timeout: 1.5` and `2.0` | `dbt debug` fails: `data did not match any variant of untagged enum StringOrInteger` | `dbt debug` passes, and `dbt run` builds the model |
| F2 | a query that runs about 6 s (`tpch.sf10`), with `query_timeout` 1.5, 3.5 and 300 | the quoted `"1.5"` cancels it after 1.52 s; 300 lets it finish | 1.5 and 3.5 cancel it on the server after 1.51 s and 3.58 s (`USER_CANCELED`); 300 lets it finish (6.3 s) |
| F2 | `query_timeout` 0.0, -1.5 and `true` | the parse error above | the Trino messages: "must be greater than zero; remove it to use the driver default of 10h", and "must be a number of seconds or a duration such as 300s, 30m or 1h; got '-1.5'" (or `'true'`) |
| F3 | `sync_all_columns`: the first four changes of the [nested ROW order checks](#nested-row-order-checks), on Iceberg, Delta and Hive (the fourth on Iceberg only) | as in the current record | every run stops before any `ALTER` with the `--full-refresh` error, and the table is unchanged |

F1's NULL inside a map value: a unit test with NULL against `''` in a map value fails on both
binaries (`map[a:] -> map[a:<nil>]`). adbc-drivers/trino returns MAP and ROW values as
Go-formatted text, and dbt splits an ARRAY into one column per element before it compares, so
no Trino value reaches the code that F1 changes. F1's Rust tests cover it.

### 892256e (4 October, without the follow-ups)

The run of 4 October, 21:25–21:47 EDT, tested `trino-pr/integration` 892256e: the series and the
fork-only commits. The binary banner was `dbt-oss 2.0.5 (892256e 2026-10-04 21:14:59)` and the
schema prefix `zz_fin_`. The functional suite (98 tests: 97 passed and 1 expected failure) and
the six jaffle-shop builds passed as in the current record. The Ctrl-C test also ran alone with
its `expectedFailure` flag cleared in that process only, and it failed with "query kept running
on the server after Ctrl-C".

#### Red/green checks of the review fixes

Each fix ran on a binary from before the fix (red) and on the 892256e binary (green), in its
own small project (schema prefix `zz_fin_rg_`) or with the suite test that is named. The red
baseline is the round-1 binary (8bf8443), in a copy that reads the 8bf8443 macro files; for S1
and S2, it is the pre-fix binary (1ff8a11) with its own macros.

| Item | Check | Before the fix | 892256e |
|---|---|---|---|
| R1 | unit test on `timestamp(12)`, `timestamp(12) with time zone` and `time(12)` (memory) | panic: `invalid time precision: 12` | passes; a wrong expectation fails with a diff; the fixture casts keep `TIMESTAMP(12)` |
| R4 | ephemeral tested model with `decimal(10,2)` and `char(2)` expected rows (memory) | the matching test fails (`12.0 -> 12.34`, `a -> ab`): the expected rows are cast to bare `DECIMAL` and `CHAR` | passes; the casts are `DECIMAL(10, 2)` and `CHAR(2)`; a wrong expectation fails |
| R9 | `skip` switches a view to a table on Delta (`test_basic.TestOnTableExists.test_skip_switches_a_view_to_a_table_on_delta`) | fails: `Renaming managed tables is not allowed with current metastore configuration` | passes; the table has the new row, and no `m__dbt_tmp` is left |
| R10 | a model without `catalog_name` when `catalogs.yml` exists (iceberg), and a direct `adapter.build_catalog_relation(config.model)` call without `catalog_name` | the model builds as well (not red: the built-in macros call `build_catalog_relation` only when `catalog_name` is set); the direct call gets the misleading Trino "Remove catalog_name" error | the model builds, and `catalog_name: lake` still gets the clear Trino error; the direct call gets the shared `Internal Error: build_relation_catalog cannot be invoked by an adapter Trino` (dbt9002) |
| R12 | docs catalog with `database: Iceberg` (mixed case) | `catalog.json` has no table comment; `check_schema_exists` is False | table and column comments present; `check_schema_exists` is True |
| R15 | a role grantee is not revoked as a user (hive) | every incremental rerun revokes the role's grant; the show-grants SQL has no `grantee_type` filter | no revoke for the role; the SQL reads `grantee_type = 'USER'`; the user's and the role's grants stay |
| S1 | uuid in `run_query` (`test_features.TestUuid.test_run_query`) | panic: `Casting from FixedSizeBinary(16) to Utf8 not supported` | `UUID=12151fd2-7586-11e9-8f9e-2a86e4085a59 NULL=None` |
| S2 | unit tests with a `varbinary` mismatch and 1 s and 1 µs `timestamp(6)` mismatches (memory) | all three pass; round 1 fails them, but shows the varbinary diff as hex (`616264 -> 616263`) | all three fail, and the varbinary diff is text (`abd -> abc`); equal rows pass |

The run also confirmed these limits of 892256e, on the memory catalog unless named:

- Unit tests compare `timestamp(9)` values only to the whole second (a 1 ns and a 1 ms
  difference pass; a 1 s difference fails), and `double` values to one decimal place (1.23
  against 1.24 passes; 1.23 against 1.33 fails, shown as `1.3 -> 1.2`).
- A `decimal(20, 2)` unit test lost the sign between -1 and 0, and an unquoted
  `query_timeout: 1.5` failed to parse. F1 and F2 fixed these two.
- On Delta, in `rename` mode, a switch from a view fails at the rename and leaves only
  `m__dbt_tmp`. The next run creates the table `m`, because nothing needs a rename, and a rerun
  of that table fails at the rename again.

## Known limits

**ADBC driver go/v0.5.3** (issue texts in [DRIVER-ISSUES.md](DRIVER-ISSUES.md), not filed
yet):

- Ctrl-C stops dbt, but a running query continues on Trino until it ends or until Trino
  abandons it after `query.client.timeout` (5 minutes by default).
- `timezone` is ignored: the session uses the Trino server's time zone.
- No client certificates (mTLS), OAuth 2.0, impersonation (`impersonation_user`), custom HTTP
  headers (`http_headers`) or Kerberos ticket cache: dbt stops with an error that names the
  option.
- `map`, `row` and `time with time zone` values in `run_query` are Go-formatted text, and
  HyperLogLog values fail.

**dbt v2 shared code:**

- `dbt run` and `dbt build` do not hydrate the relation cache, so with N threads a schema that
  is not cached yet can be listed up to N times (dbt-trino v1 lists it once).
- `dbt show` prints a uuid as 32 hex digits (the Arrow display of `FixedSizeBinary(16)`);
  `run_query`, contracts and unit tests show the canonical text.
- Unit tests compare `timestamp(7)` to `timestamp(12)` values only to the whole second, and
  `double` and `real` values to one decimal place. `main` already has these two comparisons,
  and S2 leaves them to dbt Labs.

**This adapter:**

- `catalogs.yml` catalog integrations (`catalog_name`) are not supported yet, and a custom macro
  that calls `adapter.build_catalog_relation` gets the shared internal error, because Trino has
  no default catalog relation yet.
- Nested ROW sync runs its `DROP COLUMN` statements first, as v1 does, and checks the field
  order only after all its `ALTER` statements. So with `sync_all_columns`, when one model change
  removes a field and also needs a type change that Iceberg cannot make (for example an
  `integer` field in the ROW elements of an `ARRAY` that becomes `varchar`), Iceberg drops the
  field and then fails, and the table is partly changed. A field added in the middle of a ROW
  is already at the end of the table's ROW when the order check stops the run. In both cases,
  the model needs a `--full-refresh`.
- Static analysis is disabled for Trino, as it is not part of the dbt v2 OSS build.

**Trino connectors** (as in dbt-trino v1, except where noted):

- Delta Lake on a Hive metastore cannot rename managed tables or views: use
  `on_table_exists: drop` or `replace`; `skip` never renames, so it works too. In `rename`
  mode, a switch from a view drops the view and then fails at the rename, which leaves the
  model without a relation until its next run (v1 failed earlier and kept the view).
- Delta Lake drops or renames columns only with `column_mapping_mode = 'name'`.
- Delta Lake and Hive cannot add, drop or change the type of a field inside a ROW column
  (`NOT_SUPPORTED`), so nested ROW sync fails there at its first `ALTER`, and the table does
  not change. This includes a new field order in the ROW elements of an `ARRAY` or `MAP` field
  with `sync_all_columns`, which Iceberg applies.
- Microbatch `concurrent_batches`: Iceberg rejects concurrent batch commits ("Found new
  conflicting delete files"), so batches stay sequential.
- Nested ROW sync: a top-level `ARRAY(ROW)` or `MAP(ROW)` column is not diffed field by field,
  so a reordered element ROW there is not detected, as in v1.

## Not tested

- **A live run on 112adf8.** No functional suite, jaffle-shop build or nested ROW check ran on
  a binary built on 112adf8; all live results above are on 7bbd974. The fork run of
  `trino-pr/integration` is the first live run on 112adf8. It is also the first test of the
  archive layout with the driver in `lib/dbt/`.

- **Linux x86_64 at run time.** The fork workflow builds the Linux archive and runs the
  functional suite and the jaffle-shop build with it, but it has not run on this series and
  its follow-ups, because nothing is pushed yet. Only the macOS ARM64 debug build ran live; no
  release build (`--release`) ran live.
- **The workspace gates on 7bbd974 with the follow-ups.** On 7bbd974, fmt, clippy and nextest
  ran on the four crates that the follow-ups and the revert of F3 change, and on each
  follow-up with the parts it needs, but not on the whole workspace. On 112adf8 the
  workspace gates ran on every `pr/` branch, Parts 2, 3b, 4 and 5 with F2 in their Part 1
  included (see [Gates on 112adf8](#gates-on-112adf8)).
- **The 26 ClickHouse record/replay tests** stop at setup on every branch, because this host
  has no `~/.dbt/profiles.yml` (see [Gates on 112adf8](#gates-on-112adf8)). They have no Trino
  code.
- **F1's NULL text with a Trino value:** no Trino value reaches that code (see the
  [red/green notes](#redgreen-checks-of-the-follow-ups)); it has Rust unit tests only.
- **dbt-trino v1 with a reorder in the ROW elements of an `ARRAY` or `MAP` field:** what v1
  does there (`SET DATA TYPE` with `sync_all_columns`, values in the wrong fields with
  `append_new_columns`) comes from its code (`impl.py` of v1.10.5), not from a v1 run.
- **Kerberos against a KDC:** unit tests only; the stack has no KDC.
- **Trino versions other than 483**, multi-node Trino, AWS S3, AWS Glue or a production
  metastore.
- **A real migration of a dbt 1.7.19 project:** [MIGRATION.md](MIGRATION.md) comes from the v1
  and v2 code and the lab tests.
- **`dbt init`** interactively: the wizard has headless unit tests only.

## Lab state after the run

The test projects drop their own schemas. After the run, the three `zz_f5_jaffle_acceptance_*`
schemas were dropped through their own catalogs. Each catalog's schema list is identical to the
list taken before the run (memory 2, hive 124, iceberg 125, delta 124 schemas), and the stack is
running. Trino ran through the whole run without a restart; its memory use reached 3.9 GiB of
the container's 4 GiB limit during the nested ROW order checks. The shared metastore still holds
`ft_test_failures_stored_in_audit_schema_7ed079_dbt_test__audit` (one Iceberg table,
`unique_m_id`), left by a run on 27 September before the suite dropped audit schemas. To drop
it, run this in `contrib/trino-lab`:

```sh
python3 scripts/stack.py sql \
  'drop schema iceberg."ft_test_failures_stored_in_audit_schema_7ed079_dbt_test__audit" cascade'
```

## Reproduce

See [README.md](README.md#run-it-locally-macos-or-linux). The logs of this run are not in the
repository.
