# Install the experimental dbt v2 Trino build

These archives come from this fork's GitHub Actions workflow (`trino-fork-build.yml`). They are
**not official dbt Labs releases**; use them to evaluate the adapter before it is available
upstream. There are builds for Linux x86_64 and macOS on Apple silicon only.

Each archive contains:

```
bin/dbt                          dbt v2 OSS CLI with the Trino adapter
lib/libadbc_driver_trino.so      ADBC Trino driver go/v0.5.3 (adbc-drivers/trino, Apache-2.0);
                                 libadbc_driver_trino.dylib in the macOS archive
lib/LICENSE.adbc-driver-trino, lib/NOTICE.adbc-driver-trino
LICENSE, INSTALL.md
BUILD-INFO                       the git ref, the commit SHA and the workflow run of the build
```

`dbt` finds the driver in the `lib/` folder next to `bin/`. Nothing is downloaded at run time.

## Get an archive

### From a GitHub release

A `trino-v*` tag publishes a GitHub release. The archive names contain the tag, for example
`trino-v0.1.0`:

```sh
TAG=trino-v0.1.0
TARGET=x86_64-unknown-linux-gnu      # or aarch64-apple-darwin
BASE=https://github.com/abhishekguha996-ux/dbt-trino-v2/releases/download/$TAG
curl -fLO "$BASE/dbt-trino-v2-$TAG-$TARGET.tar.gz"
curl -fLO "$BASE/dbt-trino-v2-$TAG-$TARGET.tar.gz.sha256"
sha256sum -c "dbt-trino-v2-$TAG-$TARGET.tar.gz.sha256"     # macOS: shasum -a 256 -c ...
```

No release exists yet. Until there is one, use a workflow build.

### From a workflow build

Each build of a branch keeps its archives for 90 days as workflow artifacts. Their names
contain the branch and the short commit SHA, for example
`dbt-trino-v2-trino-v2-adapter-1ff8a11-x86_64-unknown-linux-gnu`. You must be logged in to
GitHub (`gh auth login`) to download them:

```sh
REPO=abhishekguha996-ux/dbt-trino-v2
gh run list -R $REPO --workflow trino-fork-build.yml --branch trino-v2-adapter --status success --limit 1
gh run view <run-id> -R $REPO               # the ARTIFACTS section lists the archive names
gh run download <run-id> -R $REPO -n <archive name>
sha256sum -c dbt-trino-v2-*.tar.gz.sha256   # macOS: shasum -a 256 -c ...
```

## Linux x86_64 (for example a Coder workspace)

The binary is built in a `manylinux_2_28` container and needs glibc 2.28 or newer
(Ubuntu 20.04+, Debian 10+, RHEL/Alma 8+).

```sh
sudo mkdir -p /opt/dbt-trino-v2
sudo tar -xzf dbt-trino-v2-*-x86_64-unknown-linux-gnu.tar.gz -C /opt/dbt-trino-v2 --strip-components=1
export PATH=/opt/dbt-trino-v2/bin:$PATH
export DBT_ALLOW_EXPERIMENTAL_ADAPTERS=yes   # Trino is gated as experimental in dbt v2
dbt --version
cat /opt/dbt-trino-v2/BUILD-INFO
```

In Coder, add the two `export` lines to the workspace template or `~/.profile`. Install to a
path outside `/usr/local/bin` so the build doesn't shadow an existing dbt v1 installation, and
keep dbt v1 available until the migration is complete.

## macOS (Apple silicon)

The ADBC Trino driver has no build for Intel Macs, so there is no Intel archive.

```sh
mkdir -p ~/opt/dbt-trino-v2
tar -xzf dbt-trino-v2-*-aarch64-apple-darwin.tar.gz -C ~/opt/dbt-trino-v2 --strip-components=1
xattr -dr com.apple.quarantine ~/opt/dbt-trino-v2   # only if a web browser downloaded the archive
export PATH="$HOME/opt/dbt-trino-v2/bin:$PATH"
export DBT_ALLOW_EXPERIMENTAL_ADAPTERS=yes
dbt --version
```

