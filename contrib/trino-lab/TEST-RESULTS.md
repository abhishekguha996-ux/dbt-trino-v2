# Test results — 5 October 2026

Experimental adapter; this is a test record, not a production-readiness claim. The current
record is the run of 5 October on `trino-pr/integration` e7a1675: the series and its three
[follow-ups](UPSTREAM.md#follow-ups). The [previous record](#previous-record-892256e-4-october),
the run of 4 October on 892256e, tested the series without the follow-ups. The 27 September
record (72 tests, before the rebase onto dbt-labs `main` 7bbd974 and the review fixes) is in the
git history of this file.

## What was tested

| Item | Value |
|---|---|
| Base | dbt-labs/dbt `main` 7bbd974 (`7bbd974389dbd08da3ece92396ecdd0c8f99719c`, 2 October 2026) |
| Series | `trino-pr/series` 6f3a4a3: the nine parts of [UPSTREAM.md](UPSTREAM.md#the-pr-series) |
| Follow-ups | `trino-pr/followups` 135bdd0: the series plus F1 a5767d1 (for S2), F2 25a4eca (for Part 1) and F3 135bdd0 (for Part 4) |
| Tested commit | `trino-pr/integration` e7a1675: the series, the fork-only `contrib/` and `.github/` commits, and the three follow-ups as 99233a2, 56e7e77 and e7a1675. Its `crates/` and `.changes/` are the same as in `trino-pr/followups`. Later commits on `trino-pr/integration` change only documentation in `contrib/trino-lab/` |
| dbt binary | `cargo build -p dbt-sa-cli --bin dbt` (debug profile), native macOS ARM64, Rust 1.96. `dbt --version` prints `dbt-oss 2.0.5`, and every `dbt.log` shows the banner `dbt-oss 2.0.5 (e7a1675 2026-10-04 23:06:36)`. A debug build reads the macro files from its source tree at run time; that tree was clean at e7a1675 during the run |
| ADBC driver | adbc-drivers/trino `go/v0.5.3` (`libadbc_driver_trino.dylib`, macos_arm64 archive) |
| Trino | 483 (`trinodb/trino:483`, single node) |
| Catalogs | `memory`; `hive` (`sql-standard` security), `iceberg` and `delta` on one Hive metastore 3.1.3 (Postgres 18) with RustFS (S3 API); `tpch` |
| Auth | HTTP without authentication (port 8080); HTTPS (port 8443) with a password file and JWT (RS256), signed by the lab CA |
| Harness | Python 3.13.7; `SCHEMA_PREFIX=zz_r3_`, a private `HOME` and `TMPDIR`; 5 October 2026, 14:35–14:51 EDT |

## Rust checks

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

The follow-ups were checked on 4 October:

- **At the tip** of `trino-pr/followups`, 135bdd0: `cargo fmt --all --check` is clean, and
  `cargo check --all-targets`, `cargo clippy --all-targets -- -D warnings` and `cargo nextest`
  pass on the four crates that the follow-ups change (dbt-tasks-sa, dbt-schemas, dbt-auth and
  dbt-loader): 1,509 passed, 4 skipped. The workspace-wide gates have not run on this commit.
- **Alone**, on 7bbd974 with only the parts in its "Needs first" column cherry-picked before
  it: `cargo fmt --all --check`, and `cargo check --all-targets`,
  `cargo clippy --all-targets -- -D warnings` and `cargo nextest` on its crates. 3 of 3
  follow-ups apply cleanly and pass:

| Follow-up | Commit | Alone on 7bbd974 with | `cargo nextest` alone |
|---|---|---|---|
| F1 | a5767d1 | S2 | dbt-tasks-sa: 194 passed |
| F2 | 25a4eca | Part 1 | dbt-schemas, dbt-auth: 1,033 passed, 4 skipped |
| F3 | 135bdd0 | Parts 1, 2 and 4 | dbt-loader: 279 passed |

## Functional suite (`functional/`, live stack)

Each module ran alone: `python3 -m unittest -v <module>`, with `DBT_BIN` set to the binary
above. Most tests loop over the catalogs as subtests. The suite is the same as in the previous
record.

**98 tests: 97 passed and 1 expected failure, with 0 failures, 0 errors and 0 skips.**

| Module | Tests | Result | Time | Covers |
|---|---|---|---|---|
| test_auth | 14 | 14 passed | 8.0 s | LDAP-style password with a CA bundle, a password with URL-special characters, wrong password (rejected and redacted), JWT (the token is not in the output or `dbt.log`), `cert: false`, untrusted certificate, password over HTTP refused, `dbt-trino-*` source header (client tags are set, not checked); profile checks: host name only, `query_timeout` values, `role`, `starburst_*` keys |
| test_basic | 18 | 18 passed | 61.3 s | seeds, tables, views, ephemeral models and reruns; mixed-case names; view ↔ table switches; `on_table_exists` (rename, drop, replace, skip; the Delta rename limit; a failed switch from a view keeps it in `rename` mode; `skip` switches a view to a table on Delta); `view_security`; `properties`, `file_format` conflicts, `storage_uri`; `sql_header` |
| test_incremental | 23 | 23 passed | 92.1 s | append (all catalogs, default strategy, full refresh, `views_enabled: false`); merge (single and composite keys, update and exclude columns, predicates); delete+insert; `insert_overwrite` rejected; microbatch (daily, seven daily batches rerun); every `on_schema_change` mode, with type changes; nested ROW sync (field order, nested ROWs, a field in the middle of a ROW asks for `--full-refresh`) |
| test_features | 32 | 32 passed | 82.6 s | snapshots (timestamp, check, hard deletes); materialized views (create, refresh, full refresh, a failed full refresh keeps the view, mixed-case names, replace a table); grants and revokes, also in a mixed-case schema; `persist_docs`; contracts; seeds (types, escaping, JSON, overrides, 2,500 rows, v1 integer inference); unit tests and fixture types; uuid in `run_query`, contracts and unit tests; hooks and session properties; cross-database macros; debug, parse, compile, list, show, docs and `catalog.json`, `--empty`, retry, source freshness, clone, `--defer` |
| test_more | 9 | 8 passed, 1 expected failure | 54.0 s | query comments, custom schemas, `store_failures` (audit schema), snapshot `new_record`, enforced `query_max_run_time`, `dbt_utils`, `catalog_name` error, Python model rejection, Ctrl-C (**expected failure**) |
| test_projects | 2 | 2 passed | 36.0 s | retail (36 nodes) on all four catalogs against Python-generated expectations; TPC-H Q3/Q5-style marts on all four catalogs against a Python/Decimal oracle |

Fixture unit tests (`tests/`, `python3 -m unittest discover -s tests`): 2 passed.

**The expected failure** is `test_more.TestSessionLimits.test_ctrl_c_stops_server_query`. After
SIGINT, `system.runtime.queries` showed the query `RUNNING` until the test's cleanup killed it
(`ADMINISTRATIVELY_KILLED`, 37.8 s after the query started). This is the driver limit
[Cancel does not stop a running query](DRIVER-ISSUES.md#cancel-does-not-stop-a-running-query).
No query was left running.

## jaffle-shop-classic acceptance build

`acceptance/run_jaffle_shop.sh` with `SCHEMA_PREFIX=zz_r3_`, unchanged: jaffle-shop-classic
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
exactly; on Iceberg and Delta, `customers_snapshot` has 100 rows, all current.

## Red/green checks of the follow-ups

Each follow-up ran in its own small project (schema prefix `zz_r3_rg_`) on the binary above and
on the binary of the [previous record](#previous-record-892256e-4-october), 892256e.

F1 and F2 change Rust code, so their baseline is the 892256e binary as built. F3 changes only
macro files, and a debug build reads them from its source tree at run time: as built, the
892256e binary runs the e7a1675 macros. So the F3 baseline is a copy of the 892256e binary in
which only the path of the macro files was changed, to a `git archive` of 892256e. A macro probe
confirmed which tree each binary reads. A control run of the 892256e binary as built stops
before any `ALTER`, as the e7a1675 binary does, so F3 changes behavior through the macros only.

| Item | Check | 892256e | e7a1675 |
|---|---|---|---|
| F1 | unit tests on a `decimal(20, 2)` column (memory), actual value against expected value: -0.50 against 0.50, 0.50 against -0.50, and -0.05 against 0.05 | all three pass | all three fail, with the sign in the diff, for example `0.50 -> -0.50` |
| F1 | 0.05 against 0.50 on the same column | fails; the diff shows `0.50 -> 0.5` | fails; the diff shows `0.50 -> 0.05` |
| F1 | equal values, and equal NULLs, in 25 columns from `tinyint` to `map` and `row` (memory) | pass | pass |
| F2 | profiles with an unquoted `query_timeout: 1.5` and `2.0` | `dbt debug` fails: `data did not match any variant of untagged enum StringOrInteger` | `dbt debug` passes, and `dbt run` builds the model |
| F2 | a query that runs about 6 s (`tpch.sf10`), with `query_timeout` 1.5, 3.5 and 300 | the quoted `"1.5"` cancels it after 1.52 s; 300 lets it finish | 1.5 and 3.5 cancel it on the server after 1.51 s and 3.58 s (`USER_CANCELED`); 300 lets it finish (6.3 s) |
| F2 | `query_timeout` 0.0, -1.5 and `true` | the parse error above | the Trino messages: "must be greater than zero; remove it to use the driver default of 10h", and "must be a number of seconds or a duration such as 300s, 30m or 1h; got '-1.5'" (or `'true'`) |
| F3 | `sync_all_columns` and `sync_nested_columns`, inside a `ROW` column: an `ARRAY(ROW)` reorder, the same with a removed field, and a `MAP(ROW)` reorder; each on Iceberg, Delta and Hive | Iceberg runs the `ALTER` statements, and the run succeeds with correct data; Delta and Hive fail at the first `ALTER` with `NOT_SUPPORTED` | every run stops before any `ALTER` with the `--full-refresh` error, and the table is unchanged |
| F3 | Iceberg: a reorder with a field changed from `integer` to `varchar`, and a removed field | the `DROP` of the removed field runs, then `SET DATA TYPE` fails with `ICEBERG_COMMIT_ERROR`, without the `--full-refresh` message; the table is partly changed | stops before any `ALTER` |
| F3 | Iceberg, `append_new_columns`: a reorder with a removed field | stops with the `--full-refresh` error; no `ALTER` | the same |

- **F1, NULL inside a map value:** a unit test with NULL against `''` in a map value fails on
  both binaries (`map[a:] -> map[a:<nil>]`). adbc-drivers/trino returns MAP and ROW values as
  Go-formatted text, and dbt splits an ARRAY into one column per element before it compares, so
  no Trino value reaches the code that F1 changes. F1's Rust tests cover it.
- **F3 on Iceberg:** without F3, the plain reorder and the reorder with a removed field succeed
  with correct data, because Iceberg keeps each value in its field when it applies the type
  change. With F3, these runs stop and ask for `--full-refresh`. This is the
  [open review finding](UPSTREAM.md#follow-ups) on F3.
- **F3 after the stop:** the `--full-refresh` that the error asks for rebuilds the table in the
  model's order on Iceberg and Hive. On Delta, it fails in the default `rename` mode (the Delta
  rename limit under [Known limits](#known-limits)), and it works with
  `on_table_exists: replace`.

**Trino stopped once during the run.** At 14:45:45 EDT, the kernel stopped the Trino container
for lack of memory (exit 137, `OOMKilled`). The container has a 4 GiB limit and runs Trino with
`-Xmx3G`; it had run for 22 hours, and the F2 timeout check had just run eight `tpch.sf10`
scans. It was started again with `docker start`, with the same configuration and volumes. Hive,
Iceberg and Delta passed a create, select and drop check, and the F3 checks ran again in full
(Trino used at most 1.78 GiB). The suite, the jaffle-shop build, F1 and F2 had finished before
the stop.

## Previous record: 892256e (4 October)

The run of 4 October tested `trino-pr/integration` 892256e: the series and the fork-only
commits, without the follow-ups. The binary banner was
`dbt-oss 2.0.5 (892256e 2026-10-04 21:14:59)`, the schema prefix `zz_fin_`, and the run took
place from 21:25 to 21:47 EDT. Everything else was as in the current record.

**Functional suite:** 98 tests, 97 passed and 1 expected failure, with 0 failures, 0 errors and
0 skips: test_auth 14 passed (7.9 s), test_basic 18 passed (61.2 s), test_incremental 23 passed
(95.6 s), test_features 32 passed (91.4 s), test_more 8 passed and 1 expected failure (54.3 s),
test_projects 2 passed (34.4 s). Fixture unit tests: 2 passed. The Ctrl-C test ran three times:
in its module, alone as written (expected failure again), and alone with the `expectedFailure`
flag cleared in that process only, where it fails with "query kept running on the server after
Ctrl-C". Each time, `system.runtime.queries` showed the query `RUNNING` about 37 s after
SIGINT, until the test's cleanup killed it (`ADMINISTRATIVELY_KILLED`).

**jaffle-shop-classic:** the same six builds and data checks as in the current record, with
`SCHEMA_PREFIX=zz_fin_`: 32 of 32 twice on Iceberg and on Delta, and 31 of 31 twice on Hive.

### Red/green checks of the review fixes

Each fix ran on a binary from before the fix (red) and on the 892256e binary (green), in its
own small project (schema prefix `zz_fin_rg_`) or with the suite test that is named.

The red baseline is the round-1 binary (8bf8443). A debug build reads its macro files from
its source tree at run time, so as built it would run the round-1 Rust code with the final
macros and show the macro-only fixes (R9, R12, R15) as already fixed; control runs confirmed
this. The baseline therefore is a copy of that binary that reads a `git archive` of the 8bf8443
macro files. S1 and S2 were already in round 1, so their baseline is the pre-fix binary
(1ff8a11) with its own macros.

| Item | Check | Before the fix | 892256e |
|---|---|---|---|
| R1 | unit test on `timestamp(12)`, `timestamp(12) with time zone` and `time(12)` (memory) | panic: `invalid time precision: 12` | passes; a wrong expectation fails with a diff; the fixture casts keep `TIMESTAMP(12)` |
| R4 | ephemeral tested model with `decimal(10,2)` and `char(2)` expected rows (memory) | the matching test fails (`12.0 -> 12.34`, `a -> ab`): the expected rows are cast to bare `DECIMAL` and `CHAR` | passes; the casts are `DECIMAL(10, 2)` and `CHAR(2)`; a wrong expectation fails |
| R9 | `skip` switches a view to a table on Delta (`test_basic.TestOnTableExists.test_skip_switches_a_view_to_a_table_on_delta`) | fails: `Renaming managed tables is not allowed with current metastore configuration` | passes; the table has the new row, and no `m__dbt_tmp` is left |
| R10 | a model without `catalog_name` builds when `catalogs.yml` exists (iceberg) | builds as well: not red, see below | builds; `catalog_name: lake` still gets the clear Trino error |
| R12 | docs catalog with `database: Iceberg` (mixed case) | `catalog.json` has no table comment; `check_schema_exists` is False | table and column comments present; `check_schema_exists` is True |
| R15 | a role grantee is not revoked as a user (hive) | every incremental rerun revokes the role's grant; the show-grants SQL has no `grantee_type` filter | no revoke for the role; the SQL reads `grantee_type = 'USER'`; the user's and the role's grants stay |
| S1 | uuid in `run_query` (`test_features.TestUuid.test_run_query`) | panic: `Casting from FixedSizeBinary(16) to Utf8 not supported` | `UUID=12151fd2-7586-11e9-8f9e-2a86e4085a59 NULL=None` |
| S2 | unit tests with a `varbinary` mismatch and 1 s and 1 µs `timestamp(6)` mismatches (memory) | all three pass; round 1 fails them, but shows the varbinary diff as hex (`616264 -> 616263`) | all three fail, and the varbinary diff is text (`abd -> abc`); equal rows pass |

R10 was never red in the form the review stated it, because the built-in macros call
`build_catalog_relation` only when `catalog_name` is set. The fix shows on a direct
`adapter.build_catalog_relation(config.model)` call without `catalog_name`: the round-1 binary
answers with the misleading Trino "Remove catalog_name" error, and the 892256e binary with the
shared `Internal Error: build_relation_catalog cannot be invoked by an adapter Trino`
(dbt9002), because Trino has no default catalog relation yet. `catalog_name: 'none'` gets the
shared "not defined in catalogs.yml" error on both binaries.

### Further checks with the 892256e binary

These checks confirmed limits of 892256e. F1 and F2 have fixed two of them since (see the
[red/green checks of the follow-ups](#redgreen-checks-of-the-follow-ups)):

- Unit tests on the memory catalog, actual value against expected value:
  - `timestamp(9)`: a 1 ns and a 1 ms difference pass; a 1 s difference fails.
  - `double`: 1.23 against 1.24 passes; 1.23 against 1.33 fails, shown as `1.3 -> 1.2`.
  - `decimal(20, 2)`: -0.50 against 0.50 passes; -0.50 against -0.51 fails, shown without the
    signs as `0.51 -> 0.50`. Fixed by F1.
- A profile with `query_timeout: 1.5` (unquoted) fails to parse with `data did not match any
  variant of untagged enum StringOrInteger`; with `"1.5"`, `dbt debug` passes. Fixed by F2.
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
- With `sync_all_columns`, a reorder in the ROW elements of an `ARRAY` or `MAP` field inside a
  ROW column stops the run and asks for `--full-refresh`, also on Iceberg, which can apply the
  reorder in place, as dbt-trino v1 does (the [open review finding](UPSTREAM.md#follow-ups) on
  F3).
- Static analysis is disabled for Trino, as it is not part of the dbt v2 OSS build.

**Trino connectors** (as in dbt-trino v1, except where noted):

- Delta Lake on a Hive metastore cannot rename managed tables or views: use
  `on_table_exists: drop` or `replace`; `skip` never renames, so it works too. In `rename`
  mode, a switch from a view drops the view and then fails at the rename, which leaves the
  model without a relation until its next run (v1 failed earlier and kept the view).
- Delta Lake drops or renames columns only with `column_mapping_mode = 'name'`.
- Microbatch `concurrent_batches`: Iceberg rejects concurrent batch commits ("Found new
  conflicting delete files"), so batches stay sequential.
- Nested ROW sync: a top-level `ARRAY(ROW)` or `MAP(ROW)` column is not diffed field by field,
  so a reordered element ROW there is not detected, as in v1.

## Not tested

- **Linux x86_64 at run time.** The fork workflow builds the Linux archive and runs the
  functional suite and the jaffle-shop build with it, but it has not run on this series and
  its follow-ups, because nothing is pushed yet. Only the macOS ARM64 debug build ran live; no
  release build (`--release`) ran live.
- **The workspace gates with the follow-ups.** fmt, clippy and nextest ran on the four crates
  that the follow-ups change, and on each follow-up with the parts it needs, but not on the
  whole workspace. They did not run on Parts 2, 3b, 4 and 5 with F2 in their Part 1, as the
  [per-PR recipe](UPSTREAM.md#how-to-open-a-pr-from-the-fork) cuts them.
- **F1's NULL text with a Trino value:** no Trino value reaches that code (see the red/green
  notes); it has Rust unit tests only.
- **Kerberos against a KDC:** unit tests only; the stack has no KDC.
- **Trino versions other than 483**, multi-node Trino, AWS S3, AWS Glue or a production
  metastore.
- **A real migration of a dbt 1.7.19 project:** [MIGRATION.md](MIGRATION.md) comes from the v1
  and v2 code and the lab tests.
- **`dbt init`** interactively: the wizard has headless unit tests only.

## Lab state after the run

Every `zz_r3*` schema was dropped through its own catalog: the three jaffle-shop schemas and
one Iceberg schema that the F3 checks left when Trino stopped. Each catalog's schema list is
identical to the list taken before the round-3 checks began (memory 2, hive 124, iceberg 125,
delta 124 schemas), and the stack is running. The shared metastore still holds
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
