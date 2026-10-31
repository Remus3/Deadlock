"""WCAG 2.x contrast for the companion app token set (VW-APP-UX).

    python tools/vw_contrast.py check     exit 1 if a pair is under its floor or
                                          the recorded ratios are stale
    python tools/vw_contrast.py update    rewrite "measured" in the token file

Tokens: config/app/tokens.json {"colors": {name: "#rrggbb"}, "plate_alpha",
"pairs": [{"fg", "bg", "min"}], "measured": {key: ratio}}. A pair whose bg is
"overlay.plate" is the translucent overlay plate; it is measured twice, as
composited over a black and over a white game frame (keys "<fg>@black",
"<fg>@white"), since the frame under the plate is unknown. Other keys read
"<fg> on <bg>". Ratios are rounded to 2 places.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "config" / "app" / "tokens.json"
PLATE = "overlay.plate"
FRAMES = (("black", "#000000"), ("white", "#ffffff"))


def _rgb(hexcolor):
    h = hexcolor.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _channel(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hexcolor):
    r, g, b = (_channel(c) for c in _rgb(hexcolor))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg):
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def composite(top, alpha, under):
    """Source-over of `top` at `alpha` on an opaque `under`, as #rrggbb."""
    mixed = (round(alpha * t + (1 - alpha) * u) for t, u in zip(_rgb(top), _rgb(under)))
    return "#" + "".join(f"{c:02x}" for c in mixed)


def measure(tokens):
    colors = tokens["colors"]
    rows = []
    for pair in tokens["pairs"]:
        fg = colors[pair["fg"]]
        if pair["bg"] == PLATE:
            for name, frame in FRAMES:
                bg = composite(colors[PLATE], tokens["plate_alpha"], frame)
                rows.append({"key": f"{pair['fg']}@{name}", "min": pair["min"],
                             "ratio": round(ratio(fg, bg), 2)})
        else:
            rows.append({"key": f"{pair['fg']} on {pair['bg']}", "min": pair["min"],
                         "ratio": round(ratio(fg, colors[pair["bg"]]), 2)})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("check", "update"))
    args = ap.parse_args(argv)
    tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
    rows = measure(tokens)
    if args.cmd == "update":
        tokens["measured"] = {r["key"]: r["ratio"] for r in rows}
        TOKENS.write_bytes((json.dumps(tokens, indent=2) + "\n").encode("ascii"))
    bad = 0
    for r in rows:
        flag = "ok" if r["ratio"] >= r["min"] else "UNDER"
        bad += flag != "ok"
        print(f"{r['key']}: {r['ratio']} (min {r['min']}) {flag}")
    stale = tokens.get("measured") != {r["key"]: r["ratio"] for r in rows}
    if stale:
        print("measured ratios are stale: run update")
    return 1 if bad or stale else 0


if __name__ == "__main__":
    sys.exit(main())
