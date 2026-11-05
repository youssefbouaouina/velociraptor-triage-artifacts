#!/usr/bin/env python3
"""Download the pinned Velociraptor release for the current platform."""

from __future__ import annotations

import argparse
import gzip
import platform
import stat
import sys
import urllib.request
from pathlib import Path

VERSION = "0.77.3"
BASE = f"https://github.com/Velocidex/velociraptor/releases/download/v{VERSION}"


def asset_name(plat: str) -> str:
    if plat == "windows":
        return f"velociraptor-v{VERSION}-windows-amd64.exe.gz"
    return f"velociraptor-v{VERSION}-linux-amd64.gz"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", default="bin", help="directory for the binary")
    parser.add_argument("--platform", choices=["windows", "linux"], default=None)
    args = parser.parse_args()

    plat = args.platform or ("windows" if platform.system() == "Windows" else "linux")
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / ("velociraptor.exe" if plat == "windows" else "velociraptor")
    url = f"{BASE}/{asset_name(plat)}"

    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    raw = gzip.decompress(data)
    out.write_bytes(raw)
    if plat != "windows":
        out.chmod(out.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"wrote {out} ({len(raw)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
