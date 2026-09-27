# Contributing the Trino adapter to dbt-labs/dbt

Nothing in this fork has been submitted to dbt-labs/dbt. This is the kit for when you decide
to. The local clone's `upstream` remote has its push URL disabled on purpose.

## How contributions reach dbt v2 (research, 28 September 2026)

- **Guide:** [Contribute adapters to dbt v2](https://docs.getdbt.com/docs/contribute-dbt-adapters-v2) and
  [adapter creation guide](https://docs.getdbt.com/guides/adapter-creation-v2).
  - Community contributors own **Phase 1**: connect, run macros, and materialize tables, views,
    incremental models and snapshots.
  - Phase 2, SQL static analysis, is led by dbt Labs. They have already opened
    "[Trino] Add typechecking support" issues #14657–#14708.
  - **Acceptance bar:** "a clean `dbt build` on jaffle-shop-classic".
  - A **user setup guide** that names the exact driver library is required
    ([draft](docs-site/trino-setup.md)).
- **CLA first.** `cla-bot` asks for the individual CLA on your first PR. Nothing moves until it
  is signed. The only earlier Trino PR, #15345, stalled because its CLA was never signed.
- **How a PR is merged:**
  - A maintainer adds the label `ci:approve-public-fork-ci`.
  - Copybara then copies the PR into dbt Labs' private repo, where CI and review happen.
  - The public PR ends as **Closed, not Merged**. The landed commit is authored by
    `fa-assistant`, with you as `Co-authored-by`.
  - Every push removes the CI label, so batch your fixes into fewer pushes.
  - Don't open drafts: drafts aren't synced.
  - Rebase quickly if the bot sets `sync-failed`.
- **Required:**
  - an issue link (template: PRs "without an associated issue will not be merged")
  - a `changie` entry per PR
  - Product/DX sign-off for interface changes (new configs and macros count)
- **People:**
  - Hope Watson (`hope-wat`): adapter triage and CI label; the named contact in `#adapter-ecosystem` on dbt Slack.
  - Felipe Oliveira Carvalho (`felipecrv`): main adapter reviewer.
  - Lucas Valente (`serramatutu`): architecture.
  - `dataders`: adapter DevRel. Wrote the ClickHouse series and invited a community Trino adapter on #13131.
- **What landed fast:**
  - small focused PRs that follow v1 behavior (ClickHouse parts landed in 1–6 days)
  - CLA signed on day one
  - the rules in `.agents/adapters.md` respected
  - quick rebases
- **What stalled:**
  - unsigned CLA
  - adapters not on dbt Labs' current focus
  - platform-specific code in generic crates
  - competing or unsequenced series (Athena: two stacks, 0 reviews after weeks)
  - no Slack coordination
- **Exasol precedent:** landed as one 50-file PR in 65 days while experimental. So experimental
  adapters are accepted.

## The series (branches in this fork)

Each branch is stacked on the previous one. Each one compiles, passes `cargo fmt --check`,
passes `cargo clippy -D warnings` and passes the tests of the crates it touches. Together they
reproduce `trino-v2-adapter`'s `crates/` exactly. `contrib/` and `.github/` are fork-only and
never go upstream.

| # | Branch | Scope | Depends on |
|---|---|---|---|
| 0 | `trino/p0-redact-access-token` | dbt-adbc: redact `accessToken` in Builder Debug output (generic, tiny) | — |
| 1 | `trino/p1-profile-auth` | TrinoDbConfig, dbt-auth Trino module, `backend_of` | 0 (for safe JWT logging) |
| 2 | `trino/p2-types-relations` | relations, columns, SQL types, seeds, literals, microbatch filters | 1 |
| 3a | `trino/p3a-generic-metadata-adapter` | Exasol metadata adapter → GenericMetadataAdapter, no behavior change | 2 |
| 3b | `trino/p3b-metadata` | Trino relation cache, get_relation, materialized-view detection | 3a |
| 4 | `trino/p4-macros-materializations` | vendored dbt-trino v1.10.5 macros, configs, strategies, grants, nested ROW sync, loader tests | 3b |
| 5 | `trino/p5-init-wizard` | `dbt init` wizard | 4 |

GitHub PRs from a fork must target `main`, so later PRs show the earlier parts' commits too.
Each PR says "depends on #N; review only the last commit", as the Athena series does. If
maintainers prefer one PR (as with Exasol), open `trino-v2-adapter`'s crates-only commit instead.

## Order of work

1. **Sign the CLA:** read https://docs.getdbt.com/docs/contributor-license-agreements and sign the
   individual form (the same one `cla-bot` links on your first PR:
   https://docs.google.com/forms/d/e/1FAIpQLScfOV7K4enYRHozrDRP6BBIXjOij-JDGca6WBTHyP_ANXSqlg/viewform).
   If you write this on work time or with work equipment, ask your employer first; a Corporate
   CLA may be needed.
2. **Coordinate before opening PRs.** Post the Slack message below in `#adapter-ecosystem` and
   comment on #13131. Ask two questions: is Starburst or dbt Labs already building a Trino
   adapter, and is a series or a single PR preferred? Wait for an answer.
3. **Open the umbrella issue** (text below) and link it from #13131.
4. **Open Part 0**, then Part 1 when Part 0 has a reviewer, and so on. Keep at most two open at once.
5. After each review round, reply to every comment, push once, and ask for the CI label again.
6. After Part 4 lands, open a docs.getdbt.com PR with the setup guide.

## Slack message (`#adapter-ecosystem`, tag Hope Watson)

> Hi @Hope Watson — I've built a Phase 1 Trino adapter for dbt v2 on the adbc-drivers/trino
> driver (go/v0.5.3), following the adapter guide. jaffle-shop-classic plus an incremental
> model and a snapshot build clean on Iceberg and Delta Lake, and on Hive (no snapshot, since
> Hive can't MERGE). It keeps dbt-trino v1 profile fields and vendors the dbt-trino v1.10.5 macros.
> Evidence and code: https://github.com/abhishekguha996-ux/dbt-trino-v2 (contrib/trino-lab).
> Before I open PRs against #13131: (1) is anyone at dbt Labs or Starburst already working on
> Trino, and (2) would you prefer a small series like ClickHouse Parts 0–8, or one PR like
> Exasol? I've signed the CLA and can hand over a Trino test setup for your CI.

## Umbrella issue (title: "[Trino] Phase 1 adapter: merge plan")

> Tracks the Phase 1 Trino adapter for dbt v2 (#13131), built on the Apache-2.0
> [adbc-drivers/trino](https://github.com/adbc-drivers/trino) driver, loaded by name
> (`libadbc_driver_trino.so/.dylib`) as community adapters require.
>
> | Part | PR | Scope |
> |---|---|---|
> | 0 | #… | Redact `accessToken` in ADBC Builder debug output |
> | 1 | #… | Profile schema + auth (none, ldap, jwt, kerberos; v1 profile fields) |
> | 2 | #… | Relations, columns, types, seeds, literals |
> | 3a | #… | Share Exasol's metadata adapter as GenericMetadataAdapter (no behavior change) |
> | 3b | #… | Trino metadata: relation cache, get_relation, materialized views |
> | 4 | #… | dbt-trino macro package, materializations, configs |
> | 5 | #… | `dbt init` wizard |
>
> **Evidence:** jaffle-shop-classic (+incremental, +snapshot) clean builds on Trino 483 (Iceberg,
> Delta Lake, Hive on S3), plus a 72-test functional suite, all reproducible from
> https://github.com/abhishekguha996-ux/dbt-trino-v2/tree/trino-v2-adapter/contrib/trino-lab.
>
> **Known driver limits** (reported to adbc-drivers/trino): statement cancel after
> ExecuteQuery; no mTLS, OAuth, impersonation or custom HTTP headers.

## PR descriptions

Each PR starts with `Resolves #13131` (Parts 0–4 use `Part of #<umbrella>`) and uses the
repository template.

### Part 0 — `fix(adbc): redact accessToken URI parameters in Builder Debug output`

**Problem:** Some ADBC drivers (trino-go-client-based ones, such as adbc-drivers/trino) accept
bearer tokens only as a URI query parameter (`accessToken`). `database::Builder`'s `Debug` impl
redacts `user`, `username` and `password` query parameters, but not `accessToken`, so a JWT would
appear in debug logs.

**Solution:** Add `accessToken` to the redacted query keys. No new methods or traits; one unit
test (`uri_access_token_is_redacted`).

### Part 1 — `feat(trino): profile schema and ADBC authentication`

**Problem:** `AdapterType::Trino` exists, but `backend_of` is `todo!("Trino")`, `TrinoDbConfig` has
6 fields, and there is no Trino auth, so any Trino profile panics.

**Solution:**
- `TrinoDbConfig` accepts the dbt-trino v1 credential fields (`catalog` aliases `database`), so
  existing profiles load unchanged. The target context exposes host, port, user, method,
  http_scheme, timezone, client_tags and `prepared_statements_enabled`.
- `dbt-auth/src/trino` maps them to trino-go-client DSN options:
  - methods `none`, `ldap`, `jwt` and `kerberos` (keytab)
  - `roles`, `session_properties`, `client_tags`, `timezone`, `query_timeout`
  - `cert` (CA bundle or `false`, which warns unless `suppress_cert_warning`)
  - `X-Trino-Source: dbt-trino-<version>`, so resource-group selectors keep matching
- v1 options the driver can't honor (certificate, oauth, gssapi, `http_headers`,
  `impersonation_user`) fail with explicit errors. `retries` warns.
- `backend_of(Trino)` is `Backend::Generic { library_name: "adbc_driver_trino" }`, loaded like
  Exasol and Athena. No dbt-adbc changes.

**Tests:** 12 unit tests: every method and option, DSN injection resistance, secret handling,
warnings. Live-tested over HTTPS with password, JWT, a CA bundle and `cert: false`.

### Part 2 — `feat(trino): relations, columns, SQL types and literals`

**Problem:** The parse and compile paths hit `todo!("Trino")` in the relation factory, column
builder, SQL type metadata key, seed column naming and the microbatch event-time filter.

**Solution:**
- Relations use the generic `RelationStatic` path.
- Columns use the shared builder: Exasol's `build_exasol`, renamed `build_standard`. Exasol's
  behavior is unchanged.
- Trino types round-trip: `ROW`, `ARRAY(...)`, `MAP(...)`, `VARBINARY`, `DECIMAL`, and `UInt64` →
  `DECIMAL(20, 0)`.
- `TrinoColumn` type labels and predicates, and `from_description` keeps nested types verbatim
  (v1 `column.py`).
- Seeds get `DATE`/`TIMESTAMP` typed literals.
- The microbatch filter uses `TIMESTAMP '… UTC'` literals, in one arm shared with Exasol
  (v1 `relation.py`).

Each change links the v1 code it mirrors.

### Part 3a — `refactor(adapter): share the Exasol metadata adapter as GenericMetadataAdapter`

No behavior change. It renames `ExasolMetadataAdapter` to `GenericMetadataAdapter`, following the
"`GenericFoo` + `match adapter_type`" rule in `.agents/adapters.md`, and moves DuckDB's
`information_schema` row conversion into a shared helper. Exasol and DuckDB tests are unchanged.

### Part 3b — `feat(trino): metadata adapter, relation listing and get_relation`

Trino uses the generic metadata adapter. It fills the relation cache from
`<catalog>.information_schema.tables` and finds materialized views through
`system.metadata.materialized_views`, as v1's `trino__list_relations_without_caching` does.
Transactions are reported as unsupported (dbt-trino runs in autocommit), and `list_schemas`
reads `schema_name`. DuckDB's `get_relation` SQL is byte-identical.

### Part 4 — `feat(trino): dbt-trino macro package, materializations and model configs`

**Problem:** There's no Trino macro package, so nothing materializes.

**Solution:**
- **Vendored macros:** dbt-trino v1.10.5 (Apache-2.0; provenance in each file header and in
  `dbt_macro_assets/README.md`). Every v2 adaptation is marked `v2:`:
  - `information_schema('<view>')`
  - `%s` binding literals
  - escaping of interpolated literals
  - catalog SQL types
  - drop-before-add column sync
  - renames qualified with catalog and schema
- **Config keys:** `properties`, `on_table_exists`, `view_security`, `views_enabled`,
  `sync_nested_columns` and `grace_period`, using dbt-trino's names (Exasol precedent).
- **Adapter behavior:**
  - constraint support (`not_null` enforced), taken from v1 `CONSTRAINT_SUPPORT`
  - grants use the standard parser
  - incremental strategies: append, merge, delete+insert, microbatch, plus Hive `insert_overwrite`
  - seed types match v1 (`INTEGER`, `DOUBLE`, bare `TIMESTAMP`)
- **Nested ROW schema sync:** `adapter.diff_nested_column_types`, a generic struct diff in
  `dbt-adapter-sql`.
- No shared `dbt-adapters` macros are changed.

**Tests:** 12 loader macro tests.

**Evidence:**
- jaffle-shop-classic (+incremental, +snapshot) builds clean on Iceberg, Delta Lake and Hive on S3.
- The 72-test functional suite passes on Memory, Hive, Iceberg and Delta Lake.
- Retail and TPC-H projects match Python oracles.

### Part 5 — `feat(trino): dbt init profile wizard`

Adds `TrinoDbConfig` to `dbt init`'s interactive setup: host, method, port, user, and a
password, JWT or keytab depending on the method, plus catalog and schema.

## Maintainer decisions to expect

1. **Driver distribution:** a community driver is loaded by name, with no CDN. The setup guide
   documents this. Starburst's driver may change it later.
2. **Part 0 touches dbt-adbc.** It's a redaction list entry, not a method, but be ready to drop
   it if they prefer.
3. **Interface changes** (config keys, `diff_nested_column_types`) need Product/DX approval. Ask in
   the umbrella issue before Part 4.
4. **Microbatch concurrency:** Trino stays out of `MICROBATCH_SUPPORTED_ADAPTERS` because
   concurrent batches conflict in Iceberg/Delta commits.

## Driver issues (for adbc-drivers/trino, separately)

- **Cancellation:** `AdbcStatementCancel` only cancels a call that is still executing. The query
  is polled while the result stream is read, after `ExecuteQuery` returned, and driverbase's
  `FinishContext` untracks that context, so cancel is a no-op. Repro:
  `functional/test_more.py::TestSessionLimits::test_ctrl_c_stops_server_query`.
- **Not exposed:** client certificate (mTLS) auth, custom HTTP headers, impersonation,
  Kerberos ticket cache and interactive OAuth2.
