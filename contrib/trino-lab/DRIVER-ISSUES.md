# Issues for adbc-drivers/trino (not filed yet)

These are ready-to-file issue texts for <https://github.com/adbc-drivers/trino/issues>. None of
them is filed yet (19 October 2026); until they are, describe these limits as "to be reported",
not "reported". The texts were checked again on 19 October with driver go/v0.6.1 (see
[What changed in go/v0.6.1](#what-changed-in-gov061)).

Before you file:

1. Search the open and closed issues again. On 19 October 2026 these issues were related:
   - #19 "Add support for more complex data types such as ARRAY, MAP, ROW", open since
     21 October 2025. Post the [MAP and ROW evidence](#map-and-row-values-comment-on-19) there
     as a comment; do not file it as a new issue.
   - #94 "ARRAY columns returned as arrow.opaque instead of Arrow List type", the ARRAY
     sub-issue of #19, closed in June 2026.
   - #84 (query ID) and #51 (`SSLVerification=NONE`), both closed.
   - #42 (transactions, closed by #120 in go/v0.6.0) and #124 (`timezone` failed on go/v0.6.0,
     closed by #125 in go/v0.6.1).

   No issue covers the other sections.
2. File one issue per section, except the comment for #19. Copy the text between the `~~~`
   lines.
3. Afterwards, put the issue links into [UPSTREAM.md](UPSTREAM.md#umbrella-issue),
   [MIGRATION.md](MIGRATION.md) and [FEATURES.md](FEATURES.md).

Tested versions: driver `go/v0.6.1` (15 October 2026; its `go.mod` pins trino-go-client
v1.3.0 and driverbase-go `bb49cea`) and, for the first texts, `go/v0.5.3` (trino-go-client
v0.333.0, driverbase-go `31a68ee`); Trino 483 (`trinodb/trino:483`); Python
`adbc-driver-manager` 1.12.0 for the driver-only repros on go/v0.5.3. On go/v0.6.1 the checks
ran through the dbt v2 Trino adapter (`dbt run-operation` with `run_query`, `dbt show` and the
functional suite), because no Python ADBC manager was installed on that host.

## What changed in go/v0.6.1

Checked on 19 October 2026 with the macos_arm64 archive (sha256
`dec1d6d6c898d89ddf52e389e9a766029f484417fe37d846a73736d2f28c4120`), the dbt v2 Trino adapter
on dbt-labs `main` 112adf8, and Trino 483. The functional suite (98 tests, 97 pass, the Ctrl-C
test is an expected failure) and the jaffle-shop-classic build pass with it, as with
go/v0.5.3.

| Section | go/v0.6.1 | What to do |
|---|---|---|
| [Cancel](#cancel-does-not-stop-a-running-query) | Not fixed: the query keeps running after Ctrl-C | File it, with go/v0.6.1 |
| [Timezone](#the-timezone-parameter-is-fixed-in-gov061) | **Fixed**: `timezone` sets the session time zone | Do not file |
| [mTLS](#client-certificate-mtls-authentication) | trino-go-client v1.3.0 has client certificates, but the driver's own HTTP client blocks them | File it, with the new cause |
| [OAuth 2.0](#oauth-20-authentication), [impersonation](#session-user-impersonation), [HTTP headers](#custom-http-headers) | No change found in the source | File them |
| [Kerberos ticket cache](#kerberos-ticket-cache) | trino-go-client v1.3.0 has `KerberosCredentialCachePath`; not tested live | Test it first; probably do not file |
| [MAP and ROW](#map-and-row-values-comment-on-19) | MAP unchanged; ROW text changed to `{[x y] [1 a] true}` | Comment on #19, with go/v0.6.1 |
| [TIME WITH TIME ZONE, HyperLogLog](#time-with-time-zone-and-hyperloglog-values) | TIME WITH TIME ZONE unchanged; HyperLogLog no longer fails, but is Go-formatted text | File it, with go/v0.6.1 |
| [Manifest name](#manifest-name-trino-vs-adbc_driver_trino) | The archive's `MANIFEST` is unchanged | File it |

go/v0.6.0 also added transactions (#120). The adapter runs in autocommit, as dbt-trino v1 does,
and the suite shows no change.

## Cancel does not stop a running query

Title: `AdbcStatementCancel returns OK but the Trino query keeps running`

~~~markdown
**Summary**

`AdbcStatementCancel` returns `ADBC_STATUS_OK`, but the query keeps running on Trino. This is
true while `AdbcStatementExecuteQuery` is still running and while the result stream is read.
The query runs until it finishes, or until Trino abandons it after `query.client.timeout`
(5 minutes by default) when the client stops polling.

**Environment**

adbc-drivers/trino go/v0.5.3 (macos_arm64 and linux_amd64 archives) and go/v0.6.1
(macos_arm64), Trino 483, adbc-driver-manager 1.12.0 (Python).

**Steps to reproduce**

```python
import threading, time
import adbc_driver_manager.dbapi as dbapi

conn = dbapi.connect(driver="trino",  # or the path to libadbc_driver_trino.so/.dylib
                     db_kwargs={"uri": "trino://admin@localhost:8080/tpch/sf1?SSL=false"})
cur = conn.cursor()
sql = ("select 'cancel_marker' as m, count(*) "
       "from tpch.sf1.lineitem a cross join tpch.sf1.lineitem b")
threading.Thread(target=lambda: (cur.execute(sql), cur.fetchall()), daemon=True).start()
time.sleep(10)     # the query is RUNNING on Trino
cur.adbc_cancel()  # AdbcStatementCancel: returns without an error
time.sleep(20)
# On Trino: select state from system.runtime.queries where query like '%cancel_marker%'
```

**Expected**

The query is cancelled on Trino (state `FAILED`, `USER_CANCELED`) and the pending
`ExecuteQuery` or stream read returns an error.

**Actual**

```
15:17:40 query 20261004_183219_09390_rejgn RUNNING (ExecuteQuery has not returned yet)
15:17:42 AdbcStatementCancel returned OK
15:18:03 state 20 s after the cancel: RUNNING
```

The query stops only when it is killed on the server (`system.runtime.kill_query`); then
`ExecuteQuery` fails with "failed to create record reader: ... Query killed". The output above
is from go/v0.5.3. go/v0.6.1 behaves the same: after a Ctrl-C of dbt, the query is still
`RUNNING` on Trino.

**Cause, as far as we can see**

- `sqlwrapper.StatementImplBase.ExecuteQuery` (driverbase-go `31a68ee`, and still on `main`)
  starts the record reader with `context.Background()` on purpose, with a
  `TODO(lidavidm): when given ctx is cancelled, cancel the query, but not in a way that breaks
  the connection!`. So cancelling the context of the call never reaches trino-go-client.
- In go/v0.6.1, `go/pkg/driver.go` is regenerated: `TrinoStatementCancel` cancels the
  execution context and calls a `driverbase.StatementCanceler` if the statement implements
  one. `trinoStatement` (`go/statement.go`) does not implement it, and driverbase-go
  `bb49cea` still starts the record reader with `context.Background()` (same TODO). So the
  cancel still never reaches Trino. (go/v0.5.3's `driver.go` predated driverbase-go #211 and
  only cancelled the call context.)

**Possible fix**

Implement `driverbase.StatementCanceler` for `trinoStatement`: send
`DELETE /v1/query/<query id>` (what trino-go-client's `driverRows.Close` does), using the
query ID that the statement already records for `trino.statement.last_query_id`.

**Context**

We use the driver in the dbt v2 Trino adapter. On Ctrl-C, dbt stops, but the model's query
keeps running on the cluster.
~~~

## The timezone parameter is fixed in go/v0.6.1

**Do not file this issue.** go/v0.5.3 ignored the `timezone` URI parameter, because it pinned
trino-go-client v0.333.0. go/v0.6.0 moved to a client that reads it, but failed to connect
with it (#124, no time zone data in the shared library). go/v0.6.1 bundles the time zone data
(#125), and `timezone` works.

Checked on 19 October 2026 with `dbt show --inline "select current_timezone() as tz"` on a
server in UTC, on a Mac in America/New_York:

| Profile | go/v0.5.3 | go/v0.6.1 |
|---|---|---|
| `timezone: America/New_York` | `UTC` | `America/New_York` |
| `timezone: UTC` | `UTC` | `UTC` |
| no `timezone` | `UTC` (the server's) | `America/New_York` (the client's) |
| no `timezone`, `TZ=Asia/Kolkata` | not checked | `Asia/Kolkata` |

Without `timezone`, go/v0.6.1 sends the time zone of the client machine (`TZ` or
`/etc/localtime`), as the Trino Python client and dbt-trino v1 do. The earlier issue text is in
the git history of this file.

## Client certificate (mTLS) authentication

Title: `Support client certificate (mutual TLS) authentication`

~~~markdown
**Summary**

Some Trino clusters authenticate clients with TLS client certificates
(`http-server.authentication.type=CERTIFICATE`). The driver has no option for a client
certificate and key, so it cannot connect to them.

**Details** (go/v0.6.1)

trino-go-client v1.3.0, which go/v0.6.1 pins, has the DSN parameters `SSLClientCertPath`,
`SSLClientCert`, `SSLClientKeyPath` and `SSLClientKey`. But the driver always registers its own
`http.Client` (`registerCustomClientForTimeout` and `buildTLSConfig` in `go/db_factory.go`)
and sets `custom_client`. It moves `SSLCertPath`, `SSLCert` and `SSLVerification` into that
client's `tls.Config`, but not the client certificate parameters. trino-go-client refuses
client certificates together with a custom client (`validateCustomClientTLS`: "client
certificates ... cannot be combined with a custom client"). So the new parameters cannot be
used through the driver. We read this in the source and did not test it against a server
with certificate authentication.

**Request**

Load the client certificate and key in `buildTLSConfig` (set `tls.Config.Certificates`) and
remove the parameters from the DSN, as the driver already does for `SSLCert`, so that the
`SSLClientCert*` and `SSLClientKey*` parameters of trino-go-client work through the driver. The Trino JDBC driver and the Python client support this (dbt-trino v1:
`method: certificate` with `client_certificate` and `client_private_key`).

**Context**

dbt v2 Trino adapter: profiles with `method: certificate` fail today with a clear error.
~~~

## OAuth 2.0 authentication

Title: `Support Trino OAuth 2.0 external authentication`

~~~markdown
**Summary**

The driver supports a static access token (`accessToken`), but not Trino's OAuth 2.0 flow, in
which the server answers `401` with `WWW-Authenticate: Bearer x_redirect_server="...",
x_token_server="..."`, the user opens the redirect URL, and the client polls the token server.

**Request**

Support the external-authentication flow, at least the variant that prints the redirect URL
and polls the token server (no browser or keyring needed), so it works on headless hosts.
The Trino JDBC driver (`externalAuthentication`) and the Python client
(`OAuth2Authentication`) have it; dbt-trino v1 exposes it as `method: oauth` and
`method: oauth_console`. trino-go-client has no such flow, so it may need work there too.

**Context**

dbt v2 Trino adapter: users must get a JWT themselves and use `method: jwt` today.
~~~

## Session user (impersonation)

Title: `Allow a session user that differs from the authenticated user`

~~~markdown
**Summary**

With password authentication, trino-go-client uses the URI user for both HTTP Basic
authentication and the `X-Trino-User` header. There is no way to authenticate as one user and
run queries as another (Trino impersonation, allowed by the cluster's access control).

**Request**

A URI parameter or ADBC option for the session user that sets `X-Trino-User`, like the Trino
JDBC driver's `sessionUser` parameter. dbt-trino v1 calls it `impersonation_user`.

**Context**

dbt v2 Trino adapter: profiles with `impersonation_user` fail today with a clear error.
~~~

## Custom HTTP headers

Title: `Allow extra HTTP headers on Trino requests`

~~~markdown
**Summary**

Some deployments put a gateway or proxy in front of Trino that needs extra request headers.
The driver has no option to add HTTP headers.

**Request**

A URI parameter or ADBC option with extra headers, added by the driver's own HTTP transport
(the `http.Client` that `go/db_factory.go` already builds) to every request. Headers that the
client sets itself (`X-Trino-User`, `X-Trino-Catalog`, ...) could be refused, as the Python
client does. A statement-level option would also allow per-query routing headers.

**Context**

dbt-trino v1 has a profile field `http_headers` and, from 1.10, per-model `client_tags` and
`http_headers` routing. The dbt v2 Trino adapter rejects `http_headers` today.
~~~

## Kerberos ticket cache

Title: `Support Kerberos authentication with a ticket cache (no keytab)`

**Test this before you file it.** trino-go-client v1.3.0, which go/v0.6.1 pins, adds the DSN
parameter `KerberosCredentialCachePath` (default `KRB5CCNAME`, then `/tmp/krb5cc_<uid>`) and
logs in with `client.NewFromCCache` when no keytab is given. The driver passes the query
parameters of a `trino://` URI to the DSN, so this probably works with go/v0.6.1 already. It
was not tested: the lab has no KDC. If it works, do not file the issue; the dbt v2 Trino
adapter then needs a change of its own to accept `method: gssapi`. The text below is for
go/v0.5.3.

~~~markdown
**Summary**

Kerberos works only with a keytab: trino-go-client loads `KerberosKeytabPath` with
`keytab.Load` and logs in with `client.NewWithKeytab`. Many users authenticate with `kinit`
and have only a credential cache.

**Request**

Support a ticket cache, for example a `KerberosCredCachePath` parameter that defaults to
`KRB5CCNAME`. gokrb5 has `credentials.LoadCCache` and `client.NewFromCCache`, so this is
probably a trino-go-client change that the driver then exposes.

**Context**

dbt-trino v1 supports this with `method: gssapi`, which uses the ticket cache. The dbt v2 Trino
adapter requires a keytab today.
~~~

## MAP and ROW values: comment on #19

Post this as a comment on <https://github.com/adbc-drivers/trino/issues/19>, not as a new
issue.

~~~markdown
Evidence for MAP and ROW with go/v0.5.3, Trino 483 and adbc-driver-manager 1.12.0 (Python):
both types come back as the `arrow.opaque` extension type over `string`, and the text is Go's
`%v` formatting of the decoded value (sqlwrapper's default inserter). The text is hard to parse
and differs from other Trino clients.

| Query | Arrow type | Value |
|---|---|---|
| `select map(array['a'], array[1])` | `arrow.opaque[storage_type=string, type_name=MAP(VARCHAR(1), INTEGER)]` | `map[a:1]` |
| `select cast(row(1, 'a') as row(x integer, y varchar))` | `arrow.opaque[..., type_name=ROW(X INTEGER, Y VARCHAR)]` | `[1 a]` |

With go/v0.6.1 (checked on 19 October 2026 through dbt's `run_query`), MAP is unchanged
(`map[a:1]`), and the ROW text changed to `{[x y] [1 a] true}`: Go's `%v` of the new row
value, with the field names, the values and a validity flag.

ARRAY is fine since #94: `select array[1, 2]` gives `list<int64>`. For MAP and ROW we would
expect the Arrow `map` and `struct` types (the Python client returns a dict and a tuple), or at
least JSON text (`{"a": 1}`, `[1, "a"]`).

Context: we use the driver in the dbt v2 Trino adapter, where `run_query` results for these
types differ from dbt-trino v1.
~~~

## TIME WITH TIME ZONE and HyperLogLog values

Title: `TIME WITH TIME ZONE values are Go-formatted text; HyperLogLog fails`

~~~markdown
**Summary**

TIME WITH TIME ZONE values come back as the `arrow.opaque` extension type over `string`, and
the text is Go's `%v` formatting of the decoded value (sqlwrapper's default inserter).
HyperLogLog values fail. MAP and ROW values have the same formatting; #19 covers them.

**Steps to reproduce** (Python, adbc-driver-manager 1.12.0)

```python
cur.execute(sql); print(cur.fetch_arrow_table())
```

| Query | Arrow type | Value |
|---|---|---|
| `select time '01:02:03.456 +05:00'` | `arrow.opaque[..., type_name=TIME WITH TIME ZONE]` | `0000-01-01 01:02:03.456 +0500 +0500` |
| `select approx_set(1)` | error | `type not supported: "HyperLogLog"` |
| `select uuid '12151fd2-...'` | `arrow.uuid` | correct |

**Expected**

- TIME WITH TIME ZONE as ISO 8601 text (`01:02:03.456+05:00`) or a typed representation.
- HyperLogLog, P4HyperLogLog, QDigest, TDigest and SetDigest as binary. With go/v0.6.1
  (checked on 19 October 2026 through dbt's `run_query`), `select approx_set(1)` no longer
  fails, but the value is text of a Go byte list, `[2 12 1 0 128 3 68 0]`, not binary.
  TIME WITH TIME ZONE is unchanged on go/v0.6.1.
- The type table in the driver docs lists UUID, MAP, ROW, JSON and TIME WITH TIME ZONE.

**Context**

dbt v2 Trino adapter: `run_query` results differ from dbt-trino v1 for these types. Related:
#19.
~~~

## Manifest name: trino vs adbc_driver_trino

Title: `Which driver name should applications load: trino or adbc_driver_trino?`

~~~markdown
**Summary**

`dbc install trino` writes a manifest named `trino.toml`. Applications that load drivers by
the library-name convention look for `adbc_driver_trino` (`adbc_driver_trino.toml` or
`libadbc_driver_trino.so`) and do not find a dbc install. dbt v2 is one of them: its Trino
adapter loads `adbc_driver_trino` and reports "Driver not found: adbc_driver_trino" after
`dbc install trino`. Copying the manifest to `adbc_driver_trino.toml` works.

**Questions**

1. Which name should applications use to load this driver?
2. Could `dbc` also install the manifest as `adbc_driver_trino.toml`, or could the docs explain
   the two names?
3. Could the docs describe a manual install (download, check the digest, where to put the
   library), for hosts without `dbc`?

**Note**

With a Python virtual environment active, `dbc` installs into `$VIRTUAL_ENV/etc/adbc/drivers`.
dbt's driver manager does not search that folder; that part is for dbt, not this driver.
~~~
