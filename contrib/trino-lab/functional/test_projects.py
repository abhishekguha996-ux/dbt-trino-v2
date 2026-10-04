"""End-to-end projects checked against independently computed results.

- retail: synthetic shop with joins, aggregates, refunds and edge values; data tests compare
  every mart with fixtures generated separately in Python (scripts/generate_retail.py).
- tpch: TPC-H tiny joins materialized into each lakehouse catalog and compared with a
  Python/Decimal oracle (scripts/tpch_oracle.py).
"""

import json
import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from harness import TrinoTestCase

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB / "scripts"))
import tpch_oracle  # noqa: E402


def project_files(name: str) -> tuple[dict[str, str], str]:
    root = LAB / "projects" / name
    files = {
        str(path.relative_to(root)): path.read_text()
        for path in root.rglob("*")
        if path.is_file() and path.name not in ("dbt_project.yml", "profiles.yml", "expected.json")
    }
    config = (root / "dbt_project.yml").read_text()
    config = "\n".join(
        line for line in config.splitlines()
        if not line.startswith(("name:", "version:", "config-version:", "profile:"))
    ).replace("trino_retail:", "functional:").replace("trino_tpch:", "functional:")
    return files, config + "\n"


def typed(value):
    """Normalize Trino REST JSON values for comparison with the Python oracle."""
    if isinstance(value, str) and len(value) == 10 and value[4] == "-":
        return date.fromisoformat(value)
    return value


class TestProjects(TrinoTestCase):
    def test_retail(self):
        expected = json.loads((LAB / "projects" / "retail" / "expected.json").read_text())
        for catalog in self.catalogs():
            with self.subTest(catalog=catalog):
                files, config = project_files("retail")
                p = self.project(catalog, files, config)
                result = p.dbt("build")
                failed = [r["unique_id"] for r in result.results if r["status"] not in ("success", "pass", "no-op")
                  and not (r["status"] == "skipped" and ".int_" in r["unique_id"])]  # ephemeral
                self.assertEqual(failed, [])
                for seed, count in expected["rows"].items():
                    self.assertEqual(p.query(f"select count(*) from {p.relation(seed)}"), [[count]], seed)
                net = p.query(f"select sum(net_cents) from {p.relation('fct_orders')}")[0][0]
                self.assertEqual(net, expected["totals"]["net_cents"])
                if catalog != "delta":
                    p.dbt("build")  # idempotent rebuild

    def test_tpch_against_python_oracle(self):
        for catalog in self.catalogs():
            with self.subTest(catalog=catalog):
                files, config = project_files("tpch")
                p = self.project(catalog, files, config)
                p.dbt("build")

                def rows(sql):
                    out = []
                    for row in p.query(sql):
                        out.append(tuple(
                            Decimal(v) if isinstance(v, str) and v.replace(".", "", 1).isdigit() and "." in v
                            else typed(v) for v in row))
                    return out

                report = tpch_oracle.verify(rows, f'{catalog}."{p.schema}"')
                self.assertEqual(report["status"], "pass")


if __name__ == "__main__":
    unittest.main()
