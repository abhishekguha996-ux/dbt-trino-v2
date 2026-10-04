# Contributing the Trino adapter to dbt-labs/dbt

Nothing in this fork has been submitted to dbt-labs/dbt. This is the kit for when you decide
to. The local clone's `upstream` remote has its push URL disabled on purpose. Facts in this
file were checked on 3 and 4 October 2026.

Before the first PR, in this order:

1. Sign the [Individual CLA](#individual-cla).
2. Finish the review fixes in the nine parts, rebuild the parts on the latest dbt-labs `main`,
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

**Code that is not your own (sections 5 and 7).** In section 5 you state that each
contribution is your original creation, and that your submission gives the details of any
third-party license or restriction that you know of. Section 7 covers work that is not your
own. You may submit it separately from your own contributions. You must give the complete
details of its source and license, and mark it conspicuously as "Submitted on behalf of a
third-party: [named here]". Part 4 vendors the dbt-trino v1.10.5 macros, which are Starburst's
work. So the Part 4 PR text (see [PR descriptions](#pr-descriptions)) and the
[umbrella issue](#umbrella-issue) carry this marking, and they say that only the changes marked
`v2:` are your own work. If dbt Labs wants the vendored files in a separate submission, offer
them as a separate commit or PR.

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

| Part | Branch | Commit | Commit subject | Needs first |
|---|---|---|---|---|
| 0 | `trino-pr/p0` | `<sha>` | `fix(adbc): redact accessToken URI parameters in Builder Debug output` | — |
| S1 | `trino-pr/s1` | `<sha>` | `fix(dbt-agate): show arrow.uuid columns as text instead of panicking` | — |
| S2 | `trino-pr/s2` | `<sha>` | `fix(dbt-tasks-sa): compare unit-test values of Arrow types without a formatting arm` | — |
| 1 | `trino-pr/p1` | `<sha>` | `feat(trino): profile schema and ADBC authentication` | — |
| 2 | `trino-pr/p2` | `<sha>` | `feat(trino): relations, columns, SQL types and literals` | 1 |
| 3a | `trino-pr/p3a` | `<sha>` | `refactor(adapter): share the Exasol metadata adapter as GenericMetadataAdapter` | — |
| 3b | `trino-pr/p3b` | `<sha>` | `feat(trino): metadata adapter, relation listing and get_relation` | 1, 3a |
| 4 | `trino-pr/p4` | `<sha>` | `feat(trino): dbt-trino macro package, materializations and model configs` | 1, 2 |
| 5 | `trino-pr/p5` | `<sha>` | `feat(trino): dbt init profile wizard` | 1 |

Each `trino-pr/<part>` branch starts at `upstream/main` (`<sha>`) and holds the part's commit,
after the commits of the parts in its "Needs first" column. `trino-pr/series` holds all parts in
this order, and `trino-pr/integration` adds the fork-only `contrib/` and `.github/` commits. The
`trino/p*` branches, locally and on the fork, hold the series from before the review fixes: do
not open PRs from them.

S1 and S2 fix bugs in code that every adapter uses. They use no Trino code, so they go upstream
as small "Fixes" PRs of their own, each with cross-adapter tests. Part 2 needs them at run
time: S1 to show uuid values as text, and S2 to compare Trino `decimal` and `timestamp(3)`
values in unit tests.

"Needs first" lists the parts that must be on `main` first, or that the PR must include (see
Option A). On `main`, `backend_of(Trino)` is `todo!("Trino")`, so the Trino code of Parts 2,
3b, 4 and 5 runs only with Part 1: the tests of Parts 3b and 4 build a Trino engine or adapter,
and Part 5 fills the profile fields that Part 1 adds. Part 3b builds on Part 3a's
`GenericMetadataAdapter`, and Part 4 on the Trino types and relations of Part 2. Before you
open a PR, apply the part alone, with the parts it needs, to the latest `main` and run the
tests of the crates it changes. A useful adapter needs all parts; Part 0 is defense in depth
for Part 1's JWT.

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
| 2 | #… | S1: show `arrow.uuid` columns as text instead of panicking (all adapters) | | |
| 3 | #… | S2: compare unit-test values of Arrow types without a formatting arm (all adapters) | | |
| 4 | #… | Part 1: profile schema and ADBC authentication | | |
| 5 | #… | Part 2: relations, columns, SQL types and literals | Part 1 | |
| 6 | #… | Part 3a: share the Exasol metadata adapter as GenericMetadataAdapter | | |
| 7 | #… | Part 3b: metadata adapter, relation listing and get_relation | Parts 1 and 3a | |
| 8 | #… | Part 4: dbt-trino macro package, materializations and model configs | Parts 1 and 2 | |
| 9 | #… | Part 5: `dbt init` profile wizard | Part 1 | |

**Option B: one PR (the Exasol pattern).** Parts 0 to 5 in one PR from one branch, with one
review and one Copybara sync. Exasol #15322 landed this way, but it was an extension of an
existing adapter, and it still took 65 days.

**S1 and S2 are separate PRs in both options.** They are small, they fix code that every
adapter uses, and they need no other part. `trino-pr/series` holds them too: rebase it on
`main` after they have landed, before you use it for Option B.

**Recommendation.** Propose Option A in Slack and in the umbrella issue, and offer Option B if
`felipecrv` prefers one review. Do not open a strict stack: with Copybara, every later PR would
carry all earlier parts.

## How to open a PR from the fork

Your plan (clone, make a branch, port the code, open a PR) is right, with these details:

- You cannot push to dbt-labs/dbt. A PR comes from a branch in your fork,
  `abhishekguha996-ux/dbt-trino-v2`, which is already a GitHub fork of dbt-labs/dbt. The clone
  in `~/dbttrinoadapter/upstream/dbt` has `origin` = your fork and `upstream` = dbt-labs/dbt.
  A fresh clone works too.
- Open each PR from its `trino-pr/<part>` branch (see [The PR series](#the-pr-series)). These
  branches change only `crates/` and `.changes/`. Rebase the branch on the latest dbt-labs
  `main` first.
- Run the same gates as dbt Labs' CI before you push.

```sh
git fetch upstream
git switch trino-pr/p1
git rebase upstream/main          # if main has moved since the branch was made
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo nextest run --workspace
git push origin trino-pr/p1       # after a rebase of a pushed branch: add --force-with-lease
gh pr create -R dbt-labs/dbt --base main --head abhishekguha996-ux:trino-pr/p1 \
  --title "feat(trino): profile schema and ADBC authentication" --body-file pr-part1.md
```

For one PR (Option B), use `trino-pr/series` in the same way. For the live Linux evidence,
push `trino-pr/integration` (the series plus the fork-only `contrib/` and `.github/` commits)
to the fork: the fork workflow then runs the Rust checks, the functional suite and the
jaffle-shop build with the Linux binary. The other `trino-pr/` branches have no fork workflow,
so a push of them starts no run.

## Coordination with #15345

#15345 ("feat: release of trino inline udfs support", by `helloitu`, open since 24 June 2026)
is the only other open Trino PR. It adds Trino inline UDFs (issue #15344); it is not an
adapter. It changes seven files that this series also changes:

- Part 1: `crates/dbt-schemas/src/schemas/profiles.rs` (`TrinoDbConfig`) and
  `crates/dbt-adapter/src/adapter/adapter_factory.rs`
- Part 2: `crates/dbt-adapter/src/relation/factory.rs`
- S1 and Parts 3a, 3b and 4: `crates/dbt-adapter/src/adapter/adapter_impl.rs`
- Part 4: `crates/dbt-adapter/src/adapter/mod.rs`,
  `crates/dbt-schemas/src/schemas/project/configs/model_config.rs` and
  `crates/dbt-loader/src/dbt_macro_assets/dbt-trino/dbt_project.yml` (both add this file)

It has stalled for two reasons: its CLA was never signed (`cla-bot` asked four times), and on
#15344 dbt Labs replied that inline UDFs "will need more discussion" for all adapters.

- Name #15345 in the Slack message and in the umbrella issue: this series does not include
  inline UDFs, and whichever PR lands second rebases.
- Do not copy code from #15345. It is not your own work (section 5), and its author has not
  signed the CLA. Third-party code needs the section 7 marking (see
  [Individual CLA](#individual-cla)).
- Do not comment on #15345 unless a maintainer asks you to.

## Slack message

Post it in `#adapter-ecosystem` and tag Hope Watson. Send it only after you have signed the CLA
and filed the driver issues.

> Hi @Hope Watson — I've built a Phase 1 Trino adapter for dbt v2 on the adbc-drivers/trino
> driver (go/v0.5.3), following the adapter guide. jaffle-shop-classic plus an incremental
> model and a snapshot builds clean on Trino 483 with Iceberg and Delta Lake, and on Hive (no
> snapshot, since Hive can't MERGE). It keeps the dbt-trino v1 profile fields and vendors the
> dbt-trino v1.10.5 macros (unchanged in v1.10.6). Code and evidence:
> https://github.com/abhishekguha996-ux/dbt-trino-v2/tree/trino-pr/integration/contrib/trino-lab.
> I've signed the CLA. Before I open PRs for #13131, two questions: (1) is anyone at dbt Labs or
> Starburst already working on a Trino adapter or ADBC driver for v2? (2) Do you prefer parts
> based on main with a merge plan, like Athena (#16252), or one PR, like Exasol (#15322)? The
> only open Trino PR, #15345 (inline UDFs), touches seven of the same files; my series does not
> include inline UDFs. I can also hand over a Docker-based Trino test stack for your CI.

## Umbrella issue

Title: `[Trino] Phase 1 adapter for dbt v2: merge plan`

> Tracks the Phase 1 Trino adapter for dbt v2, built on the Apache-2.0
> [adbc-drivers/trino](https://github.com/adbc-drivers/trino) driver and loaded by name
> (`adbc_driver_trino`), as community adapters require. Related: #13131. Overlaps #15345
> (inline UDFs, not part of this work).
>
> **Merge plan:** (the Option A table from UPSTREAM.md, with the PR numbers)
>
> **Submitted on behalf of a third-party: Starburst Data, Inc. (dbt-trino v1.10.5, commit
> 6b097c4eb3cbdd5eb6a0bc0209796626aebf32c6, Apache-2.0).** This covers
> `crates/dbt-loader/src/dbt_macro_assets/dbt-trino/**`; only the changes marked `v2:` are my own
> work.
>
> **Evidence:** jaffle-shop-classic (+incremental, +snapshot) builds clean on Trino 483
> (Iceberg, Delta Lake, Hive on S3), plus a functional suite of about 100 tests, all
> reproducible from
> https://github.com/abhishekguha996-ux/dbt-trino-v2/tree/trino-pr/integration/contrib/trino-lab.
> The fork's CI runs both with the Linux x86_64 release binary.
>
> **Questions for dbt Labs:** the PR shape; Product/DX approval for the six model config keys
> (`properties`, `on_table_exists`, `view_security`, `views_enabled`, `sync_nested_columns`,
> `grace_period`) and `adapter.diff_nested_column_types` before Part 4; whether Part 0 (a
> redaction entry in `dbt-adbc`) is welcome; whether `AdapterType::Starburst` should use the
> Trino implementation; how to hand over a Trino target for your CI.
>
> **Known driver limits** (adbc-drivers/trino#…, #…): cancel does not stop a running query;
> go/v0.5.3 ignores `timezone`, so the session uses the server's time zone; no mTLS, OAuth
> 2.0, impersonation, custom HTTP headers or Kerberos ticket cache.

Put the real issue numbers into the last paragraph. Until the driver issues are filed, write
"to be reported to adbc-drivers/trino" instead.

## PR descriptions

Every PR uses the repository template: first line `Resolves #<umbrella issue>`, then
Problem, Solution and the checklist. Add "Related: #13131". Do not write "Resolves #13131":
that issue is "Release Starburst Trino support", and `AdapterType::Starburst` stays
`todo!()`. S1 and S2 fix bugs for every adapter: open a bug issue for each, start the PR with
`Resolves #<that issue>`, and add "Related: #<umbrella issue>".

Each part has one `changie` entry: "Fixes" for S1 and S2 (without the `[Trino]` prefix),
"Under the Hood" for Parts 0 and 3a, "Features" for the others. To make an entry again, run
this from the repository root:

```sh
changie new --kind "<kind>" --body "<text>" --custom issue=13131 \
  --custom author=abhishekguha996-ux --interactive=false
```

Do not pass `--custom project=dbt-core`: changie rejects it, because `.changie.yaml` adds
`project: dbt-core` itself (the example in `AGENTS.md` still passes it). The S1 and S2 entries
name issue 13131; when their bug issues exist, set `issue` in each entry to its bug issue.

### Part 0 — `fix(adbc): redact accessToken URI parameters in Builder Debug output`

**Problem:** Drivers based on trino-go-client, such as adbc-drivers/trino, accept a bearer
token only as the URI query parameter `accessToken`. The `Debug` impl of `database::Builder`
redacts the `user`, `username` and `password` query parameters, but not `accessToken`. No
production code prints this output today, so this is defense in depth: a future debug log
would show the JWT.

**Solution:** Add `accessToken` to the redacted query keys. No new methods or traits. One unit
test, on a `Backend::Generic` builder (the backend that carries the JWT). If you prefer no
change in `dbt-adbc`, I'll drop this part.

### S1 — `fix(dbt-agate): show arrow.uuid columns as text instead of panicking`

**Problem:** A query result with a uuid column crashes dbt. Drivers return a uuid as
`FixedSizeBinary(16)` with the canonical `arrow.uuid` extension type; adbc-drivers/trino does
this for Trino's `uuid`. Agate has no uuid type. The conversion to Agate cannot cast the column
to text, and `AgateTable::new` unwraps that error, so `run_query`, enforced contracts and unit
tests panic.

**Solution:**
- Agate shows `arrow.uuid` columns as canonical text, for example
  `12151fd2-7586-11e9-8f9e-2a86e4085a59`, as dbt v1 does. The original Arrow batch keeps the
  `FixedSizeBinary(16)` column.
- `AgateTable::try_new` returns an error instead of a panic when a column cannot be shown as
  text. The query path in `AdapterImpl` uses it, so such a column fails the query with an
  error.
- A `FixedSizeBinary(16)` column without the extension is not treated as a uuid.

**Behavior change for all adapters:** an `arrow.uuid` column shows as text instead of crashing
dbt. A query result that Agate cannot show as text fails with an error instead of a panic.

**Known limit:** `dbt show` prints the Arrow record batch, not an Agate table, so it still shows
a uuid as 32 hex digits (the Arrow display of `FixedSizeBinary(16)`). `run_query`, contracts
and unit tests show the canonical text.

**Tests:** an `arrow.uuid` column becomes canonical text (a null stays null); a
`FixedSizeBinary(16)` column without the extension is not changed; a column that cannot be
text gives an error, not a panic.

### S2 — `fix(dbt-tasks-sa): compare unit-test values of Arrow types without a formatting arm`

**Problem:** A unit test compares the actual and expected rows by the text of each value
(`value_as_string` in `crates/dbt-tasks-sa/src/materialize.rs`). Only `Int32`, `Int64`,
`Float32`, `Float64`, `Utf8`, `Boolean`, `Decimal128`, `Timestamp` in seconds or nanoseconds,
and `Date32` have a formatting arm. Every other Arrow type prints `[unsupported]` on both
sides, so the test never sees a difference in such a column, not even NULL against a value. I
found this with adbc-drivers/trino, which returns `decimal(10, 2)` as `Decimal64` and
`timestamp(3)` in milliseconds.

**Solution:** Every Arrow type without an arm compares by its Arrow display text
(`array_value_to_string`). Binary values show as UTF-8 text when they are valid UTF-8, and as
hex otherwise.

**Behavior change for all adapters:** unit tests now compare these columns, for example:
- microsecond timestamps: `TIMESTAMP` and `DATETIME` on BigQuery, Databricks, Postgres,
  Redshift and DuckDB
- millisecond timestamps, `Date64`, `Time32` and `Time64`
- `Int8`, `Int16` and unsigned integers; `Decimal32`, `Decimal64` and `Decimal256` (BigQuery
  `BIGNUMERIC`)
- dictionary and binary columns
- NULL against a value, in all of these columns

A unit test that passed only because both sides showed `[unsupported]` can now fail. The
changie entry says so.

**Tests:** cross-adapter cases for `Timestamp(µs, UTC)`, `Int16`, `Time64`, NULL against a
value and `BinaryView`, and for `Decimal64` and millisecond timestamps.

### Part 1 — `feat(trino): profile schema and ADBC authentication`

**Problem:** `AdapterType::Trino` exists, but `backend_of` is `todo!("Trino")`,
`TrinoDbConfig` has eight fields, and there is no Trino auth, so any Trino profile panics.

**Solution:**
- `TrinoDbConfig` accepts the dbt-trino v1 credential fields (`catalog` aliases `database`),
  including the `starburst_*` fields of dbt-trino 1.10.3+; `starburst_secret_key` is never
  serialized. v1 profiles load unchanged, except for the differences listed below.
- `dbt-auth/src/trino` follows the crate's pattern: `parse_auth` builds a `TrinoAuthIR`
  (`None`, `Ldap`, `Jwt`, `Kerberos`), which `apply` and `apply_connection_args` turn into
  trino-go-client v0.333.0 DSN options, wired with `auth_configure_pipeline!` like the Exasol
  and ClickHouse modules:
  - methods `none`, `ldap`, `jwt` and `kerberos` (keytab)
  - `roles`, `session_properties`, `client_tags`, `timezone` and `query_timeout`
  - `cert`: a CA bundle, `true`, or `false` (`SSLVerification=NONE`, which the ADBC driver
    reads itself)
  - `X-Trino-Source: dbt-trino-<version>`, so resource-group selectors keep matching
- `query_timeout` is not a v1 field. It takes a positive number of seconds (an integer, or a
  decimal string such as `"1.5"`) or a Go duration such as `30m`. Zero fails with its own
  message, because trino-go-client would cancel every query at once. Without the key, the
  driver stops a query after 10h (`trino.DefaultQueryTimeout`).
- Clear configuration errors for: a `host` with a scheme, port or path; an invalid
  `query_timeout`; the methods the driver can't perform (`certificate`, `oauth`,
  `oauth_console`, `gssapi`); `http_headers`, `impersonation_user` and `starburst_url` (an
  empty string or mapping counts as unset); Kerberos options other than their v1 defaults; and
  `role` (the message points to `roles`).
- `backend_of(Trino)` is `Backend::Generic { library_name: "adbc_driver_trino" }`. The driver is
  loaded by name, with no CDN, as the contribute page describes for community adapters. No
  `dbt-adbc` change.

**Differences from v1:**
- A URL host such as `https://trino.example.com:8443` is rejected with a message that asks for
  the separate keys. v1's trino-python-client accepts it and lets the URL's scheme and port
  override `http_scheme` and `port`.
- `cert` with `http_scheme: http` fails; v1 ignores it.
- TLS: without `cert`, v2 verifies the server certificate. v1 verifies only when
  `require_certificate_validation` is on (default False). This is deliberate and documented.
- `timezone` is sent, but trino-go-client reads it only from v0.336.0 on. Driver go/v0.5.3 pins
  v0.333.0, so the session keeps the server's time zone; the driver's `main` branch already
  uses v0.336.0.
- Without `query_timeout`, a query stops after 10h; v1 has no client-side query timeout.

**Notes for review:**
- The `cert: false` and `retries` warnings go to the `AuthWarningPrinter`. dbt builds auth with
  `NoopAuthWarningPrinter` today, so they are not shown; this shared gap is not changed here.
- `prepared_statements_enabled` maps to `explicitPrepare`. It has no visible effect, because
  dbt v2 renders bindings as SQL literals.
- dbt-auth reads secrets with `get_string`, as `crates/dbt-auth/AGENTS.md` asks. But profile
  parsing (`TrinoDbConfig.password` and `jwt_token` are `Option<String>`, the same as in Exasol
  and ClickHouse) still rejects a numeric password and prints it in the error. This is a shared
  gap that this PR does not change.

**Semantic changes in dbt-auth**, as `crates/dbt-auth/AGENTS.md` asks (this adds a backend and
changes no existing one):
- Borrowed data: `TrinoAuthIR` borrows from the profile. A `Cow` is owned only for `get_string`
  values given as YAML numbers or booleans, the `KRB5_CONFIG` fallback and the `s` suffix of a
  `query_timeout` in seconds.
- Accessors: `password` and `jwt_token` use `get_string`, as the Exasol and ClickHouse backends
  read secrets, and so do `port` and `query_timeout`; the other text fields use `get_str`.
- Accepted input shapes: an empty string or mapping counts as unset for `impersonation_user`,
  `http_headers`, `role` and `starburst_url`; `query_timeout` takes an integer or a string.
- Enum structure: `TrinoAuthIR { None, Ldap, Jwt, Kerberos }` is new.
- Normalization: a `query_timeout` in seconds gets an `s` suffix; `roles` and
  `session_properties` become sorted `key:value;key:value` strings and `client_tags` a
  comma-separated list; a Kerberos principal is split into principal and realm.

Human verification is required before committing this change.

**Tests:** unit tests for every method, each with its full URI; the options; host, port and
`query_timeout` validation, with zero and decimal seconds; the unsupported options, with empty
values; Kerberos options and `krb5_config` precedence; secret handling and warnings; a
`profiles.rs` parse test. Live-tested over HTTPS with a password (also one with URL-special
characters), a JWT, a CA bundle and `cert: false`.

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
  `VARCHAR`), so the full type is rebuilt: `DECIMAL(p, s)` from the Arrow decimal type, and
  `VARCHAR(n)`, `CHAR(n)`, `TIME(p)` and `TIMESTAMP(p)` from the driver's length and precision
  metadata. A `decimal(10,2)` input stays `DECIMAL(10, 2)`, so 12.34 stays 12.34. For an
  ephemeral tested model, the expected types come from the Arrow schema of the probe query in
  the same way. Trino allows a precision of up to 12 for `timestamp` and `time`; above 9, the
  Arrow type uses nanoseconds and the fixture keeps the declared type. Timestamp literals use a
  space separator, and `timestamp with time zone` and `uuid` columns are typed correctly. This
  follows the per-adapter fixture typing of 68ad837 (BigQuery) and c157a08 (DuckDB).
- Seeds get `DATE`/`TIMESTAMP` typed literals. The microbatch filter uses `TIMESTAMP '… UTC'`
  literals, in one arm shared with Exasol (v1 `relation.py`).

Each change links the v1 code that it mirrors.

**Shared files, Trino-only behavior:** `BaseRelation::resolve_component` (dbt-schemas),
`build_standard` (Exasol's `build_exasol`, renamed) and the microbatch filter arm shared with
Exasol. Other adapters behave as before. The fixes for every adapter are in S1 and S2.

**Needs S1 and S2 at run time:** without S1, a uuid value in `run_query`, an enforced contract
or a unit test crashes dbt. With S1, these paths show the canonical text; `dbt show` still
prints a uuid as 32 hex digits. Without S2, unit tests do not compare the `decimal` and
`timestamp(3)` values that adbc-drivers/trino returns as `Decimal32`, `Decimal64` and
millisecond timestamps.

### Part 3a — `refactor(adapter): share the Exasol metadata adapter as GenericMetadataAdapter`

No behavior change. It renames `ExasolMetadataAdapter` to `GenericMetadataAdapter`, following
the "`GenericFoo` + `match adapter_type`" rule in `.agents/adapters.md`, and moves DuckDB's
`information_schema` row conversion into a shared helper. Error messages keep the capitalized
adapter name. Exasol and DuckDB tests are unchanged.

### Part 3b — `feat(trino): metadata adapter, relation listing and get_relation`

Trino uses the generic metadata adapter. It lists relations from
`<catalog>.information_schema.tables` and finds materialized views through
`system.metadata.materialized_views`, as v1's `trino__list_relations_without_caching` does. The
catalog, schema and table literals in this SQL are lowercase whatever the quote policy, like
v1's `| lower`. Without a catalog (for example `get_relation(database=none, ...)`), the SQL
reads the session catalog, as v1 does. DuckDB's `get_relation` SQL is byte-identical.

When dbt needs the relation cache (with `--defer`, and before a dev-clone of the run cache),
Trino hydrates it: it lists every schema in parallel and reports progress per schema. A schema
that fails to list keeps its error, as Redshift does, and the other schemas are cached. So
`--defer` works without `--favor-state`. Exasol keeps its empty hydration.

Also for Trino: in `dbt docs generate`, a relation with a NULL `table_owner` has no owner (not
an empty one); transactions are reported as unsupported (dbt-trino runs in autocommit); and
`list_schemas` reads `schema_name`.

**Known limit:** `dbt run` and `dbt build` do not hydrate the cache in this v2 build. So with N
threads, a schema that is not cached yet can be listed up to N times: the shared `get_relation`
path has no single-flight lock. dbt-trino v1 lists it once. A per-schema lock in
`Adapter::get_relation` would fix this for every adapter, as a separate change.

**Tests:** listing SQL for mixed-case names and for an empty catalog, materialized-view rows,
the `get_relation` row mapping, a NULL table owner, the transactions feature, the
`list_schemas` column, and cache hydration, also when one schema fails to list.

### Part 4 — `feat(trino): dbt-trino macro package, materializations and model configs`

**Problem:** There's no Trino macro package, so nothing materializes.

**Solution:**

**Submitted on behalf of a third-party: Starburst Data, Inc. (dbt-trino v1.10.5, commit
6b097c4eb3cbdd5eb6a0bc0209796626aebf32c6, Apache-2.0).** This covers
`crates/dbt-loader/src/dbt_macro_assets/dbt-trino/**`; only the changes marked `v2:` are my own
work.

- **Vendored macros:** "Copyright 2021 Starburst Data, Inc."; v1.10.6 has no macro changes.
  Provenance is in each file header and in `dbt_macro_assets/README.md`. Each v2 change is
  marked `v2:`. The main ones:
  - `information_schema('<view>')`, `%s` binding literals, escaping of interpolated literals,
    catalog SQL types, and renames qualified with catalog and schema
  - the catalog, schema and table literals of the metadata queries are lowercase, because Trino
    stores these names in lowercase
  - a private `trino_quoted_literal` macro instead of a `trino__string_literal` override, so
    `dbt.string_literal` keeps dbt's default behavior
  - a switch from a view to a table in `rename` mode builds the new table first, so the old
    relation survives a failed build; `drop`, `replace` and `skip` drop the view first
  - `persist_docs` on a materialized view puts the comment into `CREATE MATERIALIZED VIEW …
    COMMENT`, because Trino rejects `COMMENT ON` for a materialized view (v1 rendered
    `comment on materialized_view …`)
  - `properties()`: a `catalog_name` gives a clear "not supported yet" error; without it,
    `storage_uri` sets `location` (v1 parity). As in v1, a fixed location (`storage_uri` or
    `properties.location`) needs `on_table_exists: replace` or `drop`: in `rename` mode, the
    new table gets the same location, which Iceberg refuses while the old table uses it
  - grants: the show-grants SQL lowercases names and reads only user grantees
    (`grantee_type = 'USER'`), because dbt grants only to users. It leaves out the current
    user, so dbt never revokes its own privileges
  - `on_schema_change` keeps drop-before-add; a comment explains the Hive metastore trade-off
- **Config keys**, with dbt-trino's names (Exasol precedent): `properties` for models, seeds and
  snapshots; `on_table_exists`, `view_security`, `views_enabled`, `sync_nested_columns` and
  `grace_period` for models only. They are in `log_state_mod_diff` too.
- **Adapter behavior:**
  - constraint support (`not_null` enforced), taken from v1 `CONSTRAINT_SUPPORT`
  - grants use the standard parser
  - incremental strategies `append`, `merge`, `delete+insert` and `microbatch`, as in v1
  - a materialized-view full refresh uses `CREATE OR REPLACE MATERIALIZED VIEW`, so the old view
    stays if the new definition fails
  - seed types match v1 (`INTEGER`, `DOUBLE`, bare `TIMESTAMP`)
- **Nested ROW schema sync:** `adapter.diff_nested_column_types`, a generic struct diff in
  `dbt-adapter-sql`. New fields keep the source order, and a missing nested struct is added as
  one field. Trino matches `ROW` fields by position, so if the fields of a `ROW` column, or of a
  `ROW` in it, would be in another order than in the model, dbt stops with an error that asks
  for `--full-refresh` (v1 swaps the values silently). The error comes after the `ALTER`
  statements, so the new field is already in the table, and later runs fail too until a
  `--full-refresh`.
- **Shared code:** `CatalogRelation::from_model_config_and_catalogs`
  (`dbt-adapter/src/catalog_relation.rs`) has a Trino arm that fails when a model sets
  `catalog_name`, with the same message as `properties()`. It is needed because
  `generate_database_name` calls `build_catalog_relation` at parse time, before any macro of
  this package runs. A generic error for every adapter without catalog integrations would work
  too, if you prefer it. No shared `dbt-adapters` macros are changed.

**Known limit (Delta Lake on a Hive metastore):** Trino cannot rename managed Delta tables
there, so `rename` mode fails on Delta: a table rerun fails at the rename, and a switch from a
view builds the new table, drops the view and then fails at the rename. Use
`on_table_exists: drop` or `replace` for Delta models. `skip` drops the view first, so a switch
works on Delta.

**Interface changes** (need Product/DX approval): the six config keys and
`adapter.diff_nested_column_types`.

**Tests:** loader tests for the `v2:` changes, including the `sync_column_schemas` override, a
mixed-case database in the catalog and `check_schema_exists` SQL, and the user-only grants
query. The two `v2:` edits in `seeds/helpers.sql` remove a v1 comment and an unused `set`, and
change no behavior. Struct-diff tests in `dbt-adapter-sql`, and unit tests for the shared guard
(with and without `catalog_name`) and for the Trino seed types in `convert_type`.

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
