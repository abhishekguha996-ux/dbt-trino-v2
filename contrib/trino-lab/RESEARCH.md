# Public research, checked 25 September 2026

The user identified dbt v2 through the [official upgrade guide](https://docs.getdbt.com/docs/dbt-versions/dbt-upgrade/upgrading-to-v2?version=2). The project targets the public [dbt-labs/dbt](https://github.com/dbt-labs/dbt) monorepo and dbt OSS 2.0.5. It does not target the older Python dbt Core v1 adapter API.

The bounded public search found [Trino support request #13131](https://github.com/dbt-labs/dbt/issues/13131). A maintainer welcomed community work and gave no delivery date. Related [PR #15345](https://github.com/dbt-labs/dbt/pull/15345) concerns inline UDF work; it is not a complete Trino adapter. These findings do not establish that nobody is working privately on one. Check the issue and open pull requests again before an upstream submission.

An outreach draft would be an unsent note asking maintainers about plans or design requirements. It is optional. This fork was built without sending such a note.

Technical sources:
- [Arrow ADBC Trino driver](https://arrow.apache.org/adbc/current/driver/trino.html)
- [Trino 483 source](https://github.com/trinodb/trino/tree/483)
- [Trino Memory connector](https://trino.io/docs/current/connector/memory.html)
- [Trino Iceberg connector](https://trino.io/docs/current/connector/iceberg.html)
- [Trino Delta Lake connector](https://trino.io/docs/current/connector/delta-lake.html)

Versions, file hashes and download URLs are recorded in `sources.lock.json`. The compiled dependency graph is frozen by this lab's `Cargo.lock`.
