# Contributing the Trino adapter to dbt-labs/dbt

Nothing in this fork has been submitted to dbt-labs/dbt. This is the kit for when you decide
to. The local clone's `upstream` remote has its push URL disabled on purpose. The facts about
dbt Labs and GitHub in this file were checked on 3 and 4 October 2026, and the follow-ups on 4
and 5 October. On 19 October the PR branches were cut on dbt-labs `main` 112adf8, and
`trino-pr/integration` was rebased onto it (see [PR branches on 112adf8](#pr-branches-on-112adf8)).

Before the first PR, in this order:

1. Sign the [Individual CLA](#individual-cla). **Done:** signed and submitted on 19 October
   2026 as `abhishekguha996-ux`.
2. Push `trino-pr/integration` to your fork, check that the fork workflow's Linux x86_64 run
   passes, and add it to [TEST-RESULTS.md](TEST-RESULTS.md). **Done:** b197698, on dbt-labs
   `main` 112adf8, was pushed on 19 October 2026, and fork run 39303130529 passed (see
   [TEST-RESULTS.md](TEST-RESULTS.md#fork-run-on-112adf8-linux-x86_64)). TEST-RESULTS.md also
   records the live results of the series on 7bbd974, of its [follow-ups](#follow-ups) F1 and
   F2, and the gates of the `pr/` branches on 112adf8.
3. File the [driver issues](DRIVER-ISSUES.md). **Done:** filed on 20 October 2026 as
   adbc-drivers/trino #127 to #133, with a comment on #19.
4. Post the [Slack message](#slack-message) and ask which [PR shape](#pr-shape-options) the
   maintainers want.

The Part 4 follow-up F3 is left out: Part 4 goes upstream as reviewed, `8f0bf3b` (see
[Follow-ups](#follow-ups)).

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
[umbrella issue](#umbrella-issue) carry this marking, and they name your own work: in the
vendored files, the provenance headers, the changes marked `v2:` and two small unmarked edits;
and the one new file, `macros/relations.sql`, which is not from dbt-trino. If dbt Labs wants the
vendored files in a separate submission, offer them as a separate commit or PR.

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

Each part is one commit. Together they change only `crates/` and `.changes/`, and so do the
[follow-ups](#follow-ups). `contrib/` and `.github/` are fork-only and never go upstream.

| Part | Record branch | Commit | PR branch on 112adf8 | Commit subject | Needs first |
|---|---|---|---|---|---|
| 0 | `trino-pr/p0-redact-access-token` | `1901220` | `pr/p0` `584285f` | `fix(adbc): redact accessToken URI parameters in Builder Debug output` | — |
| S1 | `trino-pr/s1-agate-uuid-text` | `5ee10b4` | `pr/s1` `a0851b3` | `fix(dbt-agate): show arrow.uuid columns as text instead of panicking` | — |
| S2 | `trino-pr/s2-unit-test-compare` | `5733d42` | `pr/s2` `6fc4960` | `fix(dbt-tasks-sa): compare unit-test values of Arrow types without a formatting arm` | — |
| 1 | `trino-pr/p1-profile-auth` | `ab2948f` | `pr/p1` `202707d` | `feat(trino): profile schema and ADBC authentication` | — |
| 2 | `trino-pr/p2-types-relations` | `8943170` | `pr/p2` `97f9da5` | `feat(trino): relations, columns, SQL types and literals` | 1 |
| 3a | `trino-pr/p3a-generic-metadata-adapter` | `7de6091` | `pr/p3a` `577d8e4` | `refactor(adapter): share the Exasol metadata adapter as GenericMetadataAdapter` | — |
| 3b | `trino-pr/p3b-metadata` | `10a13da` | `pr/p3b` `73b7c86` | `feat(trino): metadata adapter, relation listing and get_relation` | 1, 3a |
| 4 | `trino-pr/p4-macros-materializations` | `8f0bf3b` | `pr/p4` `afb2785` | `feat(trino): dbt-trino macro package, materializations and model configs` | 1, 2 |
| 5 | `trino-pr/p5-init-wizard` | `6f3a4a3` | `pr/p5` `06b7f01` | `feat(trino): dbt init profile wizard` | 1 |

**The record branches are stacked.** They start at dbt-labs `main` 7bbd974
(`7bbd974389dbd08da3ece92396ecdd0c8f99719c`, 2 October 2026), and each one holds all the parts
above it in the table: `trino-pr/p1-profile-auth`, for example, holds Part 0, S1, S2 and
Part 1. `trino-pr/series` holds all nine parts and equals `trino-pr/p5-init-wizard` (6f3a4a3).
These branches record the reviewed commits. Never open a PR from them: Copybara mirrors the
whole diff against `main`, so a PR from `trino-pr/p1-profile-auth` would also carry Part 0, S1
and S2. Open each PR from its `pr/` branch, which is cut on the latest `main` (see
[PR branches on 112adf8](#pr-branches-on-112adf8)).

`trino-pr/integration` is dbt-labs `main` 112adf8 with Part 0, S1, S2 (with F1) and Parts 1 to
5 (Part 1 with F2), with the same code as `pr/series`, `pr/s1` and `pr/s2` together, then the
fork-only `contrib/` and `.github/` commits. F3 and its revert are not on it. Its tip before
the rebase, 3a8beec on 7bbd974, is kept as the local branch `trino-pr/integration-7bbd974`; it
holds the commits that the live records in TEST-RESULTS.md name (892256e, e7a1675, 8809833).

Each part was also checked alone: on 7bbd974, with only the parts in its "Needs first" column
before it, it applies cleanly and passes `cargo fmt`, `cargo check --all-targets` and the tests
of its crates (see [TEST-RESULTS.md](TEST-RESULTS.md#rust-checks-7bbd974)). If `main` moves again,
rebase the `pr/` branches and update the "PR branch on 112adf8" column. The `trino/p*` branches (local and on the fork) and the local
`trino-ready/*` branches hold earlier rounds: do not open PRs from them either.

S1 and S2 fix bugs in code that every adapter uses. They use no Trino code, so they go upstream
as small "Fixes" PRs of their own, each with cross-adapter tests. Part 2 needs them at run
time: S1 to show uuid values as text, and S2 to compare the values of Trino `decimal(p)` with
p ≤ 18, `timestamp(1)` to `timestamp(6)` (with or without time zone), `tinyint`, `smallint`,
`time` and `varbinary` columns in unit tests.

"Needs first" lists the parts that must be on `main` first, or that the PR must include (see
Option A). On `main`, `backend_of(Trino)` is `todo!("Trino")`, so the Trino code of Parts 2,
3b, 4 and 5 runs only with Part 1: the tests of Parts 3b and 4 build a Trino engine or adapter,
and Part 5 fills the profile fields that Part 1 adds. Part 3b builds on Part 3a's
`GenericMetadataAdapter`, and Part 4 on the Trino types and relations of Part 2. Before you
open a PR, apply the part alone, with the parts it needs, to the latest `main` and run the
gates there (see [How to open a PR from the fork](#how-to-open-a-pr-from-the-fork)). A useful
adapter needs all parts; Part 0 is defense in depth for Part 1's JWT.

### Follow-ups

Three bugs that the reviews found were fixed after the record branches were made. Each fix is
a follow-up commit on `trino-pr/followups`, which is `trino-pr/series` plus these three
commits. F1 and F2 go upstream, each folded into its part. **F3 is left out** (decided on 5
October): `trino-pr/followups` keeps it at its tip only as a record, and `trino-pr/integration`
holds it as `e7a1675` and reverts it in `8809833`. So the `crates/` and `.changes/` of
`trino-pr/integration` are those of `trino-pr/followups~1`, the series with F1 and F2.

| Follow-up | Commit | On `trino-pr/integration` | Commit subject | Part | Needs first | Upstream |
|---|---|---|---|---|---|---|
| F1 | `a5767d1` | `99233a2` | `fix(dbt-tasks-sa): keep the decimal sign and show NULL in unit-test value comparisons` | S2 | S2 | folded into S2 |
| F2 | `25a4eca` | `56e7e77` | `fix(trino): accept a decimal number of seconds for query_timeout` | 1 | 1 | folded into Part 1 |
| F3 | `135bdd0` | `e7a1675`, reverted by `8809833` | `fix(trino): stop before any ALTER when an ARRAY or MAP element ROW changes field order` | 4 | 1, 2, 4 | **left out** |

- **F1** (S2): a unit test passed when a `Decimal128` value between -1 and 0 differed only in
  its sign (-0.50 and 0.50 both showed as `0.50`), or when a map value was NULL on one side and
  an empty string on the other.
- **F2** (Part 1): an unquoted decimal, such as `query_timeout: 1.5`, failed when dbt parsed
  `profiles.yml`. Only a quoted `"1.5"` worked.
- **F3** (Part 4), left out: with `sync_all_columns`, F3 stops the run before any `ALTER` when
  `ROW` fields are already in another order than in the model, also in the `ROW` elements of an
  `ARRAY` or `MAP` field.

**Why F3 is left out.** For the `ROW` elements of `ARRAY` and `MAP` fields, F3 stops a change
that works. Without F3, a `sync_all_columns` run of Part 4 sends `ALTER COLUMN … SET DATA TYPE`
for such a field, as dbt-trino v1 does. Iceberg maps the element fields by field id, so it keeps
each value in its field, and the run succeeds with correct data. F3 turned this into a stop
that asks for `--full-refresh`, so the incremental table had to be rebuilt. On Delta Lake and
Hive, the connector refuses the `ALTER` (`NOT_SUPPORTED`), and the run fails before the table
changes, with or without F3: no value reaches a wrong field there, and F3 only gave a clearer
message. Both results were checked live on 8809833 (see
[TEST-RESULTS.md](TEST-RESULTS.md#nested-row-order-checks)).

So Part 4 goes upstream as `8f0bf3b`, as it was reviewed:

- Its text under [PR descriptions](#pr-descriptions) has back the `sync_all_columns` limit
  that F3 removed, with the result on each connector.
- Its commit message gets a narrower first "Bugs fixed" bullet on the PR branch (see
  [How to open a PR from the fork](#how-to-open-a-pr-from-the-fork)).
- The `ARRAY` and `MAP` case has no loader test, because the only one came with F3. The
  struct-diff tests of Part 4 and the live checks cover it.

A follow-up is not a PR of its own. Fold F1 into S2 and F2 into Part 1 when you cut their PR
branches, so each of these PRs has one commit (see
[How to open a PR from the fork](#how-to-open-a-pr-from-the-fork)). The record branches of the
parts keep the reviewed commits. The follow-ups have plain `fix(…)` subjects, not `fixup!`, so
`git rebase --autosquash` does not pair them with their parts.

F1 and F2 were each checked alone on 7bbd974, with the parts in their "Needs first" column
before them: each applies cleanly and passes `cargo fmt`, `cargo check --all-targets`, clippy
and the tests of its crates (see [TEST-RESULTS.md](TEST-RESULTS.md#rust-checks-7bbd974)). The live run
of `trino-pr/integration` e7a1675 checked each fix against the binary of 892256e (see
[TEST-RESULTS.md](TEST-RESULTS.md#redgreen-checks-of-the-follow-ups)), and 8809833 has the
same F1 and F2 code. F1's NULL text has a Rust test only, because no Trino value reaches that
code.

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
adapter uses, and they need no other part. `trino-pr/series` holds them too, so do not open
the Option B PR from it: cut `pr/series` with the seven Trino parts only (see
[How to open a PR from the fork](#how-to-open-a-pr-from-the-fork)).

**Recommendation.** Propose Option A in Slack and in the umbrella issue, and offer Option B if
`felipecrv` prefers one review. Do not open a strict stack: with Copybara, every later PR would
carry all earlier parts.

## How to open a PR from the fork

### PR branches on 112adf8

On 19 October all PR branches were cut, as the recipe below describes, on dbt-labs `main`
112adf8 (`112adf89c`, 18 October 2026). They are local branches of the clone; nothing is
pushed. Each is one PR, in the form that it goes upstream:

| PR | Branch | Tip | Commits on `main` |
|---|---|---|---|
| Part 0 | `pr/p0` | `584285f` | Part 0 |
| S1 | `pr/s1` | `a0851b3` | S1 |
| S2 | `pr/s2` | `6fc4960` | S2 with F1, as one commit |
| Part 1 | `pr/p1` | `202707d` | Part 1 with F2, as one commit |
| Part 2 | `pr/p2` | `97f9da5` | Parts 1 and 2 |
| Part 3a | `pr/p3a` | `577d8e4` | Part 3a |
| Part 3b | `pr/p3b` | `73b7c86` | Parts 1, 3a and 3b |
| Part 4 | `pr/p4` | `afb2785` | Parts 1, 2 and 4 (without F3) |
| Part 5 | `pr/p5` | `06b7f01` | Parts 1 and 5 |
| Option B | `pr/series` | `6480cf3` | Parts 0, 1, 2, 3a, 3b, 4 and 5 |

What is done on them:

- F1 is folded into S2 and F2 into Part 1. F3 is left out.
- The changie entries and commit messages are completed as
  "Commit messages to complete" in [the recipe](#the-recipe) says. The S1 and S2 entries have
  `issue: ""`: set the bug issue numbers when you have them.
- Conflicts with `main` are resolved. Part 1: `connection_keys_for` in `profiles.rs` keeps
  upstream's Spark keys and adds the Trino keys. Part 2: the tests that upstream and Part 2 add
  to the same files are both kept. Part 3b: the Trino listing code takes
  `&mut ConnectionGuard<'_>` after upstream 5f5010f, and the external-Iceberg check is
  upstream's `skips_schema_wide_listing`. Part 4: the dbt-trino line of the macro assets
  README sits next to upstream's new entry. Part 5: the wizard is in
  `dbt_profile_schemas::ProfileSetup::setup` after upstream 794eb2a; its commit message names
  this.
- Part 2 uses `ErrorCode::from(e.kind())` instead of `ErrorCode::Generic`, because upstream
  `AGENTS.md` (df7e7fa) forbids `ErrorCode::Generic` in new code.
- Gates on each branch: `cargo fmt --all --check` and
  `cargo clippy --workspace --all-targets -- -D warnings` pass;
  `cargo nextest run --workspace` passes except 26 ClickHouse record/replay tests, which fail
  in the same way on `main` 112adf8 (see [TEST-RESULTS.md](TEST-RESULTS.md#gates-on-112adf8)).

To open a PR, push its branch and run `gh pr create` as in the examples below. If `main` has
moved, rebase the branch first, for example
`git rebase --onto upstream/main 112adf89c pr/p2`, and run the gates again. The cherry-pick
recipe below is how these branches were cut. Use it again only to cut a branch from the record
commits.

### The recipe

Your plan (clone, make a branch, port the code, open a PR) is right, with these details:

- You cannot push to dbt-labs/dbt. A PR comes from a branch in your fork,
  `abhishekguha996-ux/dbt-trino-v2`, which is already a GitHub fork of dbt-labs/dbt. The clone
  in `~/dbttrinoadapter/upstream/dbt` has `origin` = your fork and `upstream` = dbt-labs/dbt,
  and it holds the commits of [the PR series](#the-pr-series) and its follow-ups, which are not
  pushed yet. Run the commands below in that clone, or in a worktree of it, with a clean
  working tree.
- Cut one new branch for each PR from the latest dbt-labs `main`. Cherry-pick into it the
  parts in its "Needs first" column that are not on `main` yet, then the part itself. Fold
  F1 into S2 and F2 into Part 1, each into the same commit as its part. F3 is left out, so
  Part 4 is `8f0bf3b` as it is (see [Follow-ups](#follow-ups)). Never use a `trino-pr/*` record
  branch as a PR branch: they are stacked.
- Run the same gates as dbt Labs' CI (`.github/workflows/ci.yml`) before you push.

For example, Part 2 while Part 1 is still open:

```sh
git fetch upstream
git switch -c pr/p2 upstream/main
git cherry-pick pr/p1             # Needs first: Part 1 with F2, only while it is not on main
git cherry-pick 8943170           # Part 2
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
RUST_MIN_STACK=8388608 cargo nextest run --workspace
git push origin pr/p2
gh pr create -R dbt-labs/dbt --base main --head abhishekguha996-ux:pr/p2 \
  --title "feat(trino): relations, columns, SQL types and literals" --body-file pr-part2.md
```

`git cherry-pick pr/p1` picks the last commit of the Part 1 PR branch: Part 1 with F2 folded
in, the same commit that the Part 1 PR shows. So cut the PR branches in the order of the merge
plan.

A part with a follow-up goes into its PR as one commit. For example, S2 with F1:

```sh
git fetch upstream
git switch -c pr/s2 upstream/main
git cherry-pick -n 5733d42 a5767d1   # S2 and F1, applied and staged, not committed
git rm -qf .changes/unreleased/Fixes-20261004-224109.yaml       # F1's entry
"${EDITOR:-vi}" .changes/unreleased/Fixes-20261004-173311.yaml  # S2's issue and body, below
git add .changes/unreleased/Fixes-20261004-173311.yaml
git commit -c 5733d42                # S2's message and author, in the editor; see below
```

`git rm` needs `-f`, because the entry is staged but not committed. `git commit -c` keeps the
author and the date of the part and opens its message in the editor. A plain
`git cherry-pick 5733d42 a5767d1` followed by `git reset --soft HEAD~2` gives the same staged
changes. Then run the gates as above.

The cherry-picks for each PR:

| PR | Branch | First, only the parts not on `main` yet | Then, as one commit | Changie entries |
|---|---|---|---|---|
| Part 0 | `pr/p0` | — | `1901220` | — |
| S1 | `pr/s1` | — | `5ee10b4` | set the issue and the body (below) |
| S2 | `pr/s2` | — | `5733d42` with F1 `a5767d1` | remove F1's `Fixes-20261004-224109.yaml`; set S2's issue and body (below) |
| Part 1 | `pr/p1` | — | `ab2948f` with F2 `25a4eca` | remove F2's `Fixes-20261004-224603.yaml` |
| Part 2 | `pr/p2` | `pr/p1` (Part 1) | `8943170` | — |
| Part 3a | `pr/p3a` | — | `7de6091` | — |
| Part 3b | `pr/p3b` | `pr/p1 pr/p3a` (Parts 1 and 3a) | `10a13da` | — |
| Part 4 | `pr/p4` | `pr/p1 pr/p2` (Parts 1 and 2) | `8f0bf3b` alone: F3 is left out (see [Follow-ups](#follow-ups)) | — |
| Part 5 | `pr/p5` | `pr/p1` (Part 1) | `6f3a4a3` | — |

Checked on 5 October in a scratch clone, with 7bbd974 as `upstream/main`: each of these sets
applies cleanly. In merge-plan order, the nine PR commits give the code of
`trino-pr/followups~1` (the series with F1 and F2), which is also the code in the `crates/` of
`trino-pr/integration`; only the changie entries differ. The gates ran on each part alone, and
on each follow-up with the parts it needs (see [TEST-RESULTS.md](TEST-RESULTS.md#rust-checks-7bbd974)),
but not on Parts 2, 3b, 4 and 5 with F2 in their Part 1. Run them on each `pr/` branch before
the push.

- **A part that has landed** reaches `main` as a new Copybara commit by `fa-assistant`, so its
  SHA differs from the Commit column, and `git branch --contains` does not find it. Judge
  "landed" from its PR, and leave the part out. If you cherry-pick it anyway and git reports
  that the cherry-pick is empty, run `git cherry-pick --skip`.
- **A PR that includes a Needs-first part** says "review only the last commit" and names the
  PR of that part (see Option A).
- **A conflict** after `main` has moved: resolve it on the `pr/` branch and run the gates
  again. Leave the `trino-pr/*` record branches as they are.
- **The S1 and S2 changie entries** name issue 13131, the Trino release issue, although they
  fix code that every adapter uses. Before the push, set `issue` to the bug issue of the fix (or
  to `""`, as upstream entries without an issue do) and shorten the body. On `pr/s2`, do it
  before `git commit -c` (see the S2 example). On `pr/s1`, edit the entry after the
  cherry-pick, then run `git commit --amend --no-edit <entry file>`.
  - S1, `.changes/unreleased/Fixes-20261004-173301.yaml`: "Show arrow.uuid columns as UUID
    text in run_query, enforced contracts and unit tests instead of panicking, and return an
    error instead of a panic when Agate cannot convert a result column"
  - S2, `.changes/unreleased/Fixes-20261004-173311.yaml`, which also covers F1: "Fix unit
    tests passing despite mismatched values in columns such as small integers, Decimal32/64,
    millisecond and microsecond timestamps, time, binary and map columns, NULL against a value
    (also inside a map value), and the sign of a decimal between -1 and 0"
- **A folded follow-up keeps no changie entry of its own.** F1's facts go into S2's body above.
  Part 1 adds Trino features that no release has yet, so its "Features" entry covers F2, and
  the F2 entry is removed. F3 and its entry, `Fixes-20261004-225131.yaml`, are not picked.
- **Commit messages to complete** on their PR branches (the record commits keep the reviewed
  text). For a part with a follow-up, edit the message in the editor of `git commit -c`; for
  the others, use `git commit --amend`:
  - S2 with F1: in S2's second paragraph, replace "and a NULL shows as NULL" with "and a NULL,
    also one inside a value such as a map value, shows as NULL". Then add F1's two bullets (the
    `Decimal128` sign and the leading zeros of the fraction; the NULL text of the fallback), its
    "Unchanged" line and its "Tests" paragraph, after a line such as "Two more cases showed
    different values as the same text:". Leave out "Follow-up to …".
  - Part 1 with F2: in the first bullet, replace "(an integer, or a decimal string such as
    "1.5") or a Go duration such as 30m" with ", such as 300 or 1.5 (quoted or not), or a Go
    duration such as 30m". Add F2's second paragraph ("The field now keeps the YAML value as
    written, …") as a bullet after it. Under "Accepted input shapes", replace "query_timeout
    takes an integer or a string" with "query_timeout takes an integer, a decimal or a string",
    and add F2's "Tests" sentence to the tests paragraph. Leave out F2's own "Semantic changes"
    paragraph: Part 1's paragraph, with this change, covers it.
  - Part 2 names only S1 as a run-time need. Add after its uuid paragraph: "Unit tests detect
    mismatches in decimal(p<=18), timestamp(1-6) [with time zone], tinyint, smallint, time and
    varbinary columns only with "fix(dbt-tasks-sa): compare unit-test values of Arrow types
    without a formatting arm"."
  - Part 4 (`8f0bf3b`, without F3) says "Each change for dbt v2 is marked `v2:` in the macro
    files". Write "Each behavior change", and add that `dbt_project.yml` (quoted version) and
    `adapters.sql` (v1's header comment removed) have unmarked edits and that
    `macros/relations.sql` is new. The dbt-trino line of
    `crates/dbt-loader/src/dbt_macro_assets/README.md` says "dbt v2 changes are marked `v2:` in
    each file"; correct it in the same amend. The first "Bugs fixed" bullet ("nested ROW sync
    adds fields in the model's order …") says that dbt stops with a request for
    `--full-refresh` whenever the `ROW` elements of `ARRAY` and `MAP` fields are in another
    order. Without F3, that is true only with `append_new_columns`. Replace the whole bullet
    with this text:

    ```text
    - nested ROW sync adds fields in the model's order instead of alphabetical order, and
      stops with a request for --full-refresh when, after its ALTERs, the fields of a ROW
      column, of a ROW nested in it, or (with append_new_columns) of the ROW elements of
      its ARRAY and MAP fields are in another order in the target (a field inserted
      mid-row); v1 wrote values to the wrong fields, because Trino matches ROW fields by
      position on INSERT and MERGE. With sync_all_columns, a new field order in the ROW
      elements of an ARRAY or MAP field is a type change of that field, as in v1:
      ALTER COLUMN ... SET DATA TYPE, which Iceberg applies with each value in its field,
      and which Delta Lake and Hive refuse with NOT_SUPPORTED;
    ```

**One PR (Option B):** Parts 0 to 5 on one branch, without S1 and S2, which are separate PRs
in both options. Part 1 gets F2 as above:

```sh
git fetch upstream
git switch -c pr/series upstream/main
git cherry-pick 1901220                                   # Part 0
git cherry-pick -n ab2948f 25a4eca                        # Part 1 with F2, as one commit
git rm -qf .changes/unreleased/Fixes-20261004-224603.yaml
git commit -c ab2948f                                     # edit the message as above
git cherry-pick 8943170                                   # Part 2
git commit --amend                                        # complete its message as above
git cherry-pick 7de6091 10a13da                           # Parts 3a and 3b
git cherry-pick 8f0bf3b                                   # Part 4, without F3
"${EDITOR:-vi}" crates/dbt-loader/src/dbt_macro_assets/README.md   # the dbt-trino line
git add crates/dbt-loader/src/dbt_macro_assets/README.md
git commit --amend                                        # complete its message as above
git cherry-pick 6f3a4a3                                   # Part 5
# then the gates, git push origin pr/series, and gh pr create with
# --head abhishekguha996-ux:pr/series
```

Part 2 and Part 4 are not the last commit of this branch, so complete their messages right
after their cherry-picks. Part 4 is `8f0bf3b` as it is, because F3 is left out. `pr/series`
(`6480cf3`) is this branch on 112adf8, and it passes the gates (see
[PR branches on 112adf8](#pr-branches-on-112adf8)). Do not
push `trino-pr/series` itself as the PR branch: it also holds S1 and S2, and it has no
follow-ups.

**Live Linux evidence:** push `trino-pr/integration` (the series on 112adf8 with F1 and F2
folded in, and the fork-only `contrib/` and `.github/` commits) to the fork. The fork
workflow then runs the Rust checks, builds the Linux and macOS archives, and runs the
functional suite and the jaffle-shop build with the Linux binary. Only `trino-pr/integration`
has the fork workflow, so a push of a `trino-pr/*` record branch or a `pr/` branch starts no
fork run (dbt Labs' own workflows run on a push only to `main`).

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
> driver (go/v0.6.1), following the adapter guide. jaffle-shop-classic plus an incremental
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
> 6b097c4eb3cbdd5eb6a0bc0209796626aebf32c6, Apache-2.0).** This covers the files under
> `crates/dbt-loader/src/dbt_macro_assets/dbt-trino/` that come from dbt-trino's
> `dbt/include/trino/`: all of them except `macros/relations.sql`. In those files, my own work is
> the provenance headers, the changes marked `v2:`, and two edits without a marker:
> `dbt_project.yml` quotes `version: '1.0'` and drops a blank line, and `macros/adapters.sql`
> drops v1's three header comment lines. `macros/relations.sql` (rename and replace macros for
> the v2 relation framework) is entirely my own work.
>
> **Evidence:** jaffle-shop-classic (+incremental, +snapshot) builds clean on Trino 483
> (Iceberg, Delta Lake, Hive on S3), plus a functional suite of 98 tests (97 pass; the Ctrl-C
> test is an expected failure, a driver limit), all reproducible from
> https://github.com/abhishekguha996-ux/dbt-trino-v2/tree/trino-pr/integration/contrib/trino-lab.
> The fork's CI runs both with the Linux x86_64 release binary.
>
> **Questions for dbt Labs:** the PR shape; Product/DX approval for the six config keys
> (`properties` for models, seeds and snapshots; `on_table_exists`, `view_security`,
> `views_enabled`, `sync_nested_columns` and `grace_period` for models) and
> `adapter.diff_nested_column_types` before Part 4; whether Part 0 (a redaction entry in
> `dbt-adbc`) is welcome; whether `AdapterType::Starburst` should use the Trino implementation;
> how to hand over a Trino target for your CI.
>
> **Known driver limits**, on go/v0.6.1: cancel does not stop a running query
> (adbc-drivers/trino#127); no mTLS (#128), OAuth 2.0 (#129), impersonation (#130) or custom
> HTTP headers (#131); `time with time zone` and HyperLogLog values are Go-formatted text
> (#132), and so are `map` and `row` values (#19). The Kerberos ticket cache is not supported
> by the adapter yet.

The driver issues were filed on 20 October 2026 (see [DRIVER-ISSUES.md](DRIVER-ISSUES.md)).

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
name issue 13131: change their `issue` and body on their PR branches. The follow-ups F1 to F3
have "Fixes" entries of their own on `trino-pr/followups`. When you fold F1 or F2 into its
part, the part keeps one entry (see
[How to open a PR from the fork](#how-to-open-a-pr-from-the-fork)). F3 and its entry are left
out.

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

**Tests:** an `arrow.uuid` column becomes canonical text (a null stays null, and the Arrow
batch keeps the `FixedSizeBinary(16)` column); a `FixedSizeBinary(16)` column without the
extension stays binary, which Agate cannot show as text, so `AgateTable::try_new` returns an
error instead of a panic.

### S2 — `fix(dbt-tasks-sa): compare unit-test values of Arrow types without a formatting arm`

**Problem:** A unit test compares the actual and expected rows by the text of each value
(`value_as_string` in `crates/dbt-tasks-sa/src/materialize.rs`). Only `Int32`, `Int64`,
`Float32`, `Float64`, `Utf8`, `Boolean`, `Decimal128`, `Timestamp` in seconds or nanoseconds,
and `Date32` have a formatting arm. Every other Arrow type prints `[unsupported]` on both
sides, so the test never sees a difference in such a column, not even NULL against a value. I
found this with adbc-drivers/trino, which returns `decimal(10, 2)` as `Decimal64` and
`timestamp(3)` in milliseconds. The `Decimal128` arm also takes the sign from the integer part,
which is 0 for a value between -1 and 0, so -0.50 and 0.50 both show as `0.50`.

**Solution:** Every Arrow type without an arm compares by its Arrow display text, with the
text `NULL` for a NULL at any depth, so a NULL inside a map value does not match an empty
string. A binary column compares as text when all its values are valid UTF-8, and as hex
otherwise. The `Decimal128` arm takes the sign from the raw value, and it keeps the leading
zeros of the fraction (`0.05`, not `0.5`).

**Behavior change for all adapters:** unit tests now compare these columns, for example:
- microsecond timestamps: `TIMESTAMP` and `DATETIME` on BigQuery, Databricks, Postgres,
  Redshift and DuckDB
- millisecond timestamps, `Date64`, `Time32` and `Time64`
- `Int8`, `Int16` and unsigned integers; `Decimal32`, `Decimal64` and `Decimal256` (BigQuery
  `BIGNUMERIC`)
- dictionary, map and binary columns
- NULL against a value, in all of these columns, also inside a map value
- the sign of `Decimal128` values between -1 and 0, for example BigQuery `NUMERIC` and Trino
  `decimal(p)` with p > 18

A unit test that passed only because both sides showed `[unsupported]`, or the same text for
two different decimals, can now fail. The changie entry says so.

**Known limits:** two arms that `main` already has still hide a difference:
- `Timestamp` in nanoseconds compares only to the whole second. adbc-drivers/trino returns
  Trino `timestamp(7)` to `timestamp(12)` this way: on `timestamp(9)`, a 1 ns and a 1 ms
  difference pass, and a 1 s difference fails (checked live).
- `Float32` and `Float64` compare with one decimal place: 1.23 and 1.24 both show `1.2`
  (checked live on a Trino `double` column).

This PR leaves them as they are: how exactly floats and nanosecond timestamps compare in unit
tests is for dbt Labs to decide.

**Tests:** cross-adapter cases. A mismatch is found in `Int16`, `Decimal64`, millisecond
timestamps, `Timestamp(µs, UTC)`, `Time64`, `BinaryView` (as text and as hex), dictionary and
map columns; for NULL against a value; for the sign of `Decimal128` and `Decimal256` values
between -1 and 0; and for NULL against an empty string in a map value. Equal expected and
actual rows, NULL included, still match in `Int16`, `Decimal64`, `Decimal128`,
`Timestamp(µs, UTC)`, `Time64`, `BinaryView` (valid UTF-8 and not),
`Dictionary(Int64, Utf8View)` and `Map` columns. Checked live on a Trino `decimal(20, 2)`
column: -0.50 against 0.50 fails with the diff `0.50 -> -0.50`.

### Part 1 — `feat(trino): profile schema and ADBC authentication`

**Problem:** `AdapterType::Trino` exists, but `backend_of` is `todo!("Trino")`,
`TrinoDbConfig` has eight fields, and there is no Trino auth, so any Trino profile panics.

**Solution:**
- `TrinoDbConfig` accepts the dbt-trino v1 credential fields (`catalog` aliases `database`),
  including the `starburst_*` fields of dbt-trino 1.10.3+; `starburst_secret_key` is never
  serialized. v1 profiles load unchanged, except for the differences listed below.
- `dbt-auth/src/trino` follows the crate's pattern: `parse_auth` builds a `TrinoAuthIR`
  (`None`, `Ldap`, `Jwt`, `Kerberos`), which `apply` and `apply_connection_args` turn into
  trino-go-client DSN options (v0.333.0 in driver go/v0.5.3, v1.3.0 in go/v0.6.1), wired
  with `auth_configure_pipeline!` like the Exasol and ClickHouse modules:
  - methods `none`, `ldap`, `jwt` and `kerberos` (keytab)
  - `roles`, `session_properties`, `client_tags`, `timezone` and `query_timeout`
  - `cert`: a CA bundle, `true`, or `false` (`SSLVerification=NONE`, which the ADBC driver
    reads itself)
  - `X-Trino-Source: dbt-trino-<version>`, so resource-group selectors keep matching
- `query_timeout` is not a v1 field. It takes a positive number of seconds, such as `300` or
  `1.5` (quoted or not), or a Go duration such as `30m`. `TrinoDbConfig` keeps the YAML value
  as written, as it does for `cert`, and dbt-auth validates it. Zero fails with its own
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
- `timezone` is sent. Driver go/v0.6.1 applies it, and without it sends the client's time
  zone, as v1 does. Driver go/v0.5.3 (trino-go-client v0.333.0) ignores it, so the session
  keeps the server's time zone; go/v0.6.0 fails to connect with it (adbc-drivers/trino#124).
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
  `http_headers`, `role` and `starburst_url`; `query_timeout` takes an integer, a decimal or a
  string (`get_string` turns a YAML number into its text).
- Enum structure: `TrinoAuthIR { None, Ldap, Jwt, Kerberos }` is new.
- Normalization: a `query_timeout` in seconds gets an `s` suffix; `roles` and
  `session_properties` become sorted `key:value;key:value` strings and `client_tags` a
  comma-separated list; a Kerberos principal is split into principal and realm.

Human verification is required before committing this change.

**Tests:** unit tests for every method, each with its full URI; the options; host, port and
`query_timeout` validation, with zero, decimal seconds (also unquoted YAML floats), a negative
number, a boolean and a list; the unsupported options, with empty values; Kerberos options and
`krb5_config` precedence; secret handling and warnings; a `profiles.rs` test that parses a v1
profile as `load_profiles` does, with `query_timeout` 300, 1.5, '1.5' and 30m. Live-tested over
HTTPS with a password (also one with URL-special characters), a JWT, a CA bundle and
`cert: false`, and with an unquoted `query_timeout: 1.5`, which cancels a slow query on the
server after 1.5 s.

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

**Shared code, Trino-only behavior:**
- `BaseRelation::resolve_component` (dbt-schemas)
- `build_standard` (Exasol's `build_exasol`, renamed)
- arms shared with Exasol: the microbatch filter, and the `DATE` and `TIMESTAMP` literals of
  `SqlLiteralFormatter::format_date` and `format_datetime`
- the Trino arms of the unit-test fixture code in dbt-tasks-sa (`renderable/unit_test.rs`)
- the seed column-name strategy in dbt-df-providers (`infer_seed_column_name_strategy`)

Other adapters behave as before. The fixes for every adapter are in S1 and S2.

**Needs S1 and S2 at run time:** without S1, a uuid value in `run_query`, an enforced contract
or a unit test crashes dbt. With S1, these paths show the canonical text; `dbt show` still
prints a uuid as 32 hex digits. Without S2, unit tests do not compare the values of
`decimal(p)` with p ≤ 18, `timestamp(1)` to `timestamp(6)` (with or without time zone),
`tinyint`, `smallint`, `time` and `varbinary` columns: adbc-drivers/trino returns them as Arrow
types without a formatting arm (`Decimal32`, `Decimal64`, millisecond and microsecond
timestamps, `Int8`, `Int16`, `Time32`, `Time64`, `BinaryView`), so both sides show
`[unsupported]`, and a mismatch passes.

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
6b097c4eb3cbdd5eb6a0bc0209796626aebf32c6, Apache-2.0).** This covers the files under
`crates/dbt-loader/src/dbt_macro_assets/dbt-trino/` that come from dbt-trino's
`dbt/include/trino/`: all of them except `macros/relations.sql`. In those files, my own work is
the provenance headers, the changes marked `v2:`, and two edits without a marker:
`dbt_project.yml` quotes `version: '1.0'` and drops a blank line, and `macros/adapters.sql`
drops v1's three header comment lines. `macros/relations.sql` (rename and replace macros for the
v2 relation framework) is entirely my own work.

- **Vendored macros:** "Copyright 2021 Starburst Data, Inc."; v1.10.6 has no macro changes.
  Provenance is in the header of each `.sql` file and in `dbt_macro_assets/README.md`. Each
  behavior change for dbt v2 is marked `v2:`; the two edits named above change no behavior and
  have no marker. One new file, `macros/relations.sql`, is not vendored: it holds the rename and
  replace macros that the v2 relation framework calls, and it qualifies each rename target with
  catalog and schema. The main `v2:` changes:
  - `information_schema('<view>')`, `%s` binding literals, escaping of interpolated literals,
    and catalog SQL types
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
  - seed types match v1 (`INTEGER`, `DOUBLE`, bare `TIMESTAMP`); whole numbers beyond the
    `INTEGER` range, which v1 could not load, become `BIGINT`
- **Nested ROW schema sync:** `adapter.diff_nested_column_types`, a generic struct diff in
  `dbt-adapter-sql`. New fields keep the source order, and a missing nested struct is added as
  one field. Trino matches `ROW` fields by position. So after the `ALTER` statements, dbt checks
  the field order of a `ROW` column, of the `ROW`s nested in it and of the `ROW` elements of its
  `ARRAY` and `MAP` fields. If it differs from the model's order, dbt stops with an error that
  asks for `--full-refresh`; v1 swaps the values silently (for the `ROW` elements of `ARRAY`
  and `MAP` fields, only with `append_new_columns`). A new field that `ADD COLUMN` puts at the
  end of a `ROW`, not in the middle as in the model, is then already in the table, and later
  runs fail too until a `--full-refresh`. Known limits:
  - A top-level `ARRAY(ROW)` or `MAP(ROW)` column is not diffed field by field. It goes through
    dbt's flat `on_schema_change`, as in v1, so a reordered element `ROW` there is not detected.
  - Inside `ARRAY` and `MAP` fields, only the order of the fields that both element `ROW`s have
    is checked. A field added there is not added on its own: the whole field counts as a type
    change, which only `sync_all_columns` applies.
  - With `sync_all_columns`, a new field order in the `ROW` elements of an `ARRAY` or `MAP`
    field is a type change of that field, as in v1: dbt runs `ALTER COLUMN … SET DATA TYPE`,
    after any nested `DROP COLUMN` and before the order check. Iceberg applies it and keeps each
    value in its field, so the run succeeds. Delta Lake and Hive refuse it (`NOT_SUPPORTED`):
    the run fails with that error, not with the `--full-refresh` message, and the table does
    not change. `append_new_columns` applies no type change and stops with the message.
  - When the same diff also removes a field and needs a type change that Iceberg cannot make
    (for example `integer` to `varchar` in the element `ROW`), Iceberg runs the `DROP COLUMN`
    and then fails with `ICEBERG_COMMIT_ERROR`. This is the drop-before-add trade-off: the
    nested `DROP COLUMN` statements run first, as in v1, so the table is partly changed until a
    `--full-refresh`.
- **Shared code:** `CatalogRelation::from_model_config_and_catalogs`
  (`dbt-adapter/src/catalog_relation.rs`) has a Trino arm that fails when a model sets
  `catalog_name`, with the same message as `properties()`. It is needed because
  `generate_database_name` calls `build_catalog_relation` at parse time, before any macro of
  this package runs. For that guard, `CatalogRelation::get_model_config_value` gets a Trino arm
  that reads Trino model configs from `config`, because Trino has no adapter attribute;
  without it, the guard never sees `catalog_name`. Other adapters are unchanged. A generic error
  for every adapter without catalog integrations would work too, if you prefer it. No shared
  `dbt-adapters` macros are changed.
- **No default catalog relation:** dbt-trino v1's default catalog integration returns a
  `trino_default` relation; Trino has none in v2 yet. So a custom macro that calls
  `adapter.build_catalog_relation(...)` without `catalog_name` gets the shared
  `Internal Error: build_relation_catalog cannot be invoked by an adapter Trino`, as other
  adapters without catalog integrations do. The built-in macros call it only when
  `catalog_name` is set.

**Known limit (Delta Lake on a Hive metastore):** Trino cannot rename managed Delta tables or
views there, so `rename` mode fails on Delta: a table rerun fails at the rename, and a switch
from a view builds the new table, drops the view and then fails at the rename, which leaves the
model without a relation until its next run and leaves a `__dbt_tmp` table behind (v1 fails
earlier, at renaming the view, and keeps it). Use `on_table_exists: drop` or `replace` for Delta
models. `skip` works too: it never renames, keeps an existing table, and drops a view first, so
a switch works on Delta.

**Interface changes** (need Product/DX approval): the six config keys and
`adapter.diff_nested_column_types`.

**Tests:** loader tests for the `v2:` changes, including the `sync_column_schemas` override,
the nested `ROW` order check, a mixed-case database in the catalog and `check_schema_exists`
SQL, and the user-only grants query. The two `v2:` edits in `seeds/helpers.sql` remove a v1
comment and an unused `set`, and change no behavior. Struct-diff tests in `dbt-adapter-sql`,
also for the `ROW` elements of `ARRAY` and `MAP` fields, which have no loader test, and unit
tests for the shared guard (with and without `catalog_name`) and for the Trino seed types in
`convert_type`.

**Evidence:**
- jaffle-shop-classic (+incremental, +snapshot) builds clean on Iceberg, Delta Lake and Hive on S3.
  As for every v2 adapter, the project needs dbt-autofix's YAML changes; Delta models use
  `on_table_exists: replace`, because `rename` cannot work there, and Hive has no snapshot (no
  `MERGE`). The patch is in `contrib/trino-lab/acceptance`.
- The functional suite (98 tests) passes on Memory, Hive, Iceberg and Delta Lake, except the
  Ctrl-C test, an expected failure from the driver's cancel limit (see TEST-RESULTS.md).
- The retail and TPC-H projects match Python oracles.
- Nested ROW sync, checked live inside a `ROW` column: with `sync_all_columns`, a new field
  order in the `ROW` elements of an `ARRAY` or `MAP` field is applied on Iceberg, with each
  value in its field, and fails with `NOT_SUPPORTED` on Delta Lake and Hive, with the table
  unchanged; with `append_new_columns`, it stops with the `--full-refresh` error on all three.
  A field added in the middle of a `ROW` stops the Iceberg run with that error before any
  `INSERT` or `MERGE`.

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

## Changes to this kit after the 4 October review

- The PR series names the real record branches and commits. They are stacked, so each PR gets
  a new `pr/` branch with cherry-picks at PR time, and Option B leaves out S1 and S2.
- The section 7 marking covers only the files that come from dbt-trino. It names your own work
  in them, including two unmarked edits, and `macros/relations.sql`, which is new.
- The Part 2 and Part 4 texts name every shared-code change, Part 2 names all the unit-test
  types that need S2, and two commit messages get their missing facts on the PR branches.
- The ROW order check covers the ROW elements of ARRAY and MAP fields; its known limits are in
  Part 4, FEATURES.md and MIGRATION.md.
- `skip` mode works on Delta Lake, and a `rename`-mode switch from a view on Delta leaves no
  relation until the next run, which differs from v1.
- The S2 text names the unit-test comparisons that still hide a difference, and its test gaps.
- A decimal `query_timeout` must be quoted; Part 1, MIGRATION.md and the docs-site draft say so.
- The umbrella and Part 4 evidence give the suite of the final run: 98 tests, 97 pass, and the
  Ctrl-C test is an expected failure. TEST-RESULTS.md records that run.

## Changes to this kit after the follow-ups (5 October)

- The PR series names the follow-ups F1 (S2), F2 (Part 1) and F3 (Part 4) on
  `trino-pr/followups`. "How to open a PR" folds each into the single commit of its part, with
  the changie entries and the commit messages to merge, and picks a Needs-first part from its
  own PR branch.
- F3 waits for a decision: an open review finding says that it stops a reorder that Iceberg can
  apply in place, as v1 does.
- The S2, Part 1 and Part 4 texts no longer list what F1 to F3 fixed: the decimal sign between
  -1 and 0, a NULL inside a map value, an unquoted decimal `query_timeout`, and the connector's
  own error for a reorder inside an `ARRAY` or `MAP` field. The float and nanosecond-timestamp
  comparison limits stay.
- TEST-RESULTS.md records the live run of `trino-pr/integration` e7a1675 with the red/green
  checks of the follow-ups; the 892256e run is the previous record.
- FEATURES.md, MIGRATION.md and the docs-site draft give the new `query_timeout` and ROW order
  behavior.

## Changes to this kit after the F3 decision (5 October)

- F3 is left out, and `trino-pr/integration` reverts it in 8809833. The Follow-ups section
  gives the reason: for the `ROW` elements of `ARRAY` and `MAP` fields, F3 stopped a
  `sync_all_columns` change that Iceberg applies correctly, as v1 does. The recipe folds only
  F1 into S2 and F2 into Part 1; Part 4 is `8f0bf3b` as it is, and Option B has no F3 variant.
- The Part 4 text has back the `sync_all_columns` limit for the `ROW` elements of `ARRAY` and
  `MAP` fields, now with the result on each connector, and its evidence gives the live checks
  of 8809833. "Commit messages to complete" gives the text that replaces the first "Bugs
  fixed" bullet of the Part 4 message. The Option B recipe completes the Part 2 and Part 4
  messages right after their cherry-picks, because neither is the last commit there.
- TEST-RESULTS.md records the live run of 8809833, with nested ROW order checks; the e7a1675
  and 892256e runs are short earlier records.
- FEATURES.md, MIGRATION.md and the docs-site draft give the nested ROW behavior without F3.

## Changes to this kit after the rebase onto 112adf8 (19 October)

- The CLA is signed (19 October 2026).
- The PR branches `pr/p0` to `pr/p5` and `pr/series` are cut on dbt-labs `main` 112adf8, with
  F1 and F2 folded in, the changie entries and commit messages completed, and the conflicts
  with `main` resolved. "PR branches on 112adf8" lists them, and the series table has their
  SHAs.
- Part 2 uses `ErrorCode::from(e.kind())` instead of `ErrorCode::Generic` (upstream
  `AGENTS.md`, df7e7fa).
- `trino-pr/integration` is rebased onto 112adf8. The old tip, 3a8beec, is the local branch
  `trino-pr/integration-7bbd974`.
- The fork archive holds the driver in `lib/dbt/`, because upstream f666b6c changed the
  folder that dbt searches next to its executable. INSTALL.md and the docs-site draft say so.

## Changes to this kit after the driver go/v0.6.1 check (19 October)

- The adapter was tested with ADBC driver go/v0.6.1 on 112adf8: the functional suite and the
  jaffle-shop build pass as with go/v0.5.3 (see
  [TEST-RESULTS.md](TEST-RESULTS.md#driver-gov061-on-112adf8-macos-arm64)).
- `timezone` works with go/v0.6.1, so the timezone driver issue is not filed, and the Part 1
  text, the Slack message and the umbrella issue no longer name it as a limit.
- DRIVER-ISSUES.md gives the go/v0.6.1 state of each issue: cancel, OAuth 2.0, impersonation
  and HTTP headers are unchanged; mTLS has a new cause; the Kerberos ticket cache needs a
  test first; the ROW and HyperLogLog values changed.
- The fork workflow ships go/v0.6.1. Fork run 39361917955 (b161d7a, 20 October) passed with
  it on Linux x86_64 (see [TEST-RESULTS.md](TEST-RESULTS.md#fork-run-with-driver-gov061)).
- The Part 1 code comment in `crates/dbt-auth/src/trino/mod.rs` still names go/v0.5.3 and
  trino-go-client v0.333.0. It is unchanged on the `pr/` branches.

## Changes to this kit after the driver issues were filed (20 October)

- The driver issues are filed as adbc-drivers/trino #127 to #133, with a comment on #19 (see
  [DRIVER-ISSUES.md](DRIVER-ISSUES.md)). The umbrella issue text names them.
- Before the Slack message, only step 4 is left.

