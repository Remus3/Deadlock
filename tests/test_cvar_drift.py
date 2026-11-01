"""vw_cvar_drift: autoexec convars vs two GameTracking-Deadlock dumps (fixtures, no network)."""
from pathlib import Path

import vw_cvar_drift as D

FIX = Path(__file__).resolve().parent / "fixtures" / "cvar_drift"
OLD = FIX / "6801-old.txt"
NEW = FIX / "6826-new.txt"


def dbs():
    return (D.parse_dump(OLD.read_text(encoding="utf-8")),
            D.parse_dump(NEW.read_text(encoding="utf-8")))


def test_parse_dump_names_and_flags():
    old, new = dbs()
    assert set(old) == {"fps_max", "old_gone_cvar", "cl_interp_ratio", "rate"}
    assert new["noclip_speed"] == {"cheat"}
    assert new["fps_max"] == {"archive", "release"}


def test_removed_renamed_ok_added_absent_cheat():
    old, new = dbs()
    rows = {n: (v, c) for n, v, c in D.drift(
        ["fps_max", "old_gone_cvar", "cl_interp_ratio", "noclip_speed", "nope"], old, new)}
    assert rows["fps_max"] == ("ok", [])
    assert rows["old_gone_cvar"] == ("removed", [])
    assert rows["cl_interp_ratio"] == ("renamed", ["cl_interp_ratio_v2"])
    assert rows["noclip_speed"] == ("added+cheat", [])
    assert rows["nope"] == ("absent", [])


def test_cli_flags_removed_convar(tmp_path, capsys):
    cfg = tmp_path / "autoexec.cfg"
    cfg.write_text("// c\nfps_max 237\nold_gone_cvar 0\necho \"hi\"\n", encoding="ascii")
    assert D.main(["check", "--old", str(OLD), "--new", str(NEW), "--cfg", str(cfg)]) == 1
    out = capsys.readouterr().out
    assert "- old_gone_cvar: removed" in out and "echo" not in out.split("\n", 1)[1]


def test_cli_clean_cfg_exits_zero(tmp_path):
    cfg = tmp_path / "autoexec.cfg"
    cfg.write_text("fps_max 237\nrate 786432\n", encoding="ascii")
    assert D.main(["check", "--old", str(OLD), "--new", str(NEW), "--cfg", str(cfg)]) == 0


def test_newest_two_orders_by_build(tmp_path):
    for n in ("6801-a.txt", "6826-b.txt", "6812-c.txt"):
        (tmp_path / n).write_text("x 1 ()\n", encoding="ascii")
    o, n = D.newest_two(tmp_path)
    assert (o.name, n.name) == ("6812-c.txt", "6826-b.txt")
