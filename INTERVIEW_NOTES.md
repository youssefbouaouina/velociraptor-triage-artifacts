# Interview notes — velociraptor-triage-artifacts

## What this project demonstrates

- Writing VQL, not just running someone else's artifacts: `glob` with the registry accessor,
  `read_file`, `execve`, parameter expansion, glob lists passed through `split`.
- Testing a DFIR tool with the real engine. The harness starts the actual 0.77.3 binary, so a
  query that parses but returns nothing fails the build.
- Separating a positive test (marker must appear) from a noise baseline (how many rows on a
  clean host). Both are needed: an artifact that finds everything is as useless as one that
  finds nothing.
- Designing fixtures that are safe on a shared CI runner: `HKCU` instead of `HKLM`, temp
  directories instead of `/etc`, and cleanup in `finally`.

## Questions I expect

**Why not test against a public memory or disk image?**
Those images are large, licensed for specific use, and would make CI slow and fragile. The
question this pack answers is "does the query return the evidence it claims to return", which a
fixture answers exactly. Detection quality on real hosts is listed as a limitation because it is
not measured here.

**Why patch the YAML instead of passing a parameter on the command line?**
Velociraptor's `artifacts collect` accepts `--arg`, but the parameter names and types differ per
artifact and an override can silently be ignored if the name is wrong. Editing the default in a
temporary copy exercises the same code path a user gets after changing the parameter in the GUI,
and the test fails loudly if the parameter is renamed.

**Why does the Persistence artifact emit several JSON arrays?**
It has three sources. Velociraptor writes one array per source back-to-back (`][`), which is not
a single JSON document. The runner uses `JSONDecoder.raw_decode` in a loop rather than
`json.loads`, otherwise multi-source artifacts look like malformed output.

**What was the hardest VQL detail?**
Registry globs need an explicit accessor (`accessor="registry"`), and `{{ .Param }}` mangles the
backslashes in a Windows path. Referencing the parameter directly is the reliable form. A query
that returns zero rows prints nothing at all, not `[]`, so "no output" and "load error" must be
distinguished by the exit code.

**What would you add with more time?**
EVTX-backed artifacts (recently created local admins, 4688 process creation) with a small
licence-clean sample, a server-side hunt notebook, and a precision measurement against a labelled
host snapshot. All three need data this repository cannot ship.

## Honest limitations

- The baseline is a snapshot of one host and two CI runners, not a distribution.
- The `execve`-based SUID scan depends on `bash` and `find` being present.
- The pack is collection-only; it does not score or correlate findings.
