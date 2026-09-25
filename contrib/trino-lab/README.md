# Experimental Trino adapter for dbt OSS v2

This fork adds Trino to dbt OSS 2.0.5, based on upstream commit `841c74e863df51b89d208b1ad0eca388aa0f32a4`. It uses the Apache Arrow ADBC Trino driver through dbt's existing generic driver backend. It does not add a Python adapter package or require dbt Cloud.

The adapter remains behind `DBT_ALLOW_EXPERIMENTAL_ADAPTERS=yes`. This is a development prototype, not an upstream-supported release. See [test results](TEST-RESULTS.md) for the tested scope and open limits.

## Use a profile

Install the correct ADBC Trino shared library for your OS. This lab uses Linux ARM64 driver release `go/v0.5.3`. Make `libadbc_driver_trino.so` available through `LD_LIBRARY_PATH`. The adapter loads the local library and does not download it at runtime.

```yaml
trino_project:
  target: dev
  outputs:
    dev:
      type: trino
      host: trino.example.test
      port: 8443
      user: "{{ env_var('TRINO_USER') }}"
      database: iceberg
      schema: analytics
      threads: 1
      http_scheme: https
      method: ldap
      password: "{{ env_var('TRINO_PASSWORD') }}"
```

`database` is the Trino catalog. `https` is the default. The port is required. For an unauthenticated local server, use `method: none` and omit the password. The disposable lab uses HTTP only on its isolated network. The adapter rejects passwords over HTTP, unsupported authentication methods, and role selection. It does not offer a switch to skip certificate validation.

## Run the disposable lab

Requirements: an Apple Silicon Mac, an existing Docker Desktop Linux VM, Python 3, and Git. The checked Docker context is `desktop-linux`. Do not install project dependencies or compile Rust on the Mac. The Python scripts on the Mac use the standard library to review configuration, download data, and control Docker.

Review [compose.yaml](sandbox/compose.yaml), the two Dockerfiles, the scripts, and the resource limits before running them. Run from this directory:

```sh
python3 scripts/run_lab.py prepare
python3 scripts/run_lab.py build
python3 scripts/run_lab.py test
```

Preparation downloads hash-locked source, driver and Python wheels, then downloads the dependencies selected by the committed Cargo lock. Docker image setup verifies Debian package signatures and records package versions. The Debian repositories are not snapshot-pinned, so the images are not bit-for-bit reproducible across dates.

The build phase first builds unchanged upstream code, then applies only the changed `crates/` files from this fork. It runs Rust tests and builds the candidate binary with one Cargo job. Cargo uses `--frozen`; the build container has no network.

Keep the Mac awake during tests. Sleep can expire an in-flight Trino task even while the guest process timer is paused. For a short test run on AC power, `caffeinate -i -s -t 600 python3 scripts/run_lab.py test` holds a temporary awake assertion; it does not change permanent power settings.

The test phase runs synthetic retail models, seeds, generic and singular data tests, repeated builds, catalog export, Memory append and Iceberg append/merge updates, Delta table rebuilds, TPCH joins checked against a separate Python calculation, TLS checks, and driver timeout/cancellation checks. The cancellation probe reports the known driver limit separately and stops its stress query with a server watchdog. A restart check verifies Iceberg and Delta persistence. The script stops lab services on exit and retains reports and data. Read reports after a failure before repeating a phase. Preparation refuses to overwrite an existing prepared lab.

```sh
python3 scripts/run_lab.py stop
```

This stops only containers with both lab ownership labels. It does not remove volumes. It does not restart or change other projects.

## Isolation and costs

Docker Desktop provides the existing Linux VM. The lab creates no cloud resources and needs no paid service. It has no host directory mounts, Docker socket, host ports, device access, or real credentials. Each container runs as a non-root user, drops all Linux capabilities, has a read-only root filesystem, and cannot gain privileges.

The offline builder is limited to 2 CPUs and 4 GiB RAM. Runtime uses up to 2 CPUs and 3.75 GiB RAM across Trino and the runner. Build and runtime phases run separately. Swap does not exceed the RAM limit. Trino queries have time and memory limits. Runtime has an internal network with no host gateway and no external DNS. The driver checks that external routing is unavailable. Named volumes hold all generated files inside Docker's Linux VM.

The 80 GiB workspace-volume budget is monitored, not a filesystem quota. Trino data and Docker images are outside that monitor; this fixture writes only small synthetic datasets. The Docker VM's disk limit is unchanged. These controls reduce risk; they cannot prove that a VM, Docker, or downloaded code has no defect. Stop the lab if the Mac becomes unresponsive. No global Docker cleanup command is needed.

## Data and storage

The retail fixture has customers, orders, products, order lines, split payments, refunds, missing matches, duplicate join keys, nulls and Unicode. Expected sales results are generated independently from the SQL models. All records are synthetic.

TPCH uses Trino's `tiny` generator. Tests exercise three-table and six-table joins and exact decimal revenue calculations. The Python oracle reads the raw source rows and computes its own joins and sums.

Iceberg and Delta use a local test metastore and the named data volume. See [storage configuration](sandbox/ICEBERG-DELTA.md). This does not test S3, a production Hive metastore, multiple workers, or concurrent Delta writers.

## Contribution and research

The initial public search found the upstream [Trino request #13131](https://github.com/dbt-labs/dbt/issues/13131), but no complete public v2 adapter. That search cannot rule out private work. No message or upstream pull request was sent. See [research notes](RESEARCH.md).

The implementation reuses generic relations, type conversion, metadata probes, and materializations. It adds no crate dependency and no new dbt-adbc methods. The generic merge macro has an optional source-qualified insert mode used by Trino; its default output is preserved.
