"""Locate the Steam install, the Deadlock install and its config files.

Read only. Every path is resolved at run time, so no tracked file names a
machine path (the repo is public).

    python tools/vw_paths.py            print a JSON summary (paths redacted)
    python tools/vw_paths.py --raw      print real paths (local use only)
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

APP_ID = "1422450"
INSTALL_DIR = "Deadlock"
GAME_EXE = ("game", "bin", "win64", "deadlock.exe")
CFG_REL = ("game", "citadel", "cfg")
AUTOEXEC = "autoexec.cfg"
VIDEO_NAMES = ("video.txt",)
# The game writes its video file per Steam account, not in the install:
# <Steam>/userdata/<account>/<app>/local/cfg/video.txt (read 2026-10-25).
USERDATA_CFG = ("local", "cfg")
DEFAULT_STEAM = r"C:\Program Files (x86)\Steam"

_PATH_LINE = re.compile(r'^\s*"path"\s*"(?P<p>[^"]+)"\s*$')


def steam_root(reader=None):
    """Steam's install dir: HKCU SteamPath, else HKLM InstallPath, else the default."""
    reader = reader or _reg_value
    for key, name in ((r"HKCU\Software\Valve\Steam", "SteamPath"),
                      (r"HKLM\SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath")):
        val = reader(key, name)
        if val:
            return Path(val.replace("/", "\\") if os.name == "nt" else val)
    return Path(DEFAULT_STEAM)


def _reg_value(key, name):
    if os.name != "nt":
        return None
    try:
        out = subprocess.run(["reg", "query", key, "/v", name], capture_output=True,
                             text=True, timeout=10, creationflags=0x08000000).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[0] == name:
            return parts[2].strip()
    return None


def library_paths(vdf_text):
    """Every "path" value in a libraryfolders.vdf text, unescaped."""
    out = []
    for line in vdf_text.splitlines():
        m = _PATH_LINE.match(line)
        if m:
            out.append(m.group("p").replace("\\\\", "\\"))
    return out


def find_install(steam=None):
    """(library root, game dir) of the first library holding the app manifest."""
    steam = Path(steam) if steam else steam_root()
    vdf = steam / "steamapps" / "libraryfolders.vdf"
    libs = [steam]
    try:
        libs += [Path(p) for p in library_paths(vdf.read_text(encoding="utf-8", errors="replace"))]
    except OSError:
        pass
    for lib in libs:
        if (lib / "steamapps" / ("appmanifest_%s.acf" % APP_ID)).is_file():
            return lib, lib / "steamapps" / "common" / INSTALL_DIR
    return None, None


def summary(steam=None):
    steam = Path(steam) if steam else steam_root()
    lib, game = find_install(steam)
    doc = {"steam": str(steam), "library": str(lib) if lib else None,
           "game": str(game) if game else None}
    if game:
        cfg = game.joinpath(*CFG_REL)
        doc["cfg"] = str(cfg)
        doc["exe"] = str(game.joinpath(*GAME_EXE))
        doc["exe_exists"] = game.joinpath(*GAME_EXE).is_file()
        doc["autoexec_exists"] = (cfg / AUTOEXEC).is_file()
        doc["video"] = video_files(steam, cfg)
    return doc


def video_files(steam, cfg=None):
    """Every existing video file: per-account userdata first, then the install cfg."""
    out = []
    root = Path(steam) / "userdata"
    if root.is_dir():
        for acct in sorted(root.iterdir()):
            d = acct.joinpath(APP_ID, *USERDATA_CFG)
            out += [str(d / n) for n in VIDEO_NAMES if (d / n).is_file()]
    if cfg is not None:
        out += [str(Path(cfg) / n) for n in VIDEO_NAMES if (Path(cfg) / n).is_file()]
    return out


_ACCOUNT = re.compile(r"([\\/]userdata[\\/])\d+")


def redact(doc):
    """Replace every real prefix and Steam account id with a placeholder."""
    steam, game = doc.get("steam"), doc.get("game")

    def one(v):
        if game:
            v = v.replace(game, "<Deadlock>")
        if steam:
            v = v.replace(steam, "<Steam>")
        return _ACCOUNT.sub(r"\1<id>", v)

    out = {}
    for k, v in doc.items():
        if isinstance(v, str):
            v = one(v)
        elif isinstance(v, list):
            v = [one(x) if isinstance(x, str) else x for x in v]
        out[k] = v
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    doc = summary()
    print(json.dumps(doc if "--raw" in argv else redact(doc), indent=1, sort_keys=True))
    return 0 if doc.get("game") else 1


if __name__ == "__main__":
    sys.exit(main())
