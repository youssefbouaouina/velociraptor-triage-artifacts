# Sources and licences

| Component | Version | Licence | Use |
|---|---|---|---|
| [Velociraptor](https://github.com/Velocidex/velociraptor) | 0.77.3 (pinned in `tests/fetch_velociraptor.py`) | AGPL-3.0 | VQL engine, `artifacts collect` |
| [Velociraptor documentation](https://docs.velociraptor.app/) | current | AGPL-3.0 | Artifact schema and plugin semantics |
| [MITRE ATT&CK](https://attack.mitre.org/) | technique IDs only | CC BY 4.0 | Mapping in the README table |
| GitHub Actions `windows-latest` / `ubuntu-latest` | runner images | GitHub terms | Positive tests and baselines |

Artifact YAML and VQL in this repository were written for this project; no upstream artifact
file is redistributed. Only built-in plugins are used.

The fixtures contain a marker string (`VELO-TEST-MARKER`), a fake SSH public key and a fake
`sudoers` line. They are not usable credentials and are removed after each test.

Source code and artifact YAML: MIT (see `LICENSE`).
