"""Compare the player's Deadlock controls with config/controls.recommended.json.

    python tools/vw_controls.py check     read only: binds and convars vs recommended

Read only, always. Deadlock keeps its action keybinds in the Steam cloud file
<Steam>/userdata/<id>/1422450/remote/cfg/citadelkeys_personal.lst, which the
game safety floor forbids editing, so binds are changed in the in-game menu
(Settings > Keybinds) and this tool reads them back. Sensitivity and reticle
convars are set by config/autoexec.cfg; this tool reads back what the game
saved in local/cfg/*convars*.vcfg after a launch. docs/controls.md.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import vw_paths  # noqa: E402

RECOMMENDED = ROOT / "config" / "controls.recommended.json"
AUTOEXEC = ROOT / "config" / "autoexec.cfg"
KEYS_FILE = ("remote", "cfg", "citadelkeys_personal.lst")
CONVAR_FILES = (("local", "cfg", "user_convars_0_slot0.vcfg"),
                ("local", "cfg", "machine_convars.vcfg"))
_TOKEN = re.compile(r'"([^"]*)"|([{}])')
M_YAW = 0.022  # Source default, as saved by the game (user_convars m_yaw 0.022)


def recommended(path=RECOMMENDED):
    return json.loads(Path(path).read_text(encoding="ascii"))


def parse_kv(text):
    """Valve KeyValues text -> nested dicts (last duplicate key wins)."""
    stack, cur, key = [], {}, None
    for m in _TOKEN.finditer(text):
        s, brace = m.group(1), m.group(2)
        if brace == "{":
            new = {}
            cur[key] = new
            stack.append(cur)
            cur, key = new, None
        elif brace == "}":
            cur, key = stack.pop() if stack else cur, None
        elif key is None:
            key = s
        else:
            cur[key] = s
            key = None
    return cur


def binds(text):
    """{action: "KEY" or "MOD+KEY"} from a citadelkeys_*.lst text (primary key)."""
    keys = parse_kv(text).get("KeyBindings", {}).get("Keys", {})
    out = {}
    for action, spec in keys.items():
        if isinstance(spec, dict) and "Key" in spec:
            k = spec["Key"]
            out[action] = (spec["Modifier"] + "+" + k) if spec.get("Modifier") else k
    return out


def autoexec_cvars(text):
    out = {}
    for line in text.splitlines():
        line = line.split("//", 1)[0].strip()
        if line and not line.startswith("echo"):
            k, _, v = line.partition(" ")
            out[k] = v.strip().strip('"')
    return out


def diff_binds(current, wanted):
    """{action: (current, wanted)} for every recommended action that differs."""
    return {a: (current.get(a), k) for a, k in sorted(wanted.items()) if current.get(a) != k}


def conflicts(table, actions):
    """{key: [actions]} where two of the given actions share one primary key."""
    seen = {}
    for a in actions:
        k = table.get(a)
        if k and k != "NONE":
            seen.setdefault(k, []).append(a)
    return {k: v for k, v in seen.items() if len(v) > 1}


def cm_per_360(sens, dpi, yaw=M_YAW):
    return round(360.0 / (yaw * sens * dpi) * 2.54, 1)


def _same(a, b):
    try:
        return abs(float(a) - float(b)) < 1e-4
    except (TypeError, ValueError):
        return str(a).lower() == str(b).lower()


def _userdata_dirs(steam):
    root = Path(steam) / "userdata"
    if not root.is_dir():
        return []
    return [d / vw_paths.APP_ID for d in sorted(root.iterdir()) if (d / vw_paths.APP_ID).is_dir()]


def check(steam=None):
    rec = recommended()
    steam = Path(steam) if steam else vw_paths.steam_root()
    wanted_cv = autoexec_cvars(AUTOEXEC.read_text(encoding="ascii"))
    rows = []
    for app in _userdata_dirs(steam):
        row = {}
        kf = app.joinpath(*KEYS_FILE)
        if kf.is_file():
            cur = binds(kf.read_text(encoding="utf-8", errors="replace"))
            row["bind_changes_left"] = {a: "%s -> %s" % v
                                        for a, v in diff_binds(cur, rec["binds"]).items()}
            merged = dict(cur, **rec["binds"])
            row["conflicts_after"] = conflicts(merged, rec["combat_actions"])
        saved = {}
        for parts in CONVAR_FILES:
            f = app.joinpath(*parts)
            if f.is_file():
                cv = parse_kv(f.read_text(encoding="utf-8", errors="replace"))
                saved.update(cv.get("config", {}).get("convars", {}))
        row["convars_not_yet_saved"] = {k: "%s -> %s" % (saved.get(k, "default"), v)
                                        for k, v in sorted(wanted_cv.items())
                                        if k in rec["convars_checked"] and not _same(saved.get(k), v)}
        rows.append(row)
    sens = float(wanted_cv.get("sensitivity", 1))
    return {"accounts": rows, "sensitivity": sens,
            "cm_per_360_at_assumed_dpi": cm_per_360(sens, rec["dpi_assumed"]),
            "dpi_assumed": rec["dpi_assumed"]}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vw_controls")
    ap.add_argument("cmd", choices=("check",))
    ap.parse_args(argv)
    print(json.dumps(check(), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
