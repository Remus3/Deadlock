"""Average fps and 1 / 0.1 percent lows from PresentMon CSV captures.

    python tools/vw_frametime.py RUN.csv [RUN.csv ...] [--label TEXT] [--md FILE] [--json]

Each CSV is one capture (PresentMon 1.x column `MsBetweenPresents`, or 2.x
`FrameTime` / `MsBetweenPresents`; the first present one is used). Rows of
other processes are dropped when `--process NAME` is given (column
`Application` or `ProcessName`). Read-only: it reads CSV files, nothing else.

Definitions (CapFrameX style, frame-time based, not fps-sample based):
- avg fps    = frames * 1000 / sum(frame times in ms) (time-weighted).
- 1% low     = 1000 / mean of the slowest 1 percent of frame times
               ("1% low average": the frames at or above the 99th
               percentile frame time, at least one frame).
- 0.1% low   = the same over the slowest 0.1 percent.
- P1 / P0.1  = 1000 / the 99th / 99.9th percentile frame time (nearest
               rank), printed alongside for comparison with other tools.

Several runs: each run is reported and the MEDIAN of each metric across runs
is the result (docs/measurement.md: three runs per configuration).
`--md FILE` writes the table to a markdown file (docs/measurements/).
"""

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

COLUMNS = ("MsBetweenPresents", "FrameTime", "msBetweenPresents")
PROC_COLUMNS = ("Application", "ProcessName")
METRICS = ("avg_fps", "low_1", "low_0_1", "p1", "p0_1")
NAMES = {"avg_fps": "avg fps", "low_1": "1% low", "low_0_1": "0.1% low",
         "p1": "P1", "p0_1": "P0.1"}


def read_frametimes(path, process=None):
    """Frame times in ms from one PresentMon CSV (positive finite values)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = csv.DictReader(f)
        fields = rows.fieldnames or []
        col = next((c for c in COLUMNS if c in fields), None)
        if col is None:
            raise ValueError(f"{path}: no frame time column ({', '.join(COLUMNS)})")
        pcol = next((c for c in PROC_COLUMNS if c in fields), None)
        out = []
        for row in rows:
            if process and pcol and (row.get(pcol) or "").lower() != process.lower():
                continue
            try:
                v = float(row[col])
            except (TypeError, ValueError):
                continue
            if math.isfinite(v) and v > 0:
                out.append(v)
    if not out:
        raise ValueError(f"{path}: no frames")
    return out


def _low(sorted_desc, frac):
    n = max(1, math.ceil(len(sorted_desc) * frac))
    return 1000.0 / statistics.fmean(sorted_desc[:n])


def _pct(sorted_asc, q):
    rank = max(1, math.ceil(q * len(sorted_asc)))
    return 1000.0 / sorted_asc[rank - 1]


def metrics(frametimes):
    """{avg_fps, low_1, low_0_1, p1, p0_1, frames} for one run."""
    asc = sorted(frametimes)
    desc = asc[::-1]
    return {
        "avg_fps": len(asc) * 1000.0 / sum(asc),
        "low_1": _low(desc, 0.01),
        "low_0_1": _low(desc, 0.001),
        "p1": _pct(asc, 0.99),
        "p0_1": _pct(asc, 0.999),
        "frames": len(asc),
    }


def median_of(runs):
    return {m: statistics.median(r[m] for r in runs) for m in METRICS}


def report(paths, process=None):
    runs = [dict(metrics(read_frametimes(p, process)), run=Path(p).name) for p in paths]
    return {"runs": runs, "median": median_of(runs)}


def markdown(doc, label=""):
    head = "| run | frames | " + " | ".join(NAMES[m] for m in METRICS) + " |"
    lines = []
    if label:
        lines += [f"# {label}", ""]
    lines += ["Definitions: tools/vw_frametime.py (CapFrameX-style lows).", "",
              head, "|" + "---|" * (len(METRICS) + 2)]
    for r in doc["runs"]:
        lines.append(f"| {r['run']} | {r['frames']} | "
                     + " | ".join(f"{r[m]:.1f}" for m in METRICS) + " |")
    med = doc["median"]
    lines.append("| median | | " + " | ".join(f"{med[m]:.1f}" for m in METRICS) + " |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--process", help="keep only rows of this process name")
    ap.add_argument("--label", default="")
    ap.add_argument("--md", help="write the markdown table to this file")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        doc = report(a.csv, a.process)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    text = markdown(doc, a.label)
    if a.md:
        Path(a.md).parent.mkdir(parents=True, exist_ok=True)
        Path(a.md).write_text(text, encoding="ascii", newline="\n")
    print(json.dumps(doc, indent=1) if a.json else text, end="" if not a.json else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
