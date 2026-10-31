"""Flag each cvar an autoexec sets as ok / cheat / devonly / unknown.

    python tools/vw_cvar_check.py check [--cfg F ...] [--live] [--list F] [--dump F] [--json]
    python tools/vw_cvar_check.py fetch [--out DIR]

Flag sources (merged; a cvar is flagged when ANY source flags it):
- the community API cvar list `GET /v1/assets/convars?client_version=<n>`
  (numeric FCVAR_* flags; client and server dll only), cached by `fetch` in
  the gitignored ops/runtime/gamedata/raw/ through vw_gamedata's GET; the
  newest cached copy is the default `--list`;
- a `cvarlist` console dump (`--dump`): lines `name : value : flags : help`,
  flags as space-, comma- or quote-separated words (`cheat`, `dev` ...).

Verdicts: ok (listed, neither flag), cheat (FCVAR_CHEAT), devonly
(FCVAR_DEVELOPMENTONLY), unknown (in no source: the API list does not cover
engine2 cvars such as fps_max, so unknown is a prompt for a dump, not a
failure), command (a console command such as echo or exec, not a cvar).
Exit 1 when any cheat or devonly cvar is present, 2 when no flag source
exists, else 0. Safety floor: CLAUDE.md "Game safety floor". Read-only.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_CFG = ROOT / "config" / "autoexec.cfg"
RAW_DIR = ROOT / "ops" / "runtime" / "gamedata" / "raw"
LIST_GLOB = "v1_assets_convars_client_version_*.json"

# Source 2 FCVAR bits (tier1 convar.h as used by the Source 2 SDK headers).
FCVAR_DEVELOPMENTONLY = 1 << 1
FCVAR_CHEAT = 1 << 14

# Console commands an autoexec may use that are not cvars.
COMMANDS = frozenset({
    "echo", "exec", "bind", "unbind", "unbindall", "alias", "toggle",
    "incrementvar", "host_writeconfig", "clear", "say",
})
DUMP_CHEAT = frozenset({"cheat"})
DUMP_DEV = frozenset({"dev", "devonly", "development_only", "developmentonly"})
FAIL = ("cheat", "devonly")


def parse_cfg(text):
    """[(line, name, args)] for every statement; `//` comments, `;` splits."""
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        for stmt in _split(line):
            parts = stmt.split(None, 1)
            if parts:
                out.append((no, parts[0].lower(), parts[1] if len(parts) > 1 else ""))
    return out


def _split(line):
    """Split one line on `;` outside quotes, dropping a `//` comment."""
    stmts, cur, quoted, i = [], [], False, 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            quoted = not quoted
        elif not quoted and line.startswith("//", i):
            break
        elif not quoted and ch == ";":
            stmts.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    stmts.append("".join(cur).strip())
    return [s for s in stmts if s]


def load_api_list(data):
    """API payload {name: {"flags": int, ...}} -> {name: set(verdict words)}."""
    db = {}
    for name, info in data.items():
        flags = int(info.get("flags", 0)) if isinstance(info, dict) else 0
        tags = set()
        if flags & FCVAR_CHEAT:
            tags.add("cheat")
        if flags & FCVAR_DEVELOPMENTONLY:
            tags.add("devonly")
        db[name.lower()] = tags
    return db


def load_dump(text):
    """`cvarlist` dump text -> {name: set(verdict words)}; non-matching lines skipped."""
    db = {}
    for line in text.splitlines():
        cols = [c.strip() for c in line.split(":")]
        if len(cols) < 3 or not re.fullmatch(r"[A-Za-z_][\w.+-]*", cols[0]):
            continue
        words = {w.lower() for w in re.split(r"[\s,\"]+", cols[2]) if w}
        tags = set()
        if words & DUMP_CHEAT:
            tags.add("cheat")
        if words & DUMP_DEV:
            tags.add("devonly")
        db[cols[0].lower()] = tags
    return db


def merge(*dbs):
    out = {}
    for db in dbs:
        for name, tags in db.items():
            out.setdefault(name, set()).update(tags)
    return out


def classify(name, db):
    if name in COMMANDS:
        return "command"
    if name not in db:
        return "unknown"
    tags = db[name]
    if "cheat" in tags:
        return "cheat"
    if "devonly" in tags:
        return "devonly"
    return "ok"


def check_text(text, db):
    """[{"line", "name", "verdict"}] for one cfg text."""
    return [{"line": no, "name": name, "verdict": classify(name, db)}
            for no, name, _ in parse_cfg(text)]


def default_list(raw_dir=RAW_DIR):
    """Newest cached API cvar list by client version, or None."""
    def ver(p):
        m = re.search(r"_(\d+)\.json$", p.name)
        return int(m.group(1)) if m else -1
    found = sorted(Path(raw_dir).glob(LIST_GLOB), key=ver)
    return found[-1] if found else None


def live_cfg():
    import vw_paths
    _, game = vw_paths.find_install()
    return Path(game).joinpath(*vw_paths.CFG_REL, vw_paths.AUTOEXEC)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--cfg", action="append", default=[])
    c.add_argument("--live", action="store_true", help="also the game's autoexec (read only)")
    c.add_argument("--list", help="API cvar list JSON (default: newest cached)")
    c.add_argument("--dump", action="append", default=[], help="cvarlist dump text")
    c.add_argument("--json", action="store_true")
    f = sub.add_parser("fetch")
    f.add_argument("--out", default=str(RAW_DIR.parent))
    a = ap.parse_args(argv)

    if a.cmd == "fetch":
        import vw_gamedata as G
        latest = max(G._get("/v1/assets/client-versions", a.out))
        data = G._get(f"/v1/assets/convars?client_version={latest}", a.out)
        print(f"client_version {latest}: {len(data)} cvars cached")
        return 0

    dbs, sources = [], []
    lst = Path(a.list) if a.list else default_list()
    if lst and lst.is_file():
        dbs.append(load_api_list(json.loads(lst.read_text(encoding="utf-8"))))
        sources.append(lst.name)
    for d in a.dump:
        dbs.append(load_dump(Path(d).read_text(encoding="utf-8", errors="replace")))
        sources.append(Path(d).name)
    if not dbs:
        print("no cvar flag source: run `vw_cvar_check.py fetch` or pass --dump",
              file=sys.stderr)
        return 2
    db = merge(*dbs)

    cfgs = [Path(p) for p in a.cfg] or [REPO_CFG]
    if a.live:
        cfgs.append(live_cfg())
    report, bad = {"sources": sources, "files": []}, 0
    for p in cfgs:
        label = "<Deadlock>/game/citadel/cfg/autoexec.cfg" if a.live and p == cfgs[-1] \
            else p.name
        rows = check_text(p.read_text(encoding="utf-8", errors="replace"), db)
        bad += sum(r["verdict"] in FAIL for r in rows)
        report["files"].append({"file": label, "rows": rows})
    if a.json:
        print(json.dumps(report, indent=1))
    else:
        print("sources: " + ", ".join(sources))
        for f_ in report["files"]:
            for r in f_["rows"]:
                print(f"{f_['file']}:{r['line']}: {r['name']}: {r['verdict']}")
        print(f"flagged (cheat/devonly): {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
