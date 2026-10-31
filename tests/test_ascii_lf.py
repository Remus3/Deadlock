"""FLEET-COMMON 8: every authored tracked file is ASCII + LF."""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEXT = {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".ps1", ".cfg", ".vcfg", ".ini", "",
        ".js", ".cjs", ".mjs", ".html", ".css"}


def _tracked():
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True,
                             check=True).stdout.decode("utf-8")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("no git repository: trackedness unknowable")
    return [p for p in out.split("\0") if p and not p.startswith("ops/fleet_kit/")]


def test_ascii_and_lf():
    bad = []
    for p in _tracked():
        f = ROOT / p
        if f.suffix.lower() not in TEXT or not f.is_file():
            continue
        data = f.read_bytes()
        if b"\r" in data or any(b > 127 for b in data):
            bad.append(p)
    assert not bad, bad
