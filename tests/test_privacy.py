"""The leak gate: shapes are caught, placeholders pass, the tracked tree is clean."""
import subprocess

import pytest

import vw_privacy as P

AT = "@"
BS = chr(92)


def test_shapes_are_caught():
    assert P.line_hits("mail me: someone" + AT + "mailhost.net") == ["email"]
    assert P.line_hits("id 7656119" + "8000000001") == ["steam64"]
    assert P.line_hits("C:" + BS + "Users" + BS + "bob" + BS + "x") == ["user-path"]
    assert P.line_hits("/c/" + "Users/bob/x") == ["posix-user-path"]
    assert P.line_hits("gh" + "p_" + "a" * 30) == ["github-token"]
    assert P.line_hits("userdata" + "/123456/cfg") == ["userdata-id"]
    assert P.line_hits("hello mybox", ["mybox"]) == ["needle"]


def test_short_needles_are_dropped(tmp_path):
    f = tmp_path / "n.json"
    f.write_text('{"needles": ["box", "mybox", " "]}', encoding="ascii")
    assert P.load_needles(f) == ["mybox"]
    assert P.load_needles(tmp_path / "missing.json") == []


def test_placeholders_pass():
    assert P.line_hits("x" + AT + "example.com") == []
    assert P.line_hits("1+x" + AT + "users.noreply.github.com") == []
    assert P.line_hits("<Steam>/userdata/<account>/1422450") == []
    assert P.line_hits(r"C:\Program Files (x86)\Steam") == []


def test_lockfile_deprecated_notice_email_is_waived_only_there():
    line = '      "deprecated": "Old glob. Support: contact x' + AT + 'mailhost.net",'
    assert P.line_hits(line, (), "app/package-lock.json") == []
    assert P.line_hits(line, (), "app/other.json") == ["email"]
    assert P.line_hits('  "author": "x' + AT + 'mailhost.net",', (), "app/package-lock.json") == ["email"]
    assert P.line_hits(line + " mybox", ["mybox"], "app/package-lock.json") == ["needle"]


def test_scrub_removes_ids_names_and_paths():
    raw = ('"name"\t\t"Some Player"\n'
           '"x" "7656119' + '8000000001"\n'
           'C:' + BS + 'Program Files (x86)' + BS + 'Steam' + BS + 'userdata' + BS + '41000000'
           + BS + '1422450\n')
    out = P.scrub_text(raw, ["Some Player"])
    assert "Some Player" not in out and "76561198" not in out and "41000000" not in out
    assert P.scan_text("x", out) == []


def test_diff_scan_reads_added_lines_only():
    diff = ("+++ b/a.txt\n@@ -0,0 +1,2 @@\n+fine\n+bad " + "u" + AT + "mailhost.net\n"
            "-removed " + "v" + AT + "mailhost.net\n")
    assert P.scan_diff(diff) == ["a.txt:2 email"]


def test_tracked_tree_is_clean():
    try:
        subprocess.run(["git", "rev-parse"], cwd=P.ROOT, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("no git repository")
    assert P.scan_tracked() == []
