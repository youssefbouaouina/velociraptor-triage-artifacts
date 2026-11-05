"""Test cases: one harmless fixture per artifact.

Each case plants a marker that is unique to the test, points one artifact
parameter at the fixture, runs the artifact, and asserts the marker is in the
output. The shipped artifact keeps its real default; only the temporary copy
used by the test is edited.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

WINDOWS_PLATFORM = "windows"
LINUX_PLATFORM = "linux"

MARKER = "VELO-TEST-MARKER"


def _write(path: Path, content: str, mode: int | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if mode is not None:
        path.chmod(mode)
    return path


def _registry_key(root, *parts):
    import winreg

    key = winreg.CreateKeyEx(root, "\\".join(parts), 0, winreg.KEY_ALL_ACCESS)
    return key


def _registry_value(path_parts: tuple[str, ...], name: str, value: str) -> None:
    import winreg

    key = _registry_key(winreg.HKEY_CURRENT_USER, *path_parts)
    try:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    finally:
        winreg.CloseKey(key)


def _delete_registry_tree(path_parts: tuple[str, ...]) -> None:
    """Remove HKCU\\<path_parts> recursively with reg.exe.

    winreg.DeleteKey refuses to delete a key that still has subkeys and the
    dance required to empty a tree is error prone; reg.exe does it in one call
    and is present on every supported Windows version.
    """
    key = "HKCU\\" + "\\".join(path_parts)
    subprocess.run(
        ["reg", "delete", key, "/f"],
        capture_output=True,
        text=True,
        check=False,
    )


# Each fixture returns (parameter_value, cleanup_callable).
def fixture_registry_run() -> tuple[str, callable]:
    parts = ("Software", "VeloTriageTest", "Run")
    _registry_value(parts, "VeloTest", f"notepad.exe --marker {MARKER}")
    return (
        r"HKEY_CURRENT_USER\Software\VeloTriageTest\Run\*",
        lambda: _delete_registry_tree(("Software", "VeloTriageTest")),
    )


def fixture_registry_services() -> tuple[str, callable]:
    parts = ("Software", "VeloTriageTest", "Services", "VeloTestSvc")
    _registry_value(
        parts,
        "ImagePath",
        rf"C:\Users\Public\{MARKER}.exe",
    )
    return (
        r"HKEY_CURRENT_USER\Software\VeloTriageTest\Services\*\ImagePath",
        lambda: _delete_registry_tree(("Software", "VeloTriageTest")),
    )


def fixture_tasks() -> tuple[str, callable]:
    directory = Path(tempfile.mkdtemp(prefix="velo-tasks-"))
    content = (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        "<Task>\n"
        "  <Actions>\n"
        "    <Exec>\n"
        "      <Command>powershell.exe</Command>\n"
        "      <Arguments>-EncodedCommand SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoA</Arguments>\n"
        f"      <!-- {MARKER} -->\n"
        "    </Exec>\n"
        "  </Actions>\n"
        "</Task>\n"
    )
    _write(directory / "VeloTest", content)
    return (str(directory / "*"), lambda: _remove_tree(directory))


def fixture_prefetch() -> tuple[str, callable]:
    directory = Path(tempfile.mkdtemp(prefix="velo-prefetch-"))
    _write(directory / "CERTUTIL.EXE-VELOTESTMARKER.pf", "prefetch fixture\n")
    return (str(directory / "*.pf"), lambda: _remove_tree(directory))


def fixture_registry_defender() -> tuple[str, callable]:
    parts = ("Software", "VeloTriageTest", "Defender", "Exclusions", "Paths")
    _registry_value(parts, "VeloTest", rf"C:\Users\Public\{MARKER}")
    return (
        r"HKEY_CURRENT_USER\Software\VeloTriageTest\Defender\Exclusions\Paths\*",
        lambda: _delete_registry_tree(("Software", "VeloTriageTest")),
    )


def fixture_registry_winlogon() -> tuple[str, callable]:
    parts = ("Software", "VeloTriageTest", "Winlogon")
    _registry_value(
        parts,
        "Userinit",
        rf"C:\Windows\system32\userinit.exe, C:\Users\Public\{MARKER}.exe",
    )
    return (
        r"HKEY_CURRENT_USER\Software\VeloTriageTest\Winlogon\*",
        lambda: _delete_registry_tree(("Software", "VeloTriageTest")),
    )


def fixture_history() -> tuple[str, callable]:
    directory = Path(tempfile.mkdtemp(prefix="velo-history-"))
    path = _write(
        directory / "ConsoleHost_history.txt",
        f"Get-ChildItem C:\\\nWrite-Host {MARKER}\n",
    )
    return (str(path), lambda: _remove_tree(directory))


def fixture_cron() -> tuple[str, callable]:
    directory = Path(tempfile.mkdtemp(prefix="velo-cron-"))
    _write(directory / "velotest", f"* * * * * root echo {MARKER}\n")
    return (str(directory / "*"), lambda: _remove_tree(directory))


def fixture_systemd() -> tuple[str, callable]:
    directory = Path(tempfile.mkdtemp(prefix="velo-systemd-"))
    _write(
        directory / "velotest.timer",
        f"[Timer]\n# {MARKER}\nOnCalendar=*-*-* 03:00:00\nUnit=velotest.service\n",
    )
    return (str(directory / "*.timer"), lambda: _remove_tree(directory))


def fixture_ssh_keys() -> tuple[str, callable]:
    directory = Path(tempfile.mkdtemp(prefix="velo-ssh-"))
    _write(
        directory / "authorized_keys",
        f"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeKeyForTestingOnly {MARKER}\n",
    )
    return (str(directory / "authorized_keys"), lambda: _remove_tree(directory))


def fixture_suid() -> tuple[str, callable]:
    directory = Path(tempfile.mkdtemp(prefix="velo-suid-"))
    _write(directory / f"velotest-{MARKER}", "#!/bin/sh\nexit 0\n", mode=0o4755)
    return (str(directory), lambda: _remove_tree(directory))


def fixture_sudoers() -> tuple[str, callable]:
    directory = Path(tempfile.mkdtemp(prefix="velo-sudoers-"))
    _write(directory / "velotest", f"# {MARKER}\n%velotest ALL=(ALL) NOPASSWD: ALL\n")
    return (str(directory / "*"), lambda: _remove_tree(directory))


def _remove_tree(directory: Path) -> None:
    import shutil

    shutil.rmtree(directory, ignore_errors=True)


CASES = [
    {
        "name": "Custom.Windows.Triage.Persistence",
        "platform": WINDOWS_PLATFORM,
        "parameter": "RunKeys",
        "fixture": fixture_registry_run,
    },
    {
        "name": "Custom.Windows.Triage.UserWritableServices",
        "platform": WINDOWS_PLATFORM,
        "parameter": "ServicesRoot",
        "fixture": fixture_registry_services,
    },
    {
        "name": "Custom.Windows.Triage.ScheduledTasksEncoded",
        "platform": WINDOWS_PLATFORM,
        "parameter": "TasksGlobs",
        "fixture": fixture_tasks,
    },
    {
        "name": "Custom.Windows.Triage.PrefetchLOLBins",
        "platform": WINDOWS_PLATFORM,
        "parameter": "PrefetchGlobs",
        "fixture": fixture_prefetch,
        "marker": "VELOTESTMARKER",
    },
    {
        "name": "Custom.Windows.Triage.DefenderExclusions",
        "platform": WINDOWS_PLATFORM,
        "parameter": "ExclusionsKeys",
        "fixture": fixture_registry_defender,
    },
    {
        "name": "Custom.Windows.Triage.LogonScripts",
        "platform": WINDOWS_PLATFORM,
        "parameter": "WinlogonGlobs",
        "fixture": fixture_registry_winlogon,
    },
    {
        "name": "Custom.Windows.Triage.PowerShellHistory",
        "platform": WINDOWS_PLATFORM,
        "parameter": "HistoryGlobs",
        "fixture": fixture_history,
    },
    {
        "name": "Custom.Linux.Triage.CronPersistence",
        "platform": LINUX_PLATFORM,
        "parameter": "CronGlobs",
        "fixture": fixture_cron,
    },
    {
        "name": "Custom.Linux.Triage.SystemdTimers",
        "platform": LINUX_PLATFORM,
        "parameter": "TimerGlobs",
        "fixture": fixture_systemd,
    },
    {
        "name": "Custom.Linux.Triage.SSHAuthorizedKeys",
        "platform": LINUX_PLATFORM,
        "parameter": "KeysGlobs",
        "fixture": fixture_ssh_keys,
    },
    {
        "name": "Custom.Linux.Triage.SuidBinaries",
        "platform": LINUX_PLATFORM,
        "parameter": "Root",
        "fixture": fixture_suid,
    },
    {
        "name": "Custom.Linux.Triage.SudoersChanges",
        "platform": LINUX_PLATFORM,
        "parameter": "SudoersGlobs",
        "fixture": fixture_sudoers,
    },
]


if __name__ == "__main__":
    for case in CASES:
        print(f"{case['platform']:8} {case['name']} -> {case['parameter']}")
    sys.exit(0)
