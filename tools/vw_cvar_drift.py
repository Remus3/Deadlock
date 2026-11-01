"""Flag autoexec convars removed or renamed between two game patches.

    python tools/vw_cvar_drift.py fetch [--count N] [--out DIR]
    python tools/vw_cvar_drift.py check [--old F] [--new F] [--cfg F ...] [--json]

Source: the public GameTracking-Deadlock convar dump
(`DumpSource2/convars.txt`, one entry per convar:
`name default (flag flag ...)` then a tab-indented help line). `fetch` saves
the dump at each of the newest N commits that touched it (one commit per game
patch; the commit subject starts with the build number) to the gitignored
ops/runtime/cvar_drift/<build>-<sha10>.txt. `check` with no --old / --new
compares the two newest cached dumps.

Verdicts per autoexec convar (console commands such as echo / exec skipped):
- ok       - in both dumps;
- removed  - in the old dump, not in the new one;
- renamed  - removed, and a new-only convar is a close name match (listed);
- added    - only in the new dump (it was unknown to the old patch);
- absent   - in neither dump;
- and `cheat` / `devonly` is appended when the new dump flags it so.
Exit 1 when any convar is removed, renamed, absent, cheat or devonly, else 0.
Read-only: it reads the dumps and the autoexec, never a game file.
"""

import argparse
import difflib
import json
import re
import sys
import urllib.request
from pathlib import Path

import vw_cvar_check

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "ops" / "runtime" / "cvar_drift"
REPO = "SteamDatabase/GameTracking-Deadlock"
DUMP_PATH = "DumpSource2/convars.txt"
LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s.*\(([^()]*)\)\s*$|^([A-Za-z_][A-Za-z0-9_.]*)\s*$")
BAD = ("removed", "renamed", "absent", "cheat", "devonly")


def parse_dump(text):
    """{name: set(flag words)} from a convars.txt dump (help lines skipped)."""
    db = {}
    for line in text.splitlines():
        if not line or line[0] in " \t":
            continue
        m = LINE.match(line.rstrip())
        if not m:
            first = line.split(None, 1)[0]
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", first):
                db[first.lower()] = set()
            continue
        name = (m.group(1) or m.group(3)).lower()
        db[name] = set((m.group(2) or "").lower().split())
    return db


def drift(cvars, old, new):
    """[(name, verdict, notes)] for each cvar name, old/new = parse_dump()."""
    new_only = sorted(set(new) - set(old))
    out = []
    for name in cvars:
        notes = []
        if name in old and name in new:
            verdict = "ok"
        elif name in old:
            close = difflib.get_close_matches(name, new_only, n=3, cutoff=0.75)
            verdict, notes = ("renamed", close) if close else ("removed", [])
        elif name in new:
            verdict = "added"
        else:
            verdict = "absent"
        flags = new.get(name, set())
        if "cheat" in flags:
            verdict += "+cheat"
        if flags & {"developmentonly", "devonly"}:
            verdict += "+devonly"
        out.append((name, verdict, notes))
    return out


def cfg_cvars(paths):
    seen = []
    for p in paths:
        for _, name, _ in vw_cvar_check.parse_cfg(Path(p).read_text(encoding="utf-8")):
            if name not in vw_cvar_check.COMMANDS and name not in seen:
                seen.append(name)
    return seen


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "VeilWalker-cvar-drift",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch(count, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    commits = json.loads(_get(f"https://api.github.com/repos/{REPO}/commits"
                              f"?path={DUMP_PATH}&per_page={int(count)}"))
    saved = []
    for c in commits:
        sha = c["sha"]
        build = re.match(r"\d+", c["commit"]["message"])
        dest = out_dir / f"{build.group(0) if build else '0'}-{sha[:10]}.txt"
        if not dest.exists():
            dest.write_bytes(_get(f"https://raw.githubusercontent.com/{REPO}/{sha}/{DUMP_PATH}"))
        saved.append(dest)
    return saved


def newest_two(cache):
    files = sorted(Path(cache).glob("*-*.txt"),
                   key=lambda p: int(p.name.split("-", 1)[0]) if p.name.split("-", 1)[0].isdigit() else -1)
    return (files[-2], files[-1]) if len(files) >= 2 else (None, None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--count", type=int, default=2)
    f.add_argument("--out", default=str(CACHE))
    c = sub.add_parser("check")
    c.add_argument("--old")
    c.add_argument("--new")
    c.add_argument("--cfg", action="append")
    c.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        for p in fetch(a.count, a.out):
            print(p.name)
        return 0
    old_p, new_p = a.old, a.new
    if not (old_p and new_p):
        o, n = newest_two(CACHE)
        old_p, new_p = old_p or o, new_p or n
    if not (old_p and new_p):
        print("error: need two dumps (--old/--new or `fetch` first)", file=sys.stderr)
        return 2
    old = parse_dump(Path(old_p).read_text(encoding="utf-8"))
    new = parse_dump(Path(new_p).read_text(encoding="utf-8"))
    rows = drift(cfg_cvars(a.cfg or [vw_cvar_check.REPO_CFG]), old, new)
    if a.json:
        print(json.dumps([{"cvar": n, "verdict": v, "candidates": c} for n, v, c in rows], indent=1))
    else:
        print(f"old: {Path(old_p).name}  new: {Path(new_p).name}")
        for n, v, cands in rows:
            print(f"- {n}: {v}" + (f" (candidates: {', '.join(cands)})" if cands else ""))
    return 1 if any(any(b in v for b in BAD) for _, v, _ in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
