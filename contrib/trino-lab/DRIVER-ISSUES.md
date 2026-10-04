# Issues for adbc-drivers/trino (not filed yet)

These are ready-to-file issue texts for <https://github.com/adbc-drivers/trino/issues>. None of
them is filed yet (4 October 2026); until they are, describe these limits as "to be reported",
not "reported".

Before you file:

1. Search the open and closed issues again. On 4 October 2026 these issues were related:
   - #19 "Add support for more complex data types such as ARRAY, MAP, ROW", open since
     21 October 2025. Post the [MAP and ROW evidence](#map-and-row-values-comment-on-19) there
     as a comment; do not file it as a new issue.
   - #94 "ARRAY columns returned as arrow.opaque instead of Arrow List type", the ARRAY
     sub-issue of #19, closed in June 2026.
   - #84 (query ID) and #51 (`SSLVerification=NONE`), both closed.

   No issue covers the other sections.
2. File one issue per section, except the comment for #19. Copy the text between the `~~~`
   lines.
3. Afterwards, put the issue links into [UPSTREAM.md](UPSTREAM.md#umbrella-issue),
   [MIGRATION.md](MIGRATION.md) and [FEATURES.md](FEATURES.md).

Tested versions: driver `go/v0.5.3` (it pins trino-go-client v0.333.0 and driverbase-go
`31a68ee`), Trino 483 (`trinodb/trino:483`), Python `adbc-driver-manager` 1.12.0 for the
driver-only repros. The driver's `main` branch (`853e695`) moved to trino-go-client v0.336.0.

## Cancel does not stop a running query

Title: `AdbcStatementCancel returns OK but the Trino query keeps running`

~~~markdown
**Summary**

`AdbcStatementCancel` returns `ADBC_STATUS_OK`, but the query keeps running on Trino. This is
true while `AdbcStatementExecuteQuery` is still running and while the result stream is read.
The query runs until it finishes, or until Trino abandons it after `query.client.timeout`
(5 minutes by default) when the client stops polling.

**Environment**

adbc-drivers/trino go/v0.5.3 (macos_arm64 and linux_amd64 archives), Trino 483,
adbc-driver-manager 1.12.0 (Python).

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
`ExecuteQuery` fails with "failed to create record reader: ... Query killed".

**Cause, as far as we can see**

- `sqlwrapper.StatementImplBase.ExecuteQuery` (driverbase-go `31a68ee`, and still on `main`)
  starts the record reader with `context.Background()` on purpose, with a
  `TODO(lidavidm): when given ctx is cancelled, cancel the query, but not in a way that breaks
  the connection!`. So cancelling the context of the call never reaches trino-go-client.
- The generated `go/pkg/driver.go` in go/v0.5.3 predates driverbase-go #211: its
  `TrinoStatementCancel` only cancels that call context. The current ffitemplate calls a
  `driverbase.StatementCanceler` if the statement implements one.

**Possible fix**

Implement `driverbase.StatementCanceler` for `trinoStatement`: send
`DELETE /v1/query/<query id>` (what trino-go-client's `driverRows.Close` does), using the
query ID that the statement already records for `trino.statement.last_query_id`, and
regenerate `go/pkg/driver.go` with the current ffitemplate.

**Context**

We use the driver in the dbt v2 Trino adapter. On Ctrl-C, dbt stops, but the model's query
keeps running on the cluster.
~~~

## The timezone parameter is ignored

Title: `Release with trino-go-client v0.336.0 or later: the timezone parameter is ignored`

~~~markdown
**Summary**

With driver go/v0.5.3, the `timezone` URI parameter has no effect: the session always uses the
time zone of the Trino server. go/v0.5.3 pins trino-go-client v0.333.0, which has no `timezone`
DSN parameter. trino-go-client v0.336.0 reads it and sends `X-Trino-Time-Zone`. The driver's
`main` branch (`853e695`) already uses v0.336.0, but no release has it yet.

**Environment**

adbc-drivers/trino go/v0.5.3, Trino 483 (server time zone UTC), adbc-driver-manager 1.12.0
(Python).

**Steps to reproduce**

```python
import adbc_driver_manager.dbapi as dbapi

uri = "trino://admin@localhost:8080/memory?SSL=false&timezone=America/New_York"
with dbapi.connect(driver="trino", db_kwargs={"uri": uri}) as conn, conn.cursor() as cur:
    cur.execute("select current_timezone()")
    print(cur.fetchall())
```

**Expected**

`[('America/New_York',)]`

**Actual**

`[('UTC',)]`, the server's time zone. The `http://` form of the URI
(`http://admin@localhost:8080?catalog=memory&timezone=America/New_York`) gives the same result.

**Request**

A driver release with trino-go-client v0.336.0 or later. Note that v0.336.0 also changes the
default: without `timezone`, it sends the time zone of the client machine (`TZ` or
`/etc/localtime`), as the Trino Python client does.

**Context**

The dbt v2 Trino adapter passes the `timezone` profile field as this parameter. With
go/v0.5.3, `dbt show --inline "select current_timezone() as tz"` and a profile with
`timezone: America/New_York` prints `UTC`. dbt-trino v1 gets the profile's time zone (or the
local time zone) through the Python client.
~~~

## Client certificate (mTLS) authentication

Title: `Support client certificate (mutual TLS) authentication`

~~~markdown
**Summary**

Some Trino clusters authenticate clients with TLS client certificates
(`http-server.authentication.type=CERTIFICATE`). The driver has no option for a client
certificate and key, so it cannot connect to them.

**Details**

The driver already builds its own `http.Client` and `tls.Config` (`registerCustomClientForTimeout`
and `buildTLSConfig` in `go/db_factory.go`) for `SSLCertPath`, `SSLCert` and
`SSLVerification`. A client certificate fits there: load a PEM certificate and key and set
`tls.Config.Certificates`. trino-go-client itself offers this only through a registered custom
client, which a C/ADBC caller cannot register.

**Request**

URI parameters (or ADBC options) for a client certificate and its private key, for example
PEM file paths. The Trino JDBC driver and the Python client support this (dbt-trino v1:
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
- HyperLogLog, P4HyperLogLog, QDigest, TDigest and SetDigest as binary. trino-go-client
  v0.336.0 (already on `main`) decodes unknown types as bytes, which may fix this part.
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
