"""Guest-only commands. External code is never built or loaded on the Mac."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from archive_utils import safe_extract


ROOT = Path("/workspace")
REPORTS = ROOT / "reports"
LOCK = Path("/opt/lab/sources.lock.json")
DISK_BUDGET_KIB = 80 * 1024 * 1024


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(command, name, cwd=ROOT, timeout=7200):
    """Bound command duration and monitor lab disk usage; do not raise budgets."""
    print(f"Starting {name}", flush=True)
    started = time.monotonic()
    checked = 0
    failure = None
    with (REPORTS / f"{name}.log").open("w") as log:
        proc = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        try:
            while proc.poll() is None:
                elapsed = time.monotonic() - started
                if elapsed > timeout:
                    raise RuntimeError(f"{name} reached its time limit")
                if elapsed >= checked:
                    used = int(subprocess.check_output(["du", "-sk", str(ROOT)], text=True).split()[0])
                    if used > DISK_BUDGET_KIB:
                        raise RuntimeError("Lab disk budget exceeded")
                    checked = elapsed + 30
                    print(f"{name}: {int(elapsed)}s; lab disk {used // 1024} MiB", flush=True)
                time.sleep(1)
            if proc.returncode:
                raise RuntimeError(f"{name} exited {proc.returncode}; inspect its report log")
        except BaseException as exc:
            failure = str(exc)
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
            raise
        finally:
            (REPORTS / f"{name}.json").write_text(json.dumps({
                "command":command, "returncode":proc.returncode,
                "elapsed_seconds":round(time.monotonic()-started, 1), "failure":failure,
            }, indent=2) + "\n")


def prepare(lock):
    marker = ROOT / "prepared.json"
    if marker.exists():
        raise RuntimeError("Already prepared. Preserve the existing lock and reports.")
    inputs = Path("/opt/lab/inputs")
    for item in lock["inputs"]:
        path = inputs / item["filename"]
        if (path.is_symlink() or path.stat().st_size != item["size"] or
                digest(path) != item["sha256"]):
            raise RuntimeError(f"Input validation failed: {item['filename']}")
    source = next(i for i in lock["inputs"] if i["kind"] == "dbt-source")
    driver = next(i for i in lock["inputs"] if i["kind"] == "driver")
    safe_extract(inputs / source["filename"], ROOT / "source")
    safe_extract(inputs / driver["filename"], ROOT / "driver")
    run(["python3", "-m", "venv", "/workspace/venv"], "venv", timeout=120)
    wheels = [str(inputs / i["filename"]) for i in lock["inputs"] if i["kind"] == "wheel"]
    run(["/workspace/venv/bin/python", "-m", "pip", "install", "--no-index", "--no-deps", *wheels],
        "python-dependencies", timeout=300)
    source_dir = ROOT / "source" / f"dbt-{lock['dbt_commit']}"
    shutil.copyfile("/opt/lab/Cargo.lock", source_dir / "Cargo.lock")
    run(["cargo", "fetch", "--locked", "--target", "aarch64-unknown-linux-gnu"],
        "cargo-fetch", cwd=source_dir, timeout=1800)
    shutil.copy2(source_dir / "Cargo.lock", REPORTS / "Cargo.lock")
    shutil.copy2("/opt/lab/os-packages.txt", REPORTS / "os-packages.txt")
    shutil.copytree("/opt/lab/projects", ROOT / "projects")
    marker.write_text(json.dumps({"input_lock_sha256":digest(LOCK),
                                 "cargo_lock_sha256":digest(source_dir / "Cargo.lock")}, indent=2)+"\n")
    shutil.copy2(marker, REPORTS / "prepared.json")


def main():
    if Path("/opt/lab/sources.lock.json").is_file() is False or os.getuid() != 10001:
        raise RuntimeError("This command runs only in the reviewed lab image as UID 10001")
    REPORTS.mkdir(exist_ok=True)
    (ROOT / "home").mkdir(exist_ok=True)
    lock = json.loads(LOCK.read_text())
    command = sys.argv[1]
    if command == "prepare":
        prepare(lock)
        return
    prepared = json.loads((ROOT / "prepared.json").read_text())
    if prepared["input_lock_sha256"] != digest(LOCK):
        raise RuntimeError("Source lock changed after preparation")
    source_dir = ROOT / "source" / f"dbt-{lock['dbt_commit']}"
    if digest(source_dir / "Cargo.lock") != prepared["cargo_lock_sha256"]:
        raise RuntimeError("Cargo lock changed after preparation")
    if command == "baseline":
        run(["cargo", "build", "-p", "dbt-sa-cli", "--bin", "dbt", "--frozen", "-j", "1"],
            "baseline-build", cwd=source_dir)
        binary = source_dir / "target/debug/dbt"
        run([str(binary), "--version"], "baseline-version", timeout=60)
        run([str(binary), "--help"], "baseline-help", timeout=60)
        (REPORTS / "baseline-binary.json").write_text(json.dumps({
            "path":str(binary), "sha256":digest(binary), "dbt_commit":lock["dbt_commit"],
            "cargo_lock_sha256":prepared["cargo_lock_sha256"],
        }, indent=2)+"\n")
    elif command == "smoke":
        run(["/workspace/venv/bin/python", "/opt/lab/driver_smoke.py"], "driver-smoke", timeout=600)
    else:
        raise ValueError(f"Unknown lab command: {command}")


if __name__ == "__main__":
    main()
