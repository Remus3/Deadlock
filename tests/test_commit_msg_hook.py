""".githooks/commit-msg refuses a subject over 72 characters (after fleet_identity)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "commit-msg"
SH = shutil.which("sh") or shutil.which("bash")


def run_hook(tmp_path, text):
    msg = tmp_path / "MSG"
    msg.write_bytes(text.encode("ascii"))
    return subprocess.run([SH, str(HOOK), str(msg)], cwd=ROOT, capture_output=True,
                          text=True, timeout=60)


@pytest.mark.skipif(SH is None, reason="no POSIX shell")
def test_73_char_subject_refused(tmp_path):
    r = run_hook(tmp_path, "x" * 73 + "\n\nbody\n")
    assert r.returncode == 1
    assert "73 characters" in r.stderr


@pytest.mark.skipif(SH is None, reason="no POSIX shell")
def test_72_char_subject_accepted_and_comments_skipped(tmp_path):
    r = run_hook(tmp_path, "# " + "c" * 90 + "\n\n" + "y" * 72 + "\n\n" + "z" * 120 + "\n")
    assert r.returncode == 0, r.stderr


def test_hook_is_ascii_lf():
    data = HOOK.read_bytes()
    assert b"\r\n" not in data and data.isascii()
