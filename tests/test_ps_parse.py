"""FLEET-COMMON 8: every tracked PowerShell file parses under Windows PowerShell 5.1."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PS1 = sorted((ROOT / "tools").glob("*.ps1"))


@pytest.mark.skipif(sys.platform != "win32" or not shutil.which("powershell.exe"),
                    reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize("path", PS1, ids=lambda p: p.name)
def test_parses_under_51(path):
    cmd = ("$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile("
           "'%s', [ref]$null, [ref]$e); if ($e.Count) { $e | ForEach-Object { $_.Message }; exit 1 }; "
           "if ($PSVersionTable.PSVersion.Major -ne 5) { exit 2 }" % str(path).replace("'", "''"))
    r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr


def test_ps_files_are_ascii_lf():
    assert PS1
    for p in PS1:
        data = p.read_bytes()
        assert b"\r" not in data and all(b < 128 for b in data), p.name
