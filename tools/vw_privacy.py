"""Leak gate for a PUBLIC repo: no machine path, id, email, host name or token.

    python tools/vw_privacy.py scan              every tracked file (exit 1 on a hit)
    python tools/vw_privacy.py --staged          added lines of the staged diff
    python tools/vw_privacy.py --pre-push <remote> <url>
                                                 added lines + messages of the pushed
                                                 range (git's ref lines on stdin)
    python tools/vw_privacy.py scrub <in> <out>  copy a game config with ids, names
                                                 and paths replaced

Generic shapes live here; per-host needles (user name, machine name, Steam
account id) live in the gitignored config/leak_needles.json:
    {"needles": ["...", "..."]}
The byte-pinned kit (ops/fleet_kit/) is MAIN's and is not scanned here.
Output names the file, line number and rule only, never the matched text.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEEDLES = ROOT / "config" / "leak_needles.json"
SKIP_PREFIXES = ("ops/fleet_kit/",)
ZERO = "0" * 40

RULES = (
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]*[A-Za-z]{2,}")),
    ("steam64", re.compile(r"\b7656119\d{10}\b")),
    ("user-path", re.compile(r"(?i)\b[a-z]:[\\/]+(users|documents and settings)[\\/]+[^\\/\s\"']+")),
    ("posix-user-path", re.compile(r"(?i)/(?:c/)?users/[^/\s\"']+/|/h(?:o)me/[^/\s\"']+/")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{10,}")),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("userdata-id", re.compile(r"(?i)userdata[\\/]+\d{5,}")),
)
# Placeholder emails that are documentation, not identities.
EMAIL_OK = re.compile(r"(?i)@(example\.(com|org|net)|users\.noreply\.github\.com)$")


def load_needles(path=NEEDLES):
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [str(n) for n in doc.get("needles", []) if str(n).strip() and len(str(n)) >= 4]


def line_hits(line, needles=()):
    """Rule names hit by one line of text."""
    hits = []
    for name, rx in RULES:
        for m in rx.finditer(line):
            if name == "email" and EMAIL_OK.search(m.group(0)):
                continue
            hits.append(name)
            break
    low = line.lower()
    for n in needles:
        if n.lower() in low:
            hits.append("needle")
            break
    return hits


def scan_text(label, text, needles=()):
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for rule in line_hits(line, needles):
            out.append("%s:%d %s" % (label, i, rule))
    return out


def _git(*args, stdin=None):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, input=stdin,
                          check=True).stdout.decode("utf-8", "replace")


def _skip(path):
    return any(path.startswith(p) for p in SKIP_PREFIXES)


def scan_tracked(needles=None):
    needles = load_needles() if needles is None else needles
    out = []
    for path in _git("ls-files", "-z").split("\0"):
        if not path or _skip(path):
            continue
        try:
            data = (ROOT / path).read_bytes()
        except OSError:
            continue
        if b"\0" in data[:4096]:
            continue
        out += scan_text(path, data.decode("utf-8", "replace"), needles)
    return out


def scan_diff(diff_text, needles=()):
    """Added lines of a unified diff (and nothing else)."""
    out, path, n = [], "?", 0
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else line[4:]
            continue
        if line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            n = int(m.group(1)) - 1 if m else 0
            continue
        if line.startswith("+") and not _skip(path):
            n += 1
            for rule in line_hits(line[1:], needles):
                out.append("%s:%d %s" % (path, n, rule))
        elif not line.startswith("-"):
            n += 1
    return out


def scan_staged(needles=None):
    needles = load_needles() if needles is None else needles
    return scan_diff(_git("diff", "--cached", "-U0", "--no-color"), needles)


def scan_push(stdin_text, needles=None):
    needles = load_needles() if needles is None else needles
    out = []
    for line in stdin_text.splitlines():
        parts = line.split()
        if len(parts) != 4 or parts[1] == ZERO:
            continue
        local, remote = parts[1], parts[3]
        rng = local if remote == ZERO else "%s..%s" % (remote, local)
        try:
            out += scan_diff(_git("log", "-p", "-U0", "--no-color", "--format=", rng), needles)
            out += scan_text("commit-messages", _git("log", "--format=%B", rng), needles)
        except subprocess.CalledProcessError:
            out.append("push-range unreadable %s" % rng[:20])
    return out


# ---------------------------------------------------------------- scrub

_SCRUB = (
    (re.compile(r"\b7656119\d{10}\b"), "<steamid64>"),
    (re.compile(r'(?im)^(\s*"name"\s*)"[^"]*"'), r'\1"<player-name>"'),
    (re.compile(r"(?i)userdata[\\/]+\d+"), "userdata/<account>"),
    (re.compile(r"(?i)\b[a-z]:[\\/]+[^\"\r\n]*?[\\/]+steamapps[\\/]+common[\\/]+deadlock"), "<Deadlock>"),
    (re.compile(r"(?i)\b[a-z]:[\\/]+[^\"\r\n]*?[\\/]+steam\b"), "<Steam>"),
    (re.compile(r"(?i)\b[a-z]:[\\/]+users[\\/]+[^\\/\s\"']+"), "<home>"),
)


def scrub_text(text, needles=()):
    for rx, rep in _SCRUB:
        text = rx.sub(rep, text)
    for n in needles:
        text = re.sub(re.escape(n), "<redacted>", text, flags=re.I)
    return text


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "scan"
    if cmd == "scrub":
        if len(argv) != 3:
            print("usage: vw_privacy.py scrub <in> <out>", file=sys.stderr)
            return 2
        src = Path(argv[1]).read_bytes().decode("utf-8", "replace")
        out = scrub_text(src, load_needles()).replace("\r\n", "\n")
        out = out.encode("ascii", "replace").decode("ascii")
        Path(argv[2]).parent.mkdir(parents=True, exist_ok=True)
        Path(argv[2]).write_bytes(out.encode("ascii"))
        left = scan_text(argv[2], out, load_needles())
        for h in left:
            print("[privacy] still present after scrub: " + h, file=sys.stderr)
        return 1 if left else 0
    if cmd == "--staged":
        hits = scan_staged()
    elif cmd == "--pre-push":
        hits = scan_push(sys.stdin.read())
    elif cmd == "scan":
        hits = scan_tracked()
    else:
        print(__doc__)
        return 2
    for h in hits:
        print("[privacy] HALT " + h, file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
