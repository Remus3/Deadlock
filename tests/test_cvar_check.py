"""vw_cvar_check: autoexec cvars vs a cvar flag list (no network, no game files)."""
import json
from pathlib import Path

import vw_cvar_check as C

FIX = Path(__file__).resolve().parent / "fixtures" / "cvars"
ROOT = Path(__file__).resolve().parents[1]
DUMP = """\
cvar list
--------------
fps_max                                  : 400      : , "a", "cl", "release" : Frame rate limiter
r_wireframe_dev                          : 0        : , "cl", "dev"          : dev only
noclip_speed                             : 5        : cheat, sv               : cheat cvar
--------------
  3 convars/concommands
"""


def api_db():
    return C.load_api_list(json.loads((FIX / "convars_subset.json").read_text(encoding="utf-8")))


def test_parse_cfg_comments_quotes_and_semicolons():
    text = '// c\nfps_max 237 // trailing\necho "a;b // not a comment"; rate 1\n\n'
    assert C.parse_cfg(text) == [
        (2, "fps_max", "237"), (3, "echo", '"a;b // not a comment"'), (3, "rate", "1")]


def test_api_flags_map_to_verdicts():
    db = api_db()
    assert C.classify("sensitivity", db) == "ok"
    assert C.classify("ai_debug_enemy_position", db) == "cheat"
    assert C.classify("ag2_preserve_params_on_reload", db) == "devonly"
    assert C.classify("fps_max", db) == "unknown"
    assert C.classify("echo", db) == "command"


def test_dump_format_and_merge():
    dump = C.load_dump(DUMP)
    assert set(dump) == {"fps_max", "r_wireframe_dev", "noclip_speed"}
    db = C.merge(api_db(), dump)
    assert C.classify("fps_max", db) == "ok"
    assert C.classify("r_wireframe_dev", db) == "devonly"
    assert C.classify("noclip_speed", db) == "cheat"
    assert C.classify("sensitivity", db) == "ok"


def test_cli_exit_codes(tmp_path, capsys):
    lst = str(FIX / "convars_subset.json")
    good = tmp_path / "good.cfg"
    good.write_text("sensitivity 1.6\nfps_max 237\necho hi\n", encoding="ascii")
    bad = tmp_path / "bad.cfg"
    bad.write_text("sensitivity 1.6\nai_debug_enemy_position 1\n", encoding="ascii")
    assert C.main(["check", "--list", lst, "--cfg", str(good)]) == 0
    assert C.main(["check", "--list", lst, "--cfg", str(bad)]) == 1
    out = capsys.readouterr().out
    assert "ai_debug_enemy_position: cheat" in out and "fps_max: unknown" in out
    assert C.main(["check", "--list", str(tmp_path / "none.json"), "--cfg", str(good)]) == 2


def test_repo_autoexec_has_no_flagged_cvar():
    rows = C.check_text((ROOT / "config" / "autoexec.cfg").read_text(encoding="ascii"),
                        api_db())
    assert rows and not [r for r in rows if r["verdict"] in C.FAIL]
