# Install the experimental dbt v2 Trino build

These archives come from the `trino-v2-adapter` branch of this fork. They are **not official
dbt Labs releases**; use them to evaluate the adapter before it is available upstream.

Each archive contains:

```
bin/dbt                          dbt v2 OSS CLI with the Trino adapter
lib/libadbc_driver_trino.so      ADBC Trino driver go/v0.5.3 (adbc-drivers/trino, Apache-2.0)
lib/LICENSE.adbc-driver-trino
LICENSE, INSTALL.md
```

`dbt` finds the driver in the `lib/` directory next to `bin/`. It can also load it from the
system library path (`LD_LIBRARY_PATH`, `/usr/local/lib`, or `/opt/homebrew/lib` on macOS).
Nothing is downloaded at runtime.

## Linux x86_64 (for example a Coder workspace)

The binary is built in a `manylinux_2_28` container and needs glibc 2.28 or newer
(Ubuntu 20.04+, Debian 10+, RHEL/Alma 8+).

```sh
VERSION=<release tag or artifact name>
curl -LO "https://github.com/abhishekguha996-ux/dbt-trino-v2/releases/download/${VERSION}/dbt-trino-v2-${VERSION}-x86_64-unknown-linux-gnu.tar.gz"
curl -LO "https://github.com/abhishekguha996-ux/dbt-trino-v2/releases/download/${VERSION}/dbt-trino-v2-${VERSION}-x86_64-unknown-linux-gnu.tar.gz.sha256"
sha256sum -c dbt-trino-v2-*.tar.gz.sha256

sudo mkdir -p /opt/dbt-trino-v2
sudo tar -xzf dbt-trino-v2-*.tar.gz -C /opt/dbt-trino-v2 --strip-components=1
export PATH=/opt/dbt-trino-v2/bin:$PATH
export DBT_ALLOW_EXPERIMENTAL_ADAPTERS=yes   # Trino is gated as experimental in dbt v2
dbt --version
```

In Coder, add the two `export` lines to the workspace template or `~/.profile`. Install to a
path outside `/usr/local/bin` so the build doesn't shadow an existing dbt v1 installation, and
keep dbt v1 available until the migration is complete.

Artifacts from branch builds (not tags) are attached to the workflow run under **Actions →
Trino adapter build (fork)** and can be downloaded with
`gh run download <run-id> -R abhishekguha996-ux/dbt-trino-v2`.

## Profile

Existing dbt-trino v1 profiles load unchanged, except for the options in
[the migration guide](MIGRATION.md#profile-differences). A typical HTTPS profile:

```yaml
analytics:
  target: prod
  outputs:
    prod:
      type: trino
      method: ldap            # none | ldap | jwt | kerberos
      host: trino.internal.example.com
      port: 443
      user: "{{ env_var('TRINO_USER') }}"
      password: "{{ env_var('TRINO_PASSWORD') }}"
      catalog: hive           # alias of `database`
      schema: analytics
      threads: 8
      cert: /etc/ssl/certs/internal-ca.pem   # CA bundle; `false` disables verification
      session_properties:
        query_max_run_time: 2h
      roles:
        hive: analyst
```

Verify the connection:

```sh
dbt debug
```

## Build from source instead

```sh
git clone https://github.com/abhishekguha996-ux/dbt-trino-v2.git && cd dbt-trino-v2
cargo build --release -p dbt-sa-cli --bin dbt     # needs Rust (rust-toolchain.toml) and protoc
mkdir -p lib && cp /path/to/libadbc_driver_trino.* lib/
```
