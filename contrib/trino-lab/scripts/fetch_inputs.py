#!/usr/bin/env python3
"""Download the locked inputs as data. Never import or execute them on the Mac."""

import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith("https://"):
            raise ValueError("Refusing a redirect away from HTTPS")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def verify(path, item):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Not a regular input file: {path.name}")
    if path.stat().st_size != item["size"]:
        raise ValueError(f"Unexpected size: {path.name}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != item["sha256"]:
        raise ValueError(f"Checksum mismatch: {path.name}")


def main():
    destination = ROOT / ".inputs"
    if destination.is_symlink():
        raise SystemExit("Input directory must not be a symlink")
    destination.mkdir(exist_ok=True)
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    opener = urllib.request.build_opener(HTTPSRedirect())
    for item in lock["inputs"]:
        name = item["filename"]
        if Path(name).name != name or name in (".", ".."):
            raise ValueError("Invalid input filename")
        target = destination / name
        if target.exists() or target.is_symlink():
            verify(target, item)
            print(f"Verified: {name}", flush=True)
            continue
        if not item["url"].startswith("https://"):
            raise ValueError("Input URL must use HTTPS")
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination, prefix="download-", delete=False) as output:
                temp = Path(output.name)
                with opener.open(item["url"], timeout=60) as response:
                    total = 0
                    while chunk := response.read(1024 * 1024):
                        total += len(chunk)
                        if total > item["size"]:
                            raise ValueError(f"Download exceeds locked size: {name}")
                        output.write(chunk)
            verify(temp, item)
            temp.rename(target)
            print(f"Downloaded and verified: {name}", flush=True)
        finally:
            if temp is not None and temp.exists():
                temp.unlink()


if __name__ == "__main__":
    main()
