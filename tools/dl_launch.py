"""Steam launch options for Deadlock (localconfig.vdf), from config/launch_options.txt.

    python tools/dl_launch.py check     current vs wanted, every Steam account (read only)
    python tools/dl_launch.py apply     back up, write, read back - ONLY while Steam is
                                        not running (Steam rewrites the file on exit)

Only the "LaunchOptions" value inside the existing apps/1422450 block changes;
a block Steam has not created yet is never invented (exit 3). Output never
prints an account id or a path.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dl_paths  # noqa: E402

WANTED = ROOT / "config" / "launch_options.txt"
BACKUP = ROOT / "ops" / "runtime" / "backup"
APP = dl_paths.APP_ID
_TOKEN = re.compile(r'"((?:[^"\\]|\\.)*)"|([{}])')


def wanted():
    return WANTED.read_text(encoding="ascii").splitlines()[0].strip()


def find_app_block(lines):
    """(start, end) line indexes of the apps/<APP> block body, or None."""
    stack, pending, start = [], None, None
    for i, line in enumerate(lines):
        toks = [m.group(1) if m.group(1) is not None else m.group(2) for m in _TOKEN.finditer(line)]
        j = 0
        while j < len(toks):
            t = toks[j]
            if t == "{":
                stack.append(pending)
                pending = None
                if len(stack) >= 2 and stack[-1] == APP and str(stack[-2]).lower() == "apps":
                    start = i
            elif t == "}":
                if start is not None and len(stack) >= 2 and stack[-1] == APP \
                        and str(stack[-2]).lower() == "apps":
                    return start, i
                if stack:
                    stack.pop()
            else:
                if j + 1 < len(toks) and toks[j + 1] not in ("{", "}"):
                    j += 2
                    pending = None
                    continue
                pending = t
            j += 1
    return None


def get_option(lines, block):
    s, e = block
    for line in lines[s + 1:e]:
        m = re.match(r'^\s*"LaunchOptions"\s+"((?:[^"\\]|\\.)*)"', line)
        if m:
            return m.group(1)
    return None


def set_option(lines, block, value):
    s, e = block
    esc = value.replace("\\", "\\\\").replace('"', '\\"')
    for i in range(s + 1, e):
        m = re.match(r'^(\s*)"LaunchOptions"(\s+)"(?:[^"\\]|\\.)*"(.*)$', lines[i].rstrip("\r\n"))
        if m:
            eol = lines[i][len(lines[i].rstrip("\r\n")):]
            lines[i] = '%s"LaunchOptions"%s"%s"%s%s' % (m.group(1), m.group(2), esc, m.group(3), eol)
            return lines
    indent = re.match(r"^(\s*)", lines[e]).group(1) + "\t"
    eol = lines[e][len(lines[e].rstrip("\r\n")):] or "\n"
    lines.insert(e, '%s"LaunchOptions"\t\t"%s"%s' % (indent, esc, eol))
    return lines


def configs():
    steam = dl_paths.steam_root()
    return sorted((steam / "userdata").glob("*/config/localconfig.vdf"))


def steam_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq steam.exe", "/NH"],
                             capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return True
    return "steam.exe" in out.lower()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dl_launch")
    ap.add_argument("cmd", choices=("check", "apply"))
    a = ap.parse_args(argv)
    want, rows, rc = wanted(), [], 0
    if a.cmd == "apply" and steam_running():
        print(json.dumps({"refused": "steam.exe is running", "wanted": want}))
        return 4
    for n, f in enumerate(configs()):
        lines = f.read_bytes().decode("utf-8", "replace").splitlines(keepends=True)
        block = find_app_block(lines)
        row = {"account": n, "app_block": block is not None,
               "current": get_option(lines, block) if block else None, "wanted": want}
        if a.cmd == "apply" and block and row["current"] != want:
            dst = BACKUP / time.strftime("%Y%m%d-%H%M%S")
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst / ("localconfig-%d.vdf" % n))
            f.write_bytes("".join(set_option(lines, block, want)).encode("utf-8"))
            back = f.read_bytes().decode("utf-8", "replace").splitlines(keepends=True)
            row["readback"] = get_option(back, find_app_block(back))
            rc = rc or (0 if row["readback"] == want else 1)
        elif a.cmd == "apply" and not block:
            rc = rc or 3
        rows.append(row)
    print(json.dumps(rows, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())
