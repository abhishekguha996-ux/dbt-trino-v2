"""Minimal functional-test harness for the dbt v2 Trino adapter.

Mirrors the shape of dbt's pytest fixtures (`project.run_dbt`, `run_sql`) with the
standard library only. Each test gets a throwaway project directory and a unique schema,
runs the source-built `dbt` binary, and inspects results directly through Trino's REST API.

Environment:
  DBT_BIN          path to the dbt binary (default: <repo>/target/debug/dbt)
  TRINO_HTTP       http://127.0.0.1:8080 by default (scripts/stack.py)
  TRINO_CATALOGS   comma-separated catalogs to exercise (default: memory,hive,iceberg,delta)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import time
import unittest
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DBT_BIN = Path(os.environ.get("DBT_BIN", REPO / "target" / "debug" / "dbt"))
TRINO_HTTP = os.environ.get("TRINO_HTTP", "http://127.0.0.1:8080")
CATALOGS = [c for c in os.environ.get("TRINO_CATALOGS", "memory,hive,iceberg,delta").split(",") if c]
KEEP = os.environ.get("KEEP_SCHEMAS") == "1"
S3_BUCKET = "s3://datalake"


class TrinoError(RuntimeError):
    pass


def run_sql(statement: str, user: str = "admin", catalog: str | None = None) -> list[list]:
    """Run one statement through the Trino REST protocol and return all rows."""
    headers = {"X-Trino-User": user, "X-Trino-Role": "hive=ROLE{admin}"}
    if catalog:
        headers["X-Trino-Catalog"] = catalog
    req = urllib.request.Request(f"{TRINO_HTTP}/v1/statement", data=statement.encode(), headers=headers)
    rows: list = []
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    while True:
        if "error" in body:
            raise TrinoError(body["error"].get("message"))
        rows.extend(body.get("data", []))
        next_uri = body.get("nextUri")
        if not next_uri:
            return rows
        with urllib.request.urlopen(urllib.request.Request(next_uri, headers=headers)) as resp:
            body = json.load(resp)


def relation_type(catalog: str, schema: str, name: str) -> str | None:
    rows = run_sql(
        f"select table_type from {catalog}.information_schema.tables "
        f"where table_schema = '{schema}' and table_name = '{name}'"
    )
    if not rows:
        return None
    mv = run_sql(
        "select count(*) from system.metadata.materialized_views "
        f"where catalog_name = '{catalog}' and schema_name = '{schema}' and name = '{name}'"
    )
    return "materialized_view" if mv[0][0] else {"BASE TABLE": "table", "VIEW": "view"}[rows[0][0]]


def drop_schema(catalog: str, schema: str) -> None:
    try:
        tables = run_sql(
            f"select table_name, table_type from {catalog}.information_schema.tables "
            f"where table_schema = '{schema}'"
        )
    except TrinoError:
        return
    mvs = {
        r[0]
        for r in run_sql(
            "select name from system.metadata.materialized_views "
            f"where catalog_name = '{catalog}' and schema_name = '{schema}'"
        )
    }
    for name, kind in tables:
        noun = "materialized view" if name in mvs else ("view" if kind == "VIEW" else "table")
        try:
            run_sql(f'drop {noun} if exists {catalog}."{schema}"."{name}"')
        except TrinoError:
            pass
    try:
        run_sql(f'drop schema if exists {catalog}."{schema}"')
    except TrinoError:
        pass


class DbtResult:
    def __init__(self, proc: subprocess.CompletedProcess, project_dir: Path):
        self.returncode = proc.returncode
        self.output = proc.stdout + proc.stderr
        results = project_dir / "target" / "run_results.json"
        self.results = json.loads(results.read_text())["results"] if results.exists() else []

    def status(self, name: str) -> str | None:
        for result in self.results:
            parts = result["unique_id"].split(".")
            # test unique ids end with a hash: test.<package>.<name>.<hash>
            if name in (parts[-1], parts[2] if len(parts) > 2 else None):
                return result["status"]
        return None

    def __repr__(self) -> str:
        return f"<DbtResult rc={self.returncode}>\n{self.output[-6000:]}"


class Project:
    """A temporary dbt project bound to one Trino catalog and a unique schema."""

    def __init__(self, name: str, catalog: str, files: dict[str, str], project_config: str = "",
                 profile_overrides: dict | None = None):
        self.catalog = catalog
        self.schema = f"ft_{re.sub(r'[^a-z0-9_]', '_', name.lower())}_{uuid.uuid4().hex[:6]}"
        self.dir = Path(tempfile.mkdtemp(prefix=f"dbt_trino_{name}_"))
        self.profile_overrides = profile_overrides or {}
        for path, content in files.items():
            target = self.dir / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(textwrap.dedent(content).lstrip("\n"))
        (self.dir / "dbt_project.yml").write_text(
            "name: functional\nversion: '1.0'\nconfig-version: 2\nprofile: trino_ft\n"
            + textwrap.dedent(project_config)
        )
        self.write_profile()
        if catalog in ("hive", "iceberg", "delta"):
            run_sql(
                f"create schema if not exists {catalog}.{self.schema} "
                f"with (location = '{S3_BUCKET}/{catalog}/{self.schema}')"
            )

    def write_profile(self, **overrides) -> None:
        output = {
            "type": "trino",
            "method": "none",
            "host": "localhost",
            "port": 8080,
            "user": "admin",
            "database": self.catalog,
            "schema": self.schema,
            "threads": 4,
            "roles": {"hive": "admin"},
            "timezone": "UTC",
        }
        output.update(self.profile_overrides)
        output.update(overrides)
        profile = {"trino_ft": {"target": "ft", "outputs": {"ft": output}}}
        (self.dir / "profiles.yml").write_text(json.dumps(profile, indent=2))

    def write(self, path: str, content: str) -> None:
        target = self.dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(content).lstrip("\n"))

    def remove(self, path: str) -> None:
        (self.dir / path).unlink()

    def dbt(self, *args: str, expect: bool | None = True, env: dict | None = None) -> DbtResult:
        cmd = [str(DBT_BIN), *args, "--project-dir", str(self.dir), "--profiles-dir", str(self.dir)]
        full_env = {**os.environ, "DBT_ALLOW_EXPERIMENTAL_ADAPTERS": "yes",
                    "DBT_SEND_ANONYMOUS_USAGE_STATS": "false", **(env or {})}
        proc = subprocess.run(cmd, capture_output=True, text=True, env=full_env, cwd=self.dir,
                              timeout=900)
        result = DbtResult(proc, self.dir)
        if expect is True and result.returncode != 0:
            raise AssertionError(f"dbt {' '.join(args)} failed:\n{result.output[-8000:]}")
        if expect is False and result.returncode == 0:
            raise AssertionError(f"dbt {' '.join(args)} unexpectedly succeeded:\n{result.output[-4000:]}")
        return result

    def relation(self, name: str) -> str:
        return f'{self.catalog}."{self.schema}"."{name}"'

    def query(self, sql: str) -> list[list]:
        return run_sql(sql.replace("{schema}", f'{self.catalog}."{self.schema}"'))

    def rows(self, name: str, order_by: str = "1") -> list[list]:
        return self.query(f"select * from {self.relation(name)} order by {order_by}")

    def type_of(self, name: str) -> str | None:
        return relation_type(self.catalog, self.schema, name)

    def cleanup(self) -> None:
        if KEEP:
            print(f"kept {self.catalog}.{self.schema} and {self.dir}")
            return
        for suffix in ("", "_snapshots", "_custom"):
            drop_schema(self.catalog, self.schema + suffix)
        shutil.rmtree(self.dir, ignore_errors=True)


class TrinoTestCase(unittest.TestCase):
    """Base class: `self.project(...)` creates a project that is cleaned up after the test."""

    maxDiff = None

    def project(self, catalog: str, files: dict[str, str], project_config: str = "", **kwargs) -> Project:
        project = Project(self.id().split(".")[-1], catalog, files, project_config, **kwargs)
        self.addCleanup(project.cleanup)
        return project

    def catalogs(self, *allowed: str) -> list[str]:
        return [c for c in CATALOGS if not allowed or c in allowed]


def wait_for_trino(timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            run_sql("select 1")
            return
        except Exception:  # noqa: BLE001
            time.sleep(2)
    raise SystemExit("Trino is not reachable; run scripts/stack.py up")
