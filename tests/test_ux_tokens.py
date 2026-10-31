"""VW-APP-UX token set (docs/research/ux.md, config/app/tokens.json).

Every declared foreground / background pair meets its WCAG 2.x contrast floor,
overlay pairs on the plate as composited over BOTH a black and a white game
frame (the worst cases under a translucent plate), and the ratios recorded in
the token file are the ones the formula gives today.
"""
import json
from pathlib import Path

import pytest

import vw_contrast

ROOT = Path(__file__).resolve().parents[1]
TOKENS = json.loads((ROOT / "config" / "app" / "tokens.json").read_text(encoding="utf-8"))


def test_formula_matches_wcag_reference_points():
    assert vw_contrast.ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert vw_contrast.ratio("#ffffff", "#ffffff") == pytest.approx(1.0)
    # WCAG's own example threshold: #767676 on white is the 4.5:1 gray.
    assert vw_contrast.ratio("#767676", "#ffffff") == pytest.approx(4.54, abs=0.01)


def test_composite_of_plate_over_frame():
    assert vw_contrast.composite("#000000", 1.0, "#ffffff") == "#000000"
    assert vw_contrast.composite("#000000", 0.0, "#ffffff") == "#ffffff"
    assert vw_contrast.composite("#000000", 0.5, "#ffffff") == "#808080"


def test_every_pair_meets_its_floor():
    rows = vw_contrast.measure(TOKENS)
    assert rows, "no pairs declared"
    bad = [r for r in rows if r["ratio"] < r["min"]]
    assert bad == []


def test_recorded_ratios_are_current():
    rows = vw_contrast.measure(TOKENS)
    recorded = TOKENS["measured"]
    assert {r["key"]: r["ratio"] for r in rows} == recorded


def test_overlay_pairs_cover_both_frames():
    keys = {r["key"] for r in vw_contrast.measure(TOKENS)}
    for pair in TOKENS["pairs"]:
        if pair["bg"] == "overlay.plate":
            assert pair["fg"] + "@black" in keys and pair["fg"] + "@white" in keys
