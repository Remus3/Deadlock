"""Release version step check (docs/release.md, operator order 2026-10-29).

    python tools/vw_release.py check <proposed>   exit 0 if <proposed> is exactly
                                                  one patch or one minor step from
                                                  the latest vX.Y.Z tag, else 1
    python tools/vw_release.py latest             print the latest released version

SemVer pre-1.0. From 0.M.P the only legal next versions are 0.M.(P+1) and
0.(M+1).0; with no tag yet, 0.1.0 or 0.0.1. 1.0.0 is an operator call, outside
this check. There is no time or day gate: only the step size is checked.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse(text):
    m = _SEMVER.match(text.strip()) if text else None
    return tuple(int(g) for g in m.groups()) if m else None


def allowed_next(latest):
    """The legal next versions after `latest` (None = no release yet)."""
    if latest is None:
        return [(0, 0, 1), (0, 1, 0)]
    major, minor, patch = latest
    return [(major, minor, patch + 1), (major, minor + 1, 0)]


def check(latest, proposed):
    """Return a list of problems; empty means the step is legal."""
    want = parse(proposed)
    if want is None:
        return ["proposed %r is not SemVer X.Y.Z" % proposed]
    have = None
    if latest is not None:
        have = parse(latest)
        if have is None:
            return ["latest %r is not SemVer X.Y.Z" % latest]
    legal = allowed_next(have)
    if want in legal:
        return []
    names = " or ".join("%d.%d.%d" % v for v in legal)
    return ["%d.%d.%d is not one step from %s; next must be %s"
            % (want + (latest or "no release", names))]


def latest_tag(repo=ROOT):
    out = subprocess.run(["git", "-C", str(repo), "tag", "--list"],
                         check=True, capture_output=True, text=True).stdout
    versions = [v for v in (parse(t) for t in out.split()) if v]
    return "%d.%d.%d" % max(versions) if versions else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("proposed")
    sub.add_parser("latest")
    a = ap.parse_args(argv)
    latest = latest_tag()
    if a.cmd == "latest":
        print(latest or "none")
        return 0
    problems = check(latest, a.proposed)
    for p in problems:
        print("REFUSED: " + p)
    if not problems:
        print("OK: %s -> %s" % (latest or "none", a.proposed.lstrip("v")))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
