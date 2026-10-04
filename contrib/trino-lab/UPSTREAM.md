# Contributing the Trino adapter to dbt-labs/dbt

Nothing in this fork has been submitted to dbt-labs/dbt. This is the kit for when you decide
to. The local clone's `upstream` remote has its push URL disabled on purpose. Facts in this
file were checked on 3 October 2026.

Before the first PR, in this order:

1. Sign the [Individual CLA](#individual-cla).
2. Finish the review fixes in the seven parts, rebuild the parts on the latest dbt-labs `main`,
   and record the checks and the live results with commit SHAs in
   [TEST-RESULTS.md](TEST-RESULTS.md).
3. File the [driver issues](DRIVER-ISSUES.md).
4. Post the [Slack message](#slack-message) and ask which [PR shape](#pr-shape-options) the
   maintainers want.

## Individual CLA

**What it is.** A Contributor License Agreement (CLA) is a legal agreement between you and
dbt Labs about the code that you send them. dbt Labs uses the "Individual Contributor License
Agreement v1.0", which is based on the Apache Software Foundation's Individual CLA. When you
sign it:

- You give dbt Labs, and everyone who gets software from dbt Labs, a permanent, worldwide,
  free license to use, copy, change and share your contributions (section 2), and a license
  for any of your patents that the contributions use (section 3).
- You state that the contributions are your own work and that you are allowed to give this
  license (sections 4 and 5).
- You keep the copyright. You can still use your own code for anything else.
- It covers your present and future contributions to dbt Labs.

**Why you need it.** dbt Labs merges code only from contributors with a signed CLA. On every
pull request, `cla-bot` checks the author. Without a CLA it writes "CLA has not been signed by
users: @…", and the PR gets no `cla:yes` label. Since June 2026, no community PR without that
label got the CI label, so in practice there is no CI and no review. Two examples: Exasol
#15322 spent 28 of its 65 days waiting for the CLA, and Trino PR #15345 has had no human review
since June 2026; its CLA was never signed.

**Who signs.** You, as a private person, for the GitHub account `abhishekguha996-ux`. The form
says that all your contributions must come from this account. You told us that no employer has
rights to this work, so the Individual CLA is the only one you need, and you do not need the
Corporate CLA. (Section 4: if an employer had such rights, you would need its permission, a
waiver, or a Corporate CLA signed by the employer.)

**When.** Now, before you post in Slack or open an issue or a PR, so that the signature is on
file before your first PR.

**Where.** The form is a Google Form:
<https://docs.google.com/forms/d/e/1FAIpQLScfOV7K4enYRHozrDRP6BBIXjOij-JDGca6WBTHyP_ANXSqlg/viewform>.
It is the same form that `cla-bot` links on a PR. The explanation is on
<https://docs.getdbt.com/community/resources/contributor-license-agreements>.

**How.**

1. Open the form and read the whole text. The form asks you to keep a copy, so save the page
   (for example, print it to PDF).
2. Fill in the five required fields:

   | Field | What to enter |
   |---|---|
   | Full Name | Your full legal name |
   | Email Address | Your email address; the one that your commits use is a good choice |
   | GitHub Account Name | `abhishekguha996-ux` |
   | Mailing Address, Including Country | Your postal address, with the country |
   | Confirmation | `I AGREE` (type exactly these words) |

3. Press **Submit**. Write down the date.

**After you sign.**

- On your first PR, `cla-bot` checks again. When dbt Labs has your signature, the PR gets the
  label `cla:yes` and the check `verification/cla-signed` passes.
- If `cla-bot` still reports a missing CLA after some days, answer in the PR, for example "I
  signed the Individual CLA on <date> as abhishekguha996-ux". The bot's own message asks you to
  do this.
- The `Co-Authored-By: Claude …` trailer in the commits is not a problem: Athena PR #16365 has
  the same kind of trailer and the label `cla:yes`.
- If the facts change (for example, an employer later claims rights to this work), section 8
  asks you to tell dbt Labs.
- Write "I've signed the CLA" in Slack or in a PR only after you press Submit.

## How contributions reach dbt v2

- **Guides:** [Contribute adapters to dbt v2](https://docs.getdbt.com/docs/contribute-dbt-adapters-v2)
  and the [adapter creation guide](https://docs.getdbt.com/guides/adapter-creation-v2).
  - Community contributors own **Phase 1**: connect, run macros, and materialize tables, views,
    incremental models and snapshots.
  - Phase 2, SQL static analysis, is led by dbt Labs. For Trino it has not started. dbt Labs
    tracks 11 "[Trino] Add typechecking support" issues (#14657–#14708) under epic #15104, which
    says "Trino is not yet a supported dbt adapter". A docs workflow created them
    automatically; nobody is assigned, and #14666 was closed by an unrelated commit.
  - **Acceptance bar.** The two pages differ. The contribute page asks for table, view,
    incremental and snapshot, and "a clean `dbt build` on jaffle-shop-classic". The creation
    guide asks for table, view, incremental and seed, with jaffle-shop as "one example".
    `acceptance/run_jaffle_shop.sh` covers table, view, incremental, snapshot and seeds.
  - A **user setup guide** that names the exact driver library is required. Write it after the
    adapter is in a dbt release. The draft ([docs-site/trino-setup.md](docs-site/trino-setup.md))
    is a v2 section for the existing Starburst-maintained page, not a new page.
- **The CLA comes first** (see above).
- **How a PR is merged:**
  - A maintainer adds the label `ci:approve-public-fork-ci`. Since June 2026, Felipe Oliveira
    Carvalho (`felipecrv`) added nearly all of these labels.
  - Copybara then copies the PR into dbt Labs' private repo, where CI and the review run.
  - The public PR ends as **Closed, not Merged**. The landed commit is authored by
    `fa-assistant`, with you as `Co-authored-by`.
  - Every push removes the CI label, so batch your fixes into fewer pushes.
  - Don't open drafts: drafts aren't synced.
  - Rebase quickly if the bot sets `review-status: sync-failed`.
- **Required on every PR:**
  - an issue link (the template says PRs "without an associated issue will not be merged")
  - a `changie` entry, made with `changie new`
  - Product/DX sign-off for interface changes (new configs and macros count)
- **People:**
  - Felipe Oliveira Carvalho (`felipecrv`): reviews community adapter PRs and applies the CI
    label. In a sample of 30 adapter PRs, every maintainer review was by `felipecrv`.
  - Hope Watson (`hope-wat`): the contact that the adapter guide names for
    `#adapter-ecosystem` on the dbt Slack and for CI coordination. Adds triage labels, not the
    CI label.
  - `dataders`: adapter DevRel. Invited a community Trino adapter on #13131 (2 June 2026).
    Opened the public ClickHouse "Part" issues, which mirror dbt Labs' own internal work, so
    they are not a community PR series to copy.
- **Channels:** `#adapter-ecosystem` before you start; `#proj-isv-adapters-in-fusion` when a PR
  is ready for review (the contribute page asks for this).
- **Timing so far:**
  - ClickHouse PRs from ClickHouse Inc. engineers closed in 0–6 days (August and September
    2026). A batch of four from July took 28–32 days. A non-vendor ClickHouse PR (#15733) has
    had no review for 66 days.
  - Exasol #15322 (one PR, 50 files) took 65 days: 28 days waiting for the CLA, a first
    maintainer action on day 46, and two `sync-failed` rebases. It built on an existing Phase 1
    Exasol adapter, so it is a weaker precedent for a new adapter in one PR.
  - Athena: ten parts have waited 8–23 days with no maintainer review. The last maintainer
    review on a community adapter PR was on 8 September 2026.
- **What stalls a PR:** an unsigned CLA, an adapter outside dbt Labs' current focus,
  platform-specific code in generic crates, competing or unsequenced PRs, and no Slack
  coordination.
- **Landscape:** no other public Trino adapter for dbt v2 exists. dbt Labs invited one on
  #13131. In June 2026 dataders said that Starburst was building an ADBC driver; there is no
  public sign of it, and starburstdata/dbt-trino#539 ("dbt v2 support", 29 September 2026) has
  no reply.

## The PR series

Each part is one commit. Together they change only `crates/` and `.changes/`. `contrib/` and
`.github/` are fork-only and never go upstream.

| Part | Branch | Commit subject | Needs first |
|---|---|---|---|
| 0 | `trino/p0-redact-access-token` | `fix(adbc): redact accessToken URI parameters in Builder Debug output` | — |
| 1 | `trino/p1-profile-auth` | `feat(trino): profile schema and ADBC authentication` | — |
| 2 | `trino/p2-types-relations` | `feat(trino): relations, columns, SQL types and literals` | — |
| 3a | `trino/p3a-generic-metadata-adapter` | `refactor(adapter): share the Exasol metadata adapter as GenericMetadataAdapter` | — |
| 3b | `trino/p3b-metadata` | `feat(trino): metadata adapter, relation listing and get_relation` | 3a |
| 4 | `trino/p4-macros-materializations` | `feat(trino): dbt-trino macro package, materializations and model configs` | 2 |
| 5 | `trino/p5-init-wizard` | `feat(trino): dbt init profile wizard` | 1 |

"Needs first" lists the symbols that a part uses from another part (analysis of 3 October,
before the review fixes). Re-check it when the fixes have landed: build each part alone on
`main`. A useful adapter needs all parts; Part 0 is defense in depth for Part 1's JWT.

## PR shape options

Ask the maintainers before you open PRs. Copybara mirrors the whole diff of a PR against
`main`, so a PR that is stacked on another PR also carries that PR's commits.

**Option A: parts based on `main`, with a merge plan (the Athena pattern).** Athena's umbrella
issue #16252 holds a merge-plan table and says "Every part is based on `main`". Each part is a
PR against `main` that compiles alone. A part that needs another part waits until that part
has landed, or includes its commit and says "review only the last commit". Small PRs are
easier to review, but you rebase more, and many open PRs compete for one reviewer. Keep at most
two open at a time. The merge plan for the umbrella issue:

| Order | PR | Part | Needs first | State against `main` |
|---|---|---|---|---|
| 1 | #… | Part 0: redact `accessToken` in Builder debug output | | |
| 2 | #… | Part 1: profile schema and ADBC authentication | | |
| 3 | #… | Part 2: relations, columns, SQL types and literals | | |
| 4 | #… | Part 3a: share the Exasol metadata adapter as GenericMetadataAdapter | | |
| 5 | #… | Part 3b: metadata adapter, relation listing and get_relation | Part 3a | |
| 6 | #… | Part 4: dbt-trino macro package, materializations and model configs | Part 2 | |
| 7 | #… | Part 5: `dbt init` profile wizard | Part 1 | |

**Option B: one PR (the Exasol pattern).** All seven commits in one PR from one branch, with
one review and one Copybara sync. Exasol #15322 landed this way, but it was an extension of an
existing adapter, and it still took 65 days.

**Recommendation.** Propose Option A in Slack and in the umbrella issue, and offer Option B if
`felipecrv` prefers one review. Do not open a strict stack: with Copybara, every later PR would
carry all earlier parts.

## How to open a PR from the fork

Your plan (clone, make a branch, port the code, open a PR) is right, with these details:

- You cannot push to dbt-labs/dbt. A PR comes from a branch in your fork,
  `abhishekguha996-ux/dbt-trino-v2`, which is already a GitHub fork of dbt-labs/dbt. The clone
  in `~/dbttrinoadapter/upstream/dbt` has `origin` = your fork and `upstream` = dbt-labs/dbt.
  A fresh clone works too.
- Base every branch on the latest dbt-labs `main`, and port only `crates/` and `.changes/`.
- Run the same gates as dbt Labs' CI before you push.

```sh
git fetch upstream
git switch -c trino/p1-profile-auth upstream/main
git cherry-pick <reviewed Part 1 commit>
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo nextest run --workspace
git push origin trino/p1-profile-auth
gh pr create -R dbt-labs/dbt --base main --head abhishekguha996-ux:trino/p1-profile-auth \
  --title "feat(trino): profile schema and ADBC authentication" --body-file pr-part1.md
```

For one PR (Option B), cherry-pick all seven commits onto one branch. For the live Linux
evidence, push the same commits to a `trino-ready/…` branch of the fork: the fork workflow
then runs the functional suite and the jaffle-shop build with the Linux binary.

## Coordination with #15345

#15345 ("feat: release of trino inline udfs support", by `helloitu`, open since 24 June 2026)
is the only other open Trino PR. It adds Trino inline UDFs (issue #15344); it is not an
adapter. It overlaps this series: it adds `dbt_macro_assets/dbt-trino/dbt_project.yml`
(Part 4 adds the same file) and changes `TrinoDbConfig` and `adapter_factory.rs` (Part 1) and
`relation/factory.rs` (Part 2). It has stalled for two reasons: its CLA was never signed
(`cla-bot` asked four times), and on #15344 dbt Labs replied that inline UDFs "will need more
discussion" for all adapters.

- Name #15345 in the Slack message and in the umbrella issue: this series does not include
  inline UDFs, and whichever PR lands second rebases.
- Do not copy code from #15345. Its author has not signed the CLA, and the ICLA covers only your
  own work (sections 5 and 7).
- Do not comment on #15345 unless a maintainer asks you to.

## Slack message

Post it in `#adapter-ecosystem` and tag Hope Watson. Send it only after you have signed the CLA
and filed the driver issues.

> Hi @Hope Watson — I've built a Phase 1 Trino adapter for dbt v2 on the adbc-drivers/trino
> driver (go/v0.5.3), following the adapter guide. jaffle-shop-classic plus an incremental
> model and a snapshot builds clean on Trino 483 with Iceberg and Delta Lake, and on Hive (no
> snapshot, since Hive can't MERGE). It keeps the dbt-trino v1 profile fields and vendors the
> dbt-trino v1.10.5 macros (unchanged in v1.10.6). Code and evidence:
> https://github.com/abhishekguha996-ux/dbt-trino-v2 (contrib/trino-lab). I've signed the CLA.
> Before I open PRs for #13131, two questions: (1) is anyone at dbt Labs or Starburst already
> working on a Trino adapter or ADBC driver for v2? (2) Do you prefer parts based on main with a
> merge plan, like Athena (#16252), or one PR, like Exasol (#15322)? The only open Trino PR,
> #15345 (inline UDFs), touches four of the same files; my series does not include inline UDFs.
> I can also hand over a Docker-based Trino test stack for your CI.

## Umbrella issue

Title: `[Trino] Phase 1 adapter for dbt v2: merge plan`

> Tracks the Phase 1 Trino adapter for dbt v2, built on the Apache-2.0
> [adbc-drivers/trino](https://github.com/adbc-drivers/trino) driver and loaded by name
> (`adbc_driver_trino`), as community adapters require. Related: #13131. Overlaps #15345
> (inline UDFs, not part of this work).
>
> **Merge plan:** (the Option A table from UPSTREAM.md, with the PR numbers)
>
> **Evidence:** jaffle-shop-classic (+incremental, +snapshot) builds clean on Trino 483
> (Iceberg, Delta Lake, Hive on S3), plus a functional suite of about 100 tests, all
> reproducible from
> https://github.com/abhishekguha996-ux/dbt-trino-v2/tree/trino-v2-adapter/contrib/trino-lab.
> The fork's CI runs both with the Linux x86_64 release binary.
>
> **Questions for dbt Labs:** the PR shape; Product/DX approval for the six model config keys
> (`properties`, `on_table_exists`, `view_security`, `views_enabled`, `sync_nested_columns`,
> `grace_period`) and `adapter.diff_nested_column_types` before Part 4; whether Part 0 (a
> redaction entry in `dbt-adbc`) is welcome; whether `AdapterType::Starburst` should use the
> Trino implementation; how to hand over a Trino target for your CI.
>
> **Known driver limits** (adbc-drivers/trino#…, #…): cancel does not stop a running query;
> no mTLS, OAuth 2.0, impersonation, custom HTTP headers or Kerberos ticket cache.

Put the real issue numbers into the last paragraph. Until the driver issues are filed, write
"to be reported to adbc-drivers/trino" instead.

## PR descriptions

Every PR uses the repository template: first line `Resolves #<umbrella issue>`, then
Problem, Solution and the checklist. Add "Related: #13131". Do not write "Resolves #13131":
that issue is "Release Starburst Trino support", and `AdapterType::Starburst` stays
`todo!()`. Each part has one `changie` entry (`--custom project=dbt-core --custom issue=13131
--custom author=abhishekguha996-ux`): "Under the Hood" for Parts 0 and 3a, "Features" for the
others.

### Part 0 — `fix(adbc): redact accessToken URI parameters in Builder Debug output`

**Problem:** Drivers based on trino-go-client, such as adbc-drivers/trino, accept a bearer
token only as the URI query parameter `accessToken`. The `Debug` impl of `database::Builder`
redacts the `user`, `username` and `password` query parameters, but not `accessToken`. No
production code prints this output today, so this is defense in depth: a future debug log
would show the JWT.

**Solution:** Add `accessToken` to the redacted query keys. No new methods or traits. One unit
test, on a `Backend::Generic` builder (the backend that carries the JWT). If you prefer no
change in `dbt-adbc`, I'll drop this part.

### Part 1 — `feat(trino): profile schema and ADBC authentication`

**Problem:** `AdapterType::Trino` exists, but `backend_of` is `todo!("Trino")`,
`TrinoDbConfig` has six fields, and there is no Trino auth, so any Trino profile panics.

**Solution:**
- `TrinoDbConfig` accepts the dbt-trino v1 credential fields (`catalog` aliases `database`),
  so existing profiles load unchanged. This includes the `starburst_*` fields of dbt-trino
  1.10.3+; `starburst_secret_key` is never serialized.
- `dbt-auth/src/trino` follows the crate's pattern: `parse_auth` builds a `TrinoAuthIR`
  (`None`, `Ldap`, `Jwt`, `Kerberos`), which `apply` and `apply_connection_args` turn into
  trino-go-client v0.333.0 DSN options, wired with `auth_configure_pipeline!` like the Exasol
  and ClickHouse modules:
  - methods `none`, `ldap`, `jwt` and `kerberos` (keytab)
  - `roles`, `session_properties`, `client_tags`, `timezone`, `query_timeout` (seconds or a
    duration)
  - `cert`: a CA bundle, `true`, or `false` (the driver's `SSLVerification=NONE`)
  - `X-Trino-Source: dbt-trino-<version>`, so resource-group selectors keep matching
- Clear configuration errors for: a `host` with a scheme, port or path; an invalid
  `query_timeout`; the methods the driver can't perform (`certificate`, `oauth`,
  `oauth_console`, `gssapi`); `http_headers`, `impersonation_user`, `starburst_url`; Kerberos
  options other than their v1 defaults; and `role` (the message points to `roles`).
- `backend_of(Trino)` is `Backend::Generic { library_name: "adbc_driver_trino" }`. The driver is
  loaded by name, with no CDN, as the contribute page describes for community adapters. No
  `dbt-adbc` change.

**Notes for review:**
- TLS: without `cert`, v2 verifies the server certificate. dbt-trino v1 verifies only when
  `require_certificate_validation` is on (default False). This is deliberate and documented.
- The `cert: false` and `retries` warnings go to the `AuthWarningPrinter`. dbt builds auth with
  `NoopAuthWarningPrinter` today, so they are not shown; this shared gap is not changed here.
- `prepared_statements_enabled` maps to `explicitPrepare`. It has no visible effect, because
  dbt v2 renders bindings as SQL literals.
- `timezone` is sent, but trino-go-client reads it only from v0.336.0 on. Driver go/v0.5.3 pins
  v0.333.0; the driver's `main` branch already uses v0.336.0.
- The accessors follow `crates/dbt-auth/AGENTS.md`: secrets use `get_string`, so a YAML number
  is accepted, as in the Exasol and ClickHouse modules.

**Tests:** unit tests for every method and option (the DSN is byte-identical to the
pre-refactor output for every earlier test input), host, port and `query_timeout` validation,
Kerberos options and `krb5_config` precedence, secret handling and warnings; a `profiles.rs`
parse test. Live-tested over HTTPS with a password (also one with URL-special characters), a
JWT, a CA bundle and `cert: false`.

### Part 2 — `feat(trino): relations, columns, SQL types and literals`

**Problem:** The parse and compile paths hit `todo!("Trino")` in the relation factory, column
builder, SQL type metadata key, seed column naming and the microbatch event-time filter.

**Solution:**
- Relations use the generic `RelationStatic` path. Trino stores catalog, schema and table
  names in lowercase, even when they are quoted, so Trino relation identity (`semantic_fqn`
  and the resolved names used for matching) is lowercase, as in v1's `_is_exactish_match`.
  Rendering keeps the user's text.
- Columns use the shared builder: Exasol's `build_exasol`, renamed `build_standard`. Exasol's
  behavior is unchanged.
- Trino types round-trip: `ROW`, `ARRAY(...)`, `MAP(...)`, `VARBINARY`, `DECIMAL`, and `UInt64`
  → `DECIMAL(20, 0)`. `TrinoColumn` type labels and predicates, and `from_description` keeps
  nested types verbatim (v1 `column.py`).
- Unit-test fixtures keep their types. The driver reports only base type names (`DECIMAL`,
  `VARCHAR`), so the full type is rebuilt from the driver's precision, scale and length
  metadata: a `decimal(10,2)` input stays `DECIMAL(10, 2)`, so 12.34 stays 12.34. Timestamp
  literals use a space separator, and `timestamp with time zone` fixtures work. This follows
  the per-adapter fixture typing of 68ad837 (BigQuery) and c157a08 (DuckDB).
- `uuid` values no longer panic dbt. The driver returns them as the `arrow.uuid` extension
  type (16 bytes); `dbt-agate` now shows them as canonical text and returns an error, not a
  panic, for other values that it cannot show as text. This shared change is safe for every
  adapter and has tests.
- Seeds get `DATE`/`TIMESTAMP` typed literals. The microbatch filter uses `TIMESTAMP '… UTC'`
  literals, in one arm shared with Exasol (v1 `relation.py`).

Each change links the v1 code that it mirrors.

### Part 3a — `refactor(adapter): share the Exasol metadata adapter as GenericMetadataAdapter`

No behavior change. It renames `ExasolMetadataAdapter` to `GenericMetadataAdapter`, following
the "`GenericFoo` + `match adapter_type`" rule in `.agents/adapters.md`, and moves DuckDB's
`information_schema` row conversion into a shared helper. Error messages keep the capitalized
adapter name. Exasol and DuckDB tests are unchanged.

### Part 3b — `feat(trino): metadata adapter, relation listing and get_relation`

Trino uses the generic metadata adapter. At startup it hydrates the relation cache: it lists
every schema in parallel from `<catalog>.information_schema.tables` (a MapReduce, as Fabric
does) and finds materialized views through `system.metadata.materialized_views`, as v1's
`trino__list_relations_without_caching` does. So `--defer` works without `--favor-state`, and
dbt sends one listing per schema instead of one per thread. The catalog, schema and table
literals in this SQL are lowercase whatever the quote policy, like v1's `| lower`. Exasol keeps
its empty hydration. Transactions are reported as unsupported (dbt-trino runs in autocommit),
and `list_schemas` reads `schema_name`. DuckDB's `get_relation` SQL is byte-identical.

**Tests:** listing SQL for mixed-case names, materialized-view rows, the transactions
feature, the `list_schemas` column and cache hydration.

### Part 4 — `feat(trino): dbt-trino macro package, materializations and model configs`

**Problem:** There's no Trino macro package, so nothing materializes.

**Solution:**
- **Vendored macros:** dbt-trino v1.10.5 (commit `6b097c4eb3cbdd5eb6a0bc0209796626aebf32c6`,
  Apache-2.0, "Copyright 2021 Starburst Data, Inc."; v1.10.6 has no macro changes). Provenance
  is in each file header and in `dbt_macro_assets/README.md`. Every v2 change is marked `v2:`
  and has a loader test. The main ones:
  - `information_schema('<view>')`, `%s` binding literals, escaping of interpolated literals,
    catalog SQL types, and renames qualified with catalog and schema
  - a private `trino_quoted_literal` macro instead of a `trino__string_literal` override, so
    `dbt.string_literal` keeps dbt's default behavior
  - a switch from a view to a table in `rename` and `skip` mode builds the new table first, so
    the old relation survives a failed build; `drop` and `replace` keep drop-first
  - `persist_docs` on a materialized view puts the comment into `CREATE MATERIALIZED VIEW …
    COMMENT`, because Trino has no `COMMENT ON MATERIALIZED VIEW`
  - `properties()`: a `catalog_name` gives a clear "not supported yet" error; without it,
    `storage_uri` sets `location` (v1 parity)
  - grants: the show-grants SQL lowercases names and leaves out the current user, so dbt never
    revokes its own privileges
  - `on_schema_change` keeps drop-before-add; a comment explains the Hive metastore trade-off
- **Config keys:** `properties`, `on_table_exists`, `view_security`, `views_enabled`,
  `sync_nested_columns` and `grace_period`, with dbt-trino's names (Exasol precedent). They are
  in `log_state_mod_diff` too.
- **Adapter behavior:**
  - constraint support (`not_null` enforced), taken from v1 `CONSTRAINT_SUPPORT`
  - grants use the standard parser
  - incremental strategies `append`, `merge`, `delete+insert` and `microbatch`, as in v1
  - a materialized-view full refresh uses `CREATE OR REPLACE MATERIALIZED VIEW`, so the old view
    stays if the new definition fails
  - seed types match v1 (`INTEGER`, `DOUBLE`, bare `TIMESTAMP`)
- **Nested ROW schema sync:** `adapter.diff_nested_column_types`, a generic struct diff in
  `dbt-adapter-sql`. New fields keep the source order, and a missing nested struct is added as
  one field. Trino matches `ROW` fields by position, so if the target field order would differ
  from the source, dbt stops with an error that asks for `--full-refresh` (v1 swaps the
  values silently).
- No shared `dbt-adapters` macros are changed.

**Interface changes** (need Product/DX approval): the six config keys and
`adapter.diff_nested_column_types`.

**Tests:** a loader test for every `v2:` change, and struct-diff tests in `dbt-adapter-sql`.

**Evidence:**
- jaffle-shop-classic (+incremental, +snapshot) builds clean on Iceberg, Delta Lake and Hive on S3.
  As for every v2 adapter, the project needs dbt-autofix's YAML changes; Delta models also need
  `on_table_exists: replace`, and Hive has no snapshot (no `MERGE`). The patch is in
  `contrib/trino-lab/acceptance`.
- The functional suite passes on Memory, Hive, Iceberg and Delta Lake (see TEST-RESULTS.md).
- The retail and TPC-H projects match Python oracles.

### Part 5 — `feat(trino): dbt init profile wizard`

`dbt init` now offers Trino: it is in `ProfileSetup::get_available_adapters()` and in the
headless API (`supported_adapters`, `adapter_fields`, `build_profile_target`). The wizard asks
for the host, the method (`none`, `ldap`, `jwt`, `kerberos`), the port, the user (optional for
`jwt`), then a password, a JWT or a keytab and principal depending on the method, an optional
CA bundle for HTTPS, and the catalog and schema. `http_scheme` follows the method (`http` for
`none`, `https` otherwise, as in v1), and editing an existing profile pre-selects its method.

**Tests:** headless profile setup for each method, and Trino in the adapter list.

## Maintainer decisions to expect

1. **Driver distribution and name:** a community driver is loaded by name, with no CDN, and
   the setup guide documents this. `dbc install trino` writes a manifest named `trino`, which
   dbt does not find (see [INSTALL.md](INSTALL.md#drivers-installed-with-dbc)). Ask whether dbt
   should also try that name. A Starburst driver may change the picture later.
2. **Part 0 touches `dbt-adbc`.** It's a redaction list entry, not a method, but be ready to
   drop it.
3. **Interface changes** (config keys, `diff_nested_column_types`) need Product/DX approval.
   Ask in the umbrella issue before Part 4.
4. **Microbatch concurrency:** Trino stays out of `MICROBATCH_SUPPORTED_ADAPTERS`, because
   concurrent batches conflict in Iceberg and Delta Lake commits.
5. **`AdapterType::Starburst`** stays `todo!()`. Ask whether it should share the Trino
   implementation.
6. **CI handoff:** dbt Labs' CI needs a Trino. Offer the Docker stack in `contrib/trino-lab/stack`
   (no cloud credentials). It uses Starburst's proprietary Hive metastore image, as dbt-trino
   v1's CI does; dbt Labs may want an Apache image.

## Changes to this kit after the 3 October review

- The driver limits are "to be reported" until the issues in DRIVER-ISSUES.md are filed.
- The ClickHouse "Parts 0–8" were dbt Labs' internal work; the PR shape choices are Athena
  #16252 and Exasol #15322.
- `felipecrv`, not Hope Watson, applies the CI label.
- The Athena parts are based on `main`; they are not a strict stack.
- #15345 is an inline-UDF PR, stalled by its CLA and by a product reply.
- The Trino typecheck issues were created automatically and nobody works on them.
- The Exasol precedent spent 28 of its 65 days waiting for the CLA.
- The cancel analysis is corrected: the driver runs the query with `context.Background()`, so
  `AdbcStatementCancel` cannot stop it (checked with a driver-only repro).