The binary and the driver are not signed. A web browser marks downloads with the
`com.apple.quarantine` attribute, and macOS then blocks the binary and the driver; the `xattr`
command removes the mark. `curl` and `gh` do not set it.

Do not link `bin/dbt` into another folder (for example `ln -s ~/opt/dbt-trino-v2/bin/dbt
/opt/homebrew/bin/dbt`). On macOS, dbt then looks for `lib/` next to the link and does not
find the driver. Put the archive's `bin/` folder on `PATH` instead, or set `ADBC_DRIVER_PATH`
(see below).

## How dbt finds the driver

dbt loads the driver by its name, `adbc_driver_trino`. It looks in these places, in this
order:

1. Each folder in `ADBC_DRIVER_PATH` (a `:`-separated list).
2. The first `lib/` folder in the folder of the `dbt` executable or up to five folders above
   it. For the archive, this is the `lib/` folder next to `bin/`.
3. `/opt/homebrew/lib` (macOS on Apple silicon only).
4. Your ADBC driver folder: `~/.config/adbc/drivers` on Linux (`$XDG_CONFIG_HOME/adbc/drivers`
   if that is set), `~/Library/Application Support/ADBC/Drivers` on macOS.
5. The system ADBC driver folder: `/etc/adbc/drivers` on Linux,
   `/Library/Application Support/ADBC/Drivers` on macOS.
6. Last, the operating system's own library search for the file name (for example
   `LD_LIBRARY_PATH` on Linux or `DYLD_LIBRARY_PATH` on macOS).

In each folder of steps 1-5, dbt first looks for a driver manifest named
`adbc_driver_trino.toml`, then for the library `libadbc_driver_trino.so` (Linux) or
`libadbc_driver_trino.dylib` (macOS).

To keep the library somewhere else, write a manifest with that name into one of these folders,
for example `~/.config/adbc/drivers/adbc_driver_trino.toml`:

```toml
manifest_version = 1

[Driver]
shared = "/opt/adbc/trino/libadbc_driver_trino.so"
```

### Drivers installed with dbc

The driver's own documentation installs it with `dbc install trino`. That writes a manifest
named `trino.toml`, and dbt does not find it, because dbt looks for `adbc_driver_trino`. Copy
the manifest to the name that dbt uses:

```sh
# Linux
cp ~/.config/adbc/drivers/trino.toml ~/.config/adbc/drivers/adbc_driver_trino.toml
# macOS
cd ~/Library/Application\ Support/ADBC/Drivers && cp trino.toml adbc_driver_trino.toml
```

With a Python virtual environment active, `dbc` installs into `$VIRTUAL_ENV/etc/adbc/drivers`.
dbt does not search that folder, so copy the manifest there and add the folder to
`ADBC_DRIVER_PATH`:

```sh
cp "$VIRTUAL_ENV/etc/adbc/drivers/trino.toml" "$VIRTUAL_ENV/etc/adbc/drivers/adbc_driver_trino.toml"
export ADBC_DRIVER_PATH="$VIRTUAL_ENV/etc/adbc/drivers"
```

### "Driver not found" looks like a credentials error

When dbt cannot load the driver, `dbt debug` reports an authentication failure:

```
[error] [AuthenticationFailed (dbt1011)]: dbt was unable to connect to the database configured for the `trino` adapter.
The following error was returned:
Driver not found: adbc_driver_trino
```

and it asks you to check your credentials. The credentials are not the cause: dbt did not find
the driver. Check the places listed above.

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
      host: trino.internal.example.com   # host name only: no scheme, port or path
      port: 443
      user: "{{ env_var('TRINO_USER') }}"
      password: "{{ env_var('TRINO_PASSWORD') }}"
      catalog: hive           # alias of `database`
      schema: analytics
      threads: 8
      cert: /etc/ssl/certs/internal-ca.pem   # CA bundle; without `cert`, the system trust store
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
export ADBC_DRIVER_PATH="$PWD/lib"
```

The driver archives are on the
[adbc-drivers/trino releases page](https://github.com/adbc-drivers/trino/releases) (tested:
`go/v0.5.3`).
