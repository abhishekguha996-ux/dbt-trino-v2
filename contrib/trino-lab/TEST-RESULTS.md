# Validation record — 25 September 2026

This is an experimental adapter, not a production readiness claim. The tested binary is dbt OSS 2.0.5 plus this fork's adapter changes, built in Linux ARM64 with Rust 1.96.0. The server is Trino 483. The ADBC Trino driver is `go/v0.5.3`. Machine-readable evidence is in [validation/results.json](validation/results.json).

| Check | Result |
|---|---|
| Unchanged upstream baseline build | Passed, dbt OSS 2.0.5 |
| Candidate Rust CLI build | Passed, offline, one Cargo job |
| SQL type tests | 43 passed |
| Authentication tests | 324 passed; 3 existing tests ignored |
| Column builder, SQL type formatting, DuckDB metadata regression tests | 34 passed |
| Loader macro/materialization test target | 181 passed, including 6 new Trino tests |
| Host configuration, archive extraction, fixture tests | 9 passed |
| Direct ADBC data tests | 25 passed |
| Retail on Memory | 10 seeds, 12 stored models, 14 data tests passed; 2 ephemeral models inlined |
| Retail on Iceberg | Same 36 executed nodes passed; 2 ephemeral models inlined |
| Retail rebuilds and catalog export | Passed on Memory and Iceberg |
| TPCH on Memory and Delta | 2 models and 5 data tests passed for each catalog |
| TPCH Python oracle | 60,175 source lines; all 138 shipping groups and 5 regional groups match exactly |
| Append on Memory | Initial, update, repeat, full refresh passed |
| Append and merge on Iceberg | All 8 stages passed; expected rows and no leftover staging tables checked |
| TLS/basic password transport | Trusted certificate passed; bad password, untrusted CA and wrong host name rejected |
| Password redaction | Synthetic password absent from debug output and dbt log files |
| Server execution timeout | Enforced; connection reusable after timeout |
| ADBC statement cancellation | **Open limitation:** did not stop an active query; the 10-second watchdog stopped it through Trino |
| Connection reuse after watchdog | Passed; no stress query left running |
| Iceberg/Delta persistence | Counts and totals unchanged after Trino restart |
| Isolation | Actual limits, named volumes, no host mounts/ports, dropped capabilities, internal network verified |

The final packaged workflow reuses the already prepared, frozen dependency cache. Earlier iterations found a Trino thread-pool burst that reached the 512 PID cap; the lab now bounds its internal query and callback pools without raising container limits. A separate interrupted run failed when the Mac slept. The final test run used a temporary awake assertion.

The retail join checks include inner, left, right, full outer, cross, self, non-equality, EXISTS and NOT EXISTS. They cover duplicate keys, null keys and unmatched rows. Aggregation coverage includes COUNT/DISTINCT, SUM, AVG, null and empty inputs, HAVING, FILTER, ROLLUP, GROUPING SETS and windows. Decimal, date, boolean, Unicode, apostrophe and SQL-like text seeds passed. Direct driver tests also cover Arrow ingestion, metadata and ten result batches.

Retail order totals are checked against a separate Python fixture generator. Net receipts are 757,230 cents across 200 orders. TPCH revenue is computed independently with Python dictionaries and Decimal arithmetic: shipping total `12364206.8366`, regional total `3391042.9114`.

## Limits and follow-up work

- ADBC cancellation needs driver investigation. Ctrl-C/client cancellation must not be relied on to stop server work. The lab has server time limits and a test watchdog; dbt CLI signal cancellation has not been qualified.
- Delta CTAS, queries and table rebuilds passed. Delta INSERT/MERGE on the local filesystem is rejected by Trino 483 because it has no local transaction-log synchronizer. Production object storage has not been tested.
- TLS tests use a local HTTPS proxy and synthetic Basic credentials. They test transport validation and credential redaction, not a real LDAP directory or corporate authentication service.
- `dbt compile --write-catalog` passed. `dbt docs generate` could not finish because its separate DuckDB driver is absent and the runtime cannot download it. No docs-site support claim is made.
- Static SQL analysis is disabled by upstream for this experimental adapter. Contracts are rejected. Microbatch, snapshots, Python models, grants, role selection, OAuth/Kerberos/JWT, source freshness, schema evolution, production metastores, distributed execution and concurrent writers are outside this validation.
- No full monorepo test suite, native macOS binary, x86 build, production workload or live tests for the other database adapters were run. The focused regression tests and all loader macro tests passed.
- Debian package versions are recorded at image build time, but their repositories are not snapshot-pinned. The source, Rust crate graph, driver and Python wheels are pinned. The lab disk monitor is a soft budget.

## Authentication compatibility review

No existing borrowed authentication field became owned. Existing adapter accessor behavior, accepted input forms, enum structure and normalization remain unchanged. The new Trino path borrows string fields until the URL builder boundary. It uses `get_str` for actual strings and `get_string` only for the integer-or-string port, followed by a nonzero u16 check. URI option values are encoded; HTTPS is the default; password-over-HTTP and unsupported methods/roles fail explicitly.

Before a production or upstream release, a maintainer should run the live authentication smoke suite described in `crates/dbt-auth-tests/README.md` for their deployment, in addition to these synthetic tests. No real credential was used in this lab.

## Review

The adapter architecture review checked shared implementations, platform-specific module boundaries, SQL utilities, dependencies and Jinja objects. Relations and metadata parsing reuse generic paths. Trino authentication lives in its own auth module. SQL parsing changes live in dbt-adapter-sql. No new crate dependency or dbt-adbc method was added. Shared seed and merge macros use optional arguments with regression tests for their unchanged defaults.
