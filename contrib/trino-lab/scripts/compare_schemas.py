#!/usr/bin/env python3
"""Compare two Trino schemas built by dbt v1 and dbt v2 (read-only).

For every relation present in either schema, report missing relations, relation type and
column type differences, row counts, and an order-independent checksum of the columns both
sides share (Trino's `checksum()` over each row serialized as JSON).

    python3 compare_schemas.py --host trino.example.com --user me --password-env TRINO_PASSWORD \
        --catalog hive --left analytics --right analytics_v2_check [--cert ca.pem] [--port 443]

Uses only the Python standard library and Trino's REST protocol. Exit code 1 if anything differs.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
import urllib.request


class Trino:
    def __init__(self, args: argparse.Namespace):
        scheme = "http" if args.http else "https"
        self.url = f"{scheme}://{args.host}:{args.port}/v1/statement"
        self.headers = {"X-Trino-User": args.user, "X-Trino-Source": "dbt-trino-compare"}
        password = os.environ.get(args.password_env) if args.password_env else None
        if password:
            token = base64.b64encode(f"{args.user}:{password}".encode()).decode()
            self.headers["Authorization"] = f"Basic {token}"
        self.context = None
        if not args.http:
            self.context = ssl.create_default_context(cafile=args.cert) if args.cert else ssl.create_default_context()

    def rows(self, sql: str) -> list[list]:
        req = urllib.request.Request(self.url, data=sql.encode(), headers=self.headers)
        out: list = []
        with urllib.request.urlopen(req, context=self.context) as resp:
            body = json.load(resp)
        while True:
            if "error" in body:
                raise RuntimeError(f"{body['error'].get('message')}\n{sql}")
            out.extend(body.get("data", []))
            if not body.get("nextUri"):
                return out
            req = urllib.request.Request(body["nextUri"], headers=self.headers)
            with urllib.request.urlopen(req, context=self.context) as resp:
                body = json.load(resp)


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def describe(trino: Trino, catalog: str, schema: str) -> dict[str, dict]:
    relations = {
        name: {"type": kind, "columns": {}}
        for name, kind in trino.rows(
            f"select table_name, table_type from {ident(catalog)}.information_schema.tables "
            f"where table_schema = {literal(schema)}")
    }
    for name, column, data_type in trino.rows(
            f"select table_name, column_name, data_type from {ident(catalog)}.information_schema.columns "
            f"where table_schema = {literal(schema)}"):
        if name in relations:
            relations[name]["columns"][column] = data_type
    return relations


def fingerprint(trino: Trino, relation: str, columns: list[str]) -> tuple[int, str]:
    row = ", ".join(ident(c) for c in columns)
    count, digest = trino.rows(
        f"select count(*), to_hex(checksum(json_format(cast(row({row}) as json)))) from {relation}")[0]
    return count, digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password-env", help="environment variable holding the password (Basic auth)")
    parser.add_argument("--cert", help="CA bundle for TLS verification")
    parser.add_argument("--http", action="store_true", help="plain HTTP (local testing only)")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--left", required=True, help="schema built by dbt v1")
    parser.add_argument("--right", required=True, help="schema built by dbt v2")
    parser.add_argument("--right-catalog", help="catalog of the right schema if different")
    parser.add_argument("--skip-data", action="store_true", help="compare metadata only")
    args = parser.parse_args()

    trino = Trino(args)
    right_catalog = args.right_catalog or args.catalog
    left = describe(trino, args.catalog, args.left)
    right = describe(trino, right_catalog, args.right)
    problems = 0
    for name in sorted(set(left) | set(right)):
        if name not in right or name not in left:
            print(f"MISSING  {name}: only in {'left' if name in left else 'right'}")
            problems += 1
            continue
        l, r = left[name], right[name]
        if l["type"] != r["type"]:
            print(f"TYPE     {name}: {l['type']} vs {r['type']}")
            problems += 1
        for column in sorted(set(l["columns"]) | set(r["columns"])):
            lt, rt = l["columns"].get(column), r["columns"].get(column)
            if lt != rt:
                print(f"COLUMN   {name}.{column}: {lt} vs {rt}")
                problems += 1
        if args.skip_data:
            continue
        shared = sorted(set(l["columns"]) & set(r["columns"]))
        if not shared:
            continue
        lf = fingerprint(trino, f"{ident(args.catalog)}.{ident(args.left)}.{ident(name)}", shared)
        rf = fingerprint(trino, f"{ident(right_catalog)}.{ident(args.right)}.{ident(name)}", shared)
        if lf != rf:
            print(f"DATA     {name}: rows {lf[0]} vs {rf[0]}, checksum {lf[1]} vs {rf[1]}")
            problems += 1
        else:
            print(f"OK       {name}: {lf[0]} rows")
    print(f"\n{problems} difference(s) across {len(set(left) | set(right))} relation(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError) as exc:  # URLError and ssl errors are OSErrors
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
