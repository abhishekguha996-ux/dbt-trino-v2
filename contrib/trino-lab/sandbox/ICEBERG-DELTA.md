# Local Iceberg and Delta fixtures

This single-node lab keeps metadata and table files in the named Trino data volume. It uses no cloud account, object store, external metastore or host directory.

Trino 483 selects the Iceberg file metastore with `iceberg.catalog.type=testing_file_metastore`. Delta uses `hive.metastore=file`. These settings are for this disposable test environment. They do not establish production metastore compatibility.

`local.location=/data/trino` is a filesystem path in Trino 483. Table and metastore locations use `local:///...` URIs relative to that root. The 483 documentation example uses a URI for `local.location`, but the 483 implementation takes a Java Path and rejects that example at startup. The tested configuration follows the implementation.

Sources:
- https://github.com/trinodb/trino/blob/483/plugin/trino-iceberg/src/main/java/io/trino/plugin/iceberg/catalog/IcebergCatalogModule.java
- https://github.com/trinodb/trino/blob/483/plugin/trino-delta-lake/src/main/java/io/trino/plugin/deltalake/metastore/DeltaLakeMetastoreModule.java
- https://github.com/trinodb/trino/blob/483/lib/trino-filesystem/src/main/java/io/trino/filesystem/local/LocalFileSystemConfig.java

Trino 483 has no local-filesystem transaction-log synchronizer for Delta updates. The non-concurrent-writes flag does not add one. The lab tests Delta CTAS, reads, and table rebuilds; it does not claim Delta INSERT/MERGE support with this storage configuration. Source: https://github.com/trinodb/trino/blob/483/plugin/trino-delta-lake/src/main/java/io/trino/plugin/deltalake/DeltaLakeSynchronizerModule.java
