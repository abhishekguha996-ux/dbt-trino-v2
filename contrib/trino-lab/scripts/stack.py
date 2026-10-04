#!/usr/bin/env python3
"""Start, stop and inspect the local Trino lakehouse stack used by the lab.

Generates throwaway TLS, password and JWT material under stack/.generated
(ignored by git), then drives `docker compose`. Only standard library + the
openssl and htpasswd CLIs are used.

    python3 scripts/stack.py up        # generate secrets if missing, start, wait
    python3 scripts/stack.py down      # stop containers, keep volumes
    python3 scripts/stack.py reset     # stop and delete this stack's volumes
    python3 scripts/stack.py jwt USER  # print a JWT for USER
    python3 scripts/stack.py sql "select 1"
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

STACK = Path(__file__).resolve().parent.parent / "stack"
GEN = STACK / ".generated"
COMPOSE = ["docker", "compose", "-f", str(STACK / "compose.yaml")]

# Synthetic lab-only credentials. Never reuse outside this stack.
USERS = {"admin": "admin-lab-password", "user1": "user1-lab-password", "dbt_ldap": "ldap-lab-password"}


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kwargs)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generate() -> None:
    GEN.mkdir(exist_ok=True)
    ca_key, ca_crt = GEN / "ca.key", GEN / "ca.crt"
    if not ca_crt.exists():
        run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650",
             "-keyout", str(ca_key), "-out", str(ca_crt), "-subj", "/CN=dbt-trino-lab-ca",
             "-addext", "basicConstraints=critical,CA:TRUE",
             "-addext", "keyUsage=critical,keyCertSign,cRLSign"],
            capture_output=True)
    server_pem = GEN / "server.pem"
    if not server_pem.exists():
        key, csr, crt, ext = (GEN / n for n in ("server.key", "server.csr", "server.crt", "server.ext"))
        ext.write_text("subjectAltName=DNS:localhost,DNS:trino,IP:127.0.0.1\n"
                       "keyUsage=critical,digitalSignature,keyEncipherment\n"
                       "extendedKeyUsage=serverAuth\n")
        run(["openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key),
             "-out", str(csr), "-subj", "/CN=localhost"], capture_output=True)
        run(["openssl", "x509", "-req", "-in", str(csr), "-CA", str(ca_crt), "-CAkey", str(ca_key),
             "-CAcreateserial", "-days", "3650", "-out", str(crt), "-extfile", str(ext)],
            capture_output=True)
        server_pem.write_text(key.read_text() + crt.read_text())
    password_db = GEN / "password.db"
    if not password_db.exists():
        lines = []
        for user, password in USERS.items():
            out = run(["htpasswd", "-B", "-C", "10", "-nb", user, password],
                      capture_output=True, text=True).stdout.strip()
            lines.append(out)
        password_db.write_text("\n".join(lines) + "\n")
    jwt_key = GEN / "jwt-private.pem"
    if not jwt_key.exists():
        run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048",
             "-out", str(jwt_key)], capture_output=True)
        run(["openssl", "pkey", "-in", str(jwt_key), "-pubout", "-out", str(GEN / "jwt-public.pem")],
            capture_output=True)
    for path in GEN.iterdir():
        path.chmod(0o644)  # read by the non-root trino user inside the container


def jwt(user: str, ttl: int = 3600) -> str:
    header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = _b64url(json.dumps({"sub": user, "iat": now, "exp": now + ttl}).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = run(["openssl", "dgst", "-sha256", "-sign", str(GEN / "jwt-private.pem")],
              input=signing_input, capture_output=True).stdout
    return f"{header}.{payload}.{_b64url(sig)}"


def sql(statement: str, user: str = "admin") -> list:
    """Run a statement over HTTP using Trino's REST protocol; return all rows."""
    headers = {"X-Trino-User": user, "X-Trino-Role": "hive=ROLE{admin}"}
    req = urllib.request.Request("http://127.0.0.1:8080/v1/statement", data=statement.encode(),
                                 headers=headers)
    rows: list = []
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    while True:
        if "error" in body:
            raise RuntimeError(body["error"].get("message"))
        rows.extend(body.get("data", []))
        next_uri = body.get("nextUri")
        if not next_uri:
            return rows
        with urllib.request.urlopen(urllib.request.Request(next_uri, headers=headers)) as resp:
            body = json.load(resp)


def wait_ready(timeout: int = 300) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/v1/info", timeout=3) as resp:
                if not json.load(resp).get("starting", True):
                    # Metastore reachable and S3 writable?
                    for catalog in ("hive", "iceberg", "delta"):
                        schema = f"{catalog}.lab_probe"
                        sql(f"create schema if not exists {schema} "
                            f"with (location = 's3://datalake/lab_probe_{catalog}')")
                        sql(f"create table if not exists {schema}.t as select 1 as x")
                        assert sql(f"select x from {schema}.t") == [[1]]
                        sql(f"drop table {schema}.t")
                        sql(f"drop schema {schema}")
                    return
        except Exception as exc:  # noqa: BLE001 - keep polling until ready
            last = exc
        time.sleep(3)
    raise SystemExit(f"Trino stack did not become ready: {last}")


def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "up"
    if cmd == "up":
        generate()
        run(COMPOSE + ["up", "-d"])
        wait_ready()
        print("Trino ready: http://localhost:8080 (none), https://localhost:8443 (ldap/jwt)")
        print(f"CA certificate: {GEN / 'ca.crt'}")
    elif cmd == "down":
        run(COMPOSE + ["stop"])
    elif cmd == "reset":
        run(COMPOSE + ["down", "--volumes"])
    elif cmd == "jwt":
        print(jwt(argv[2] if len(argv) > 2 else "admin"))
    elif cmd == "sql":
        for row in sql(argv[2]):
            print(row)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
