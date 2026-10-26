"""Patch the Deadlock video settings file from config/video.recommended.json.

    python tools/dl_video.py check            show file vs recommended (read only)
    python tools/dl_video.py apply [--file F] back up, then set the recommended keys

Rules (CLAUDE.md game safety floor):
- the file must already exist (the game writes it on first launch); a key that
  is not already in the file is never added;
- the game must not be running (deadlock.exe);
- the original is copied to ops/runtime/backup/<stamp>/ first; the change is
  read back after the write.
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

RECOMMENDED = ROOT / "config" / "video.recommended.json"
BACKUP = ROOT / "ops" / "runtime" / "backup"
_KV = re.compile(r'^(\s*)"(?P<k>[^"]+)"(\s+)"(?P<v>[^"]*)"(.*)$')


def recommended_keys(path=RECOMMENDED):
    return json.loads(Path(path).read_text(encoding="ascii"))["keys"]


def patch(text, wanted):
    """(new text, {key: (old, new)}) - only keys already present change."""
    changed, lines = {}, text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        m = _KV.match(line.rstrip("\r\n"))
        if not m or m.group("k") not in wanted:
            continue
        new = wanted[m.group("k")]
        if m.group("v") != new:
            eol = line[len(line.rstrip("\r\n")):]
            lines[i] = '%s"%s"%s"%s"%s%s' % (m.group(1), m.group("k"), m.group(3), new,
                                            m.group(5), eol)
            changed[m.group("k")] = (m.group("v"), new)
    return "".join(lines), changed


def read_values(text, keys):
    out = {}
    for line in text.splitlines():
        m = _KV.match(line)
        if m and m.group("k") in keys:
            out[m.group("k")] = m.group("v")
    return out


def game_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq deadlock.exe", "/NH"],
                             capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return True  # unknown = do not touch
    return "deadlock.exe" in out.lower()


def video_file():
    doc = dl_paths.summary()
    return Path(doc["video"][0]) if doc.get("video") else None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dl_video")
    ap.add_argument("cmd", choices=("check", "apply"))
    ap.add_argument("--file")
    a = ap.parse_args(argv)
    f = Path(a.file) if a.file else video_file()
    if f is None or not f.is_file():
        print("no video file yet: launch the game once, then re-run")
        return 3
    wanted = recommended_keys()
    text = f.read_bytes().decode("utf-8", "replace")
    new, changed = patch(text, wanted)
    if a.cmd == "check":
        print(json.dumps({"present": read_values(text, wanted), "would_change": changed},
                         indent=1, sort_keys=True))
        return 0
    if game_running():
        print("refused: deadlock.exe is running")
        return 4
    if not changed:
        print("no change")
        return 0
    dst = BACKUP / time.strftime("%Y%m%d-%H%M%S")
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, dst / f.name)
    f.write_bytes(new.encode("utf-8"))
    back = read_values(f.read_bytes().decode("utf-8", "replace"), wanted)
    bad = {k: v for k, (_o, v) in changed.items() if back.get(k) != v}
    print(json.dumps({"changed": changed, "backup": str(dst / f.name), "readback_bad": bad},
                     indent=1, sort_keys=True))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
