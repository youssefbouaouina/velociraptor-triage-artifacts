#!/usr/bin/env python3
"""Run the positive test and the clean-host baseline for every artifact.

The positive test plants a harmless fixture (a registry value, a cron file, a
SUID binary, ...), copies the artifact to a temporary directory, points one
parameter default at the fixture, runs Velociraptor and asserts that the marker
string appears in the JSON output. The shipped artifact is never modified.

The baseline run uses the unmodified artifact on the clean host and records how
many rows it returns. That number is the noise floor: a triage artifact that
returns hundreds of rows on a fresh runner is not useful in an incident.

Usage:
    python tests/run_tests.py --binary bin/velociraptor --platform linux
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cases  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def point_parameter_at(artifact_text: str, parameter: str, value: str) -> str:
    """Replace the default of one parameter in the YAML text."""
    lines = artifact_text.splitlines(keepends=True)
    out: list[str] = []
    in_parameter = False
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- name:"):
            in_parameter = stripped.split(":", 1)[1].strip() == parameter
        elif in_parameter and stripped.startswith("default:"):
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}default: {_yaml_quote(value)}\n")
            in_parameter = False
            replaced = True
            continue
        out.append(line)
    if not replaced:
        raise SystemExit(f"parameter {parameter!r} not found in artifact")
    return "".join(out)


def run_artifact(binary: Path, definitions: Path, name: str, timeout: int = 180):
    command = [
        str(binary),
        "--nobanner",
        "artifacts",
        "collect",
        name,
        "--definitions",
        str(definitions),
        "--format",
        "json",
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, timeout=timeout
    )
    rows = None
    parse_error = None
    # Velociraptor occasionally prints a log line to stdout before the JSON
    # document, and a UTF-8 BOM can survive .strip(). Find the first JSON
    # opener instead of assuming the output starts with one.
    text = completed.stdout.lstrip("\ufeff \t\r\n")
    if text:
        starts = [index for index in (text.find("["), text.find("{")) if index >= 0]
        if not starts:
            parse_error = "no JSON document in stdout"
        else:
            decoder = json.JSONDecoder()
            rows = []
            index = min(starts)
            try:
                while index < len(text):
                    while index < len(text) and text[index].isspace():
                        index += 1
                    if index >= len(text):
                        break
                    value, index = decoder.raw_decode(text, index)
                    rows.extend(value if isinstance(value, list) else [value])
            except json.JSONDecodeError as exc:
                parse_error = str(exc)
    else:
        rows = []
    return completed, rows, parse_error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, help="path to the velociraptor binary")
    parser.add_argument(
        "--definitions", default=None, help="directory with the .yaml artifacts"
    )
    parser.add_argument(
        "--platform", choices=["windows", "linux"], default=None, help="test platform"
    )
    parser.add_argument("--report", default=None, help="write a JSON report here")
    parser.add_argument(
        "--keep-fixtures", action="store_true", help="do not remove planted fixtures"
    )
    args = parser.parse_args()

    plat = args.platform or ("windows" if platform.system() == "Windows" else "linux")
    definitions = Path(args.definitions) if args.definitions else ROOT / "artifacts" / plat
    binary = Path(args.binary).resolve()
    if not binary.exists():
        raise SystemExit(f"binary not found: {binary}")

    selected = [case for case in cases.CASES if case["platform"] == plat]
    print(f"platform={plat} artifacts={len(selected)} binary={binary}")

    report = {"platform": plat, "velociraptor": str(binary), "results": []}
    failures = 0

    for case in selected:
        name = case["name"]
        print(f"\n== {name} ==")
        record = {"name": name, "parameter": case["parameter"]}

        # 1. Clean-host baseline, before anything is planted.
        completed, rows, parse_error = run_artifact(binary, definitions, name)
        if completed.returncode != 0 or parse_error:
            failures += 1
            record.update(
                status="baseline-error",
                returncode=completed.returncode,
                stderr=completed.stderr[-2000:],
                parse_error=parse_error,
            )
            print(f"  baseline FAILED rc={completed.returncode} {parse_error or ''}")
            report["results"].append(record)
            continue
        record["baseline_rows"] = len(rows)
        print(f"  baseline rows={len(rows)}")

        # 2. Plant the fixture and run a copy of the artifact against it.
        parameter_value, cleanup = case["fixture"]()
        record["parameter_value"] = parameter_value
        try:
            source = definitions / f"{name}.yaml"
            text = source.read_text(encoding="utf-8")
            patched = point_parameter_at(text, case["parameter"], parameter_value)
            temp_dir = Path(tempfile.mkdtemp(prefix="velo-artifact-"))
            try:
                (temp_dir / source.name).write_text(patched, encoding="utf-8")
                completed, rows, parse_error = run_artifact(
                    binary, temp_dir, name
                )
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

            marker = case.get("marker", cases.MARKER)
            output = json.dumps(rows) if rows is not None else ""
            if completed.returncode != 0 or parse_error:
                failures += 1
                record.update(
                    status="run-error",
                    returncode=completed.returncode,
                    stderr=completed.stderr[-2000:],
                    parse_error=parse_error,
                )
                print(f"  positive FAILED rc={completed.returncode} {parse_error or ''}")
            elif marker not in output:
                failures += 1
                record.update(status="marker-missing", rows=len(rows), output=output[-2000:])
                print(f"  positive FAILED marker missing (rows={len(rows)})")
            else:
                record.update(status="pass", positive_rows=len(rows))
                print(f"  positive PASS rows={len(rows)}")
        finally:
            if not args.keep_fixtures:
                try:
                    cleanup()
                except Exception as exc:  # cleanup must never mask a test result
                    print(f"  cleanup warning: {exc}")
        report["results"].append(record)

    report["passed"] = sum(1 for row in report["results"] if row["status"] == "pass")
    report["total"] = len(report["results"])
    report["failed"] = failures

    print(f"\n{report['passed']}/{report['total']} passed on {plat}")
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"report: {path}")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
