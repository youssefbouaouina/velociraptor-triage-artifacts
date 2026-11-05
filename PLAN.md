# Plan — velociraptor-triage-artifacts

## Goal

Ship 8–12 read-only Velociraptor artifacts for Windows and Linux triage, each with a harmless
positive test and a clean-host baseline, proven by GitHub Actions on both operating systems.

## Non-negotiables

- Every number in the README comes from a run whose report is committed under `results/`.
- The shipped artifact is never modified by a test; only a temporary copy is parameterised.
- Fixtures are harmless (a marker string, a file in a temp directory, an `HKCU` value).
- No malware, no real credentials, no personal data.
- Pin the Velociraptor release (0.77.3) so the VQL behaviour does not drift under the tests.

## Steps

1. **Artifacts (12).** Seven Windows, five Linux; one query per triage question; every query
   read-only and parameterised with comma-separated globs.
2. **Test harness.** `tests/cases.py` holds one fixture per artifact. `tests/run_tests.py`
   plants the fixture, patches one parameter default in a temp copy, runs the real binary and
   asserts the marker. It also records the clean-host row count first.
3. **Local run.** Windows 11 host, 7/7 positive tests; report committed.
4. **CI.** Matrix `windows-latest` + `ubuntu-latest`, pinned Python and Velociraptor; upload the
   JSON report; fail on any missing marker or load error.
5. **Docs.** README table, import instructions, limitations, sources; `INTERVIEW_NOTES.md`.

## Done criteria

- 12 artifacts load and return JSON.
- 7/7 Windows and 5/5 Linux positive tests pass in CI.
- CI is green and the reports are downloadable.
- README quotes only measured values.

## Time box

Two sittings: artifact writing and local harness first, CI and documentation second. Anything
that needs a Windows event log sample or a Velociraptor server is explicitly out of scope rather
than half-finished.
