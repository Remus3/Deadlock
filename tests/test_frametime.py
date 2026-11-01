"""vw_frametime: fps and CapFrameX-style lows from a PresentMon CSV fixture."""
from pathlib import Path

import pytest

import vw_frametime as F

FIX = Path(__file__).resolve().parent / "fixtures" / "frametime" / "presentmon_run.csv"


def test_fixture_metrics():
    # 198 frames at 4 ms, 2 at 20 ms (plus a dwm row and a bad row dropped).
    m = F.metrics(F.read_frametimes(FIX, process="project8.exe"))
    assert m["frames"] == 200
    assert m["avg_fps"] == pytest.approx(200 * 1000 / (198 * 4 + 2 * 20))
    assert m["low_1"] == pytest.approx(50.0)     # slowest 2 frames (1 percent)
    assert m["low_0_1"] == pytest.approx(50.0)   # slowest 1 frame (at least one)
    assert m["p1"] == pytest.approx(250.0)       # 99th percentile frame time 4 ms
    assert m["p0_1"] == pytest.approx(50.0)


def test_process_filter_keeps_other_rows_when_absent():
    assert len(F.read_frametimes(FIX)) == 201


def test_median_of_three_runs():
    runs = [dict(avg_fps=a, low_1=a / 2, low_0_1=a / 3, p1=a, p0_1=a) for a in (100, 300, 200)]
    assert F.median_of(runs)["avg_fps"] == 200
    assert F.median_of(runs)["low_1"] == 100


def test_cli_writes_markdown(tmp_path):
    out = tmp_path / "m.md"
    assert F.main([str(FIX), str(FIX), str(FIX), "--process", "project8.exe",
                   "--label", "baseline", "--md", str(out)]) == 0
    text = out.read_text(encoding="ascii")
    assert "# baseline" in text and "| median | | 240.4 | 50.0 | 50.0 | 250.0 | 50.0 |" in text


def test_missing_column_is_an_error(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n1,2\n", encoding="ascii")
    assert F.main([str(bad)]) == 2
