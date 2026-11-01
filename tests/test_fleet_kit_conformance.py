"""The vendored kit is byte-identical to its manifest and CLAUDE.md embeds the block."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "ops" / "fleet_kit"
BEGIN, END = "<!-- FLEET-COMMON BEGIN -->\n", "<!-- FLEET-COMMON END -->"


def _man():
    return json.loads((KIT / "MANIFEST.json").read_text(encoding="ascii"))


def test_every_kit_file_matches_the_manifest():
    man = _man()
    bad = [n for n, h in man["files"].items()
           if hashlib.sha256((KIT / n).read_bytes()).hexdigest() != h]
    assert not bad, bad
    assert man["version"] == 27


def test_claude_md_embeds_the_block_byte_exact():
    text = (ROOT / "CLAUDE.md").read_bytes().decode("ascii")
    i, j = text.find(BEGIN), text.find(END)
    assert 0 <= i < j
    block = text[i + len(BEGIN):j].encode("ascii")
    assert hashlib.sha256(block).hexdigest() == _man()["common_block_sha256"]
    lines = text.split("\n")
    assert lines.count(BEGIN.rstrip("\n")) == 1 and lines.count(END) == 1


def test_settings_wire_the_kit_hooks():
    s = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="ascii"))
    cmds = [h["command"] for ev in s["hooks"].values() for g in ev for h in g["hooks"]]
    launcher = 'bash "$CLAUDE_PROJECT_DIR/ops/fleet_kit/fleet_hook.sh" '
    pre = {h["command"]: h for g in s["hooks"]["PreToolUse"] for h in g["hooks"]}
    for cmd in (launcher + "fleet_subagent_first.py", launcher + "fleet_claims.py hook"):
        assert cmd in pre, cmd
        assert pre[cmd]["timeout"] == 15
    assert not any("|| true" in c for c in pre)
    assert 'python "$CLAUDE_PROJECT_DIR/ops/fleet_kit/fleet_claims.py" release-hook' in cmds
    assert "python ops/fleet_kit/fleet_done.py stop-hook" in cmds


def test_done_command_marks_and_prints_the_line():
    t = (ROOT / ".claude" / "commands" / "done.md").read_text(encoding="ascii")
    assert "fleet_done.py mark" in t and "Done ritual complete, safe to clear" in t


def test_git_hooks_call_fleet_identity():
    hooks = ROOT / ".githooks"
    assert "fleet_identity.py\" commit-msg" in (hooks / "commit-msg").read_text(encoding="ascii")
    assert "fleet_identity.py\" pre-push" in (hooks / "pre-push").read_text(encoding="ascii")


def test_handoff_has_one_session_line_last():
    lines = (ROOT / "VW-NEXT-SESSION.txt").read_text(encoding="ascii").splitlines()
    sess = [ln for ln in lines if ln.startswith("SESSION: ")]
    assert len(sess) == 1 and lines[-1] == sess[0] and sess[0][9:].isdigit()
