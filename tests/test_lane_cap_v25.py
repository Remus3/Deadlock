"""Kit v25 LANE-CAP guard (MAIN ORDER 2026-10-27-2136 section 5 item 4).

The VW lane driver's cap and governor slot count follow the machine config
(FLEET_LANES_CONFIG here; ~/.fleet/lanes.json live), with no hard-coded 3, and
the driver never kills or terminates a worker when should_yield is True.
"""
import ast
import contextlib
import json
from pathlib import Path

import fleet_lanes
import vw_lane


def test_cap_and_slots_read_the_config(tmp_path, monkeypatch):
    cfg = tmp_path / "lanes.json"
    cfg.write_text(json.dumps({"governor_width": 5, "lane_cap_max": 5}), encoding="ascii")
    monkeypatch.setenv(fleet_lanes.CONFIG_ENV, str(cfg))
    assert vw_lane.cap() == 5
    assert vw_lane.slots() == 5


def test_cap_and_slots_default_to_3_without_the_file(tmp_path, monkeypatch):
    monkeypatch.setenv(fleet_lanes.CONFIG_ENV, str(tmp_path / "missing.json"))
    assert vw_lane.cap() == 3
    assert vw_lane.slots() == 3


def test_no_hard_coded_cap_or_slot_count():
    tree = ast.parse(Path(vw_lane.__file__).read_text(encoding="ascii"))
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg in ("cap", "width"):
            assert not isinstance(node.value, ast.Constant) or node.value.value is None


class _Spy:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*a, **k):
            self.calls.append(name)
            return {"rc": 0}
        return record


def test_should_yield_true_starts_nothing_and_kills_nothing(monkeypatch):
    fh = _Spy()

    class FL:
        LaneRefused = fleet_lanes.LaneRefused

        @staticmethod
        def should_yield(code):
            assert code == "VW"
            return True

        @staticmethod
        def run_lane(*a, **k):
            raise AssertionError("no lane may be claimed when should_yield is True")

    monkeypatch.setattr(vw_lane, "_kit", lambda: (fh, FL))
    killed = []
    import os
    import subprocess
    monkeypatch.setattr(os, "kill", lambda *a, **k: killed.append("os.kill"))
    monkeypatch.setattr(subprocess.Popen, "kill", lambda self: killed.append("kill"))
    monkeypatch.setattr(subprocess.Popen, "terminate", lambda self: killed.append("terminate"))
    line = vw_lane.run("build", "n", "p")
    assert line["retry"] is True and line["rc"] is None
    assert fh.calls == [] and killed == []


def test_admission_refusal_is_retry_next_tick(monkeypatch):
    fh = _Spy()

    class FL:
        LaneRefused = fleet_lanes.LaneRefused

        @staticmethod
        def should_yield(code):
            return False

        @staticmethod
        @contextlib.contextmanager
        def run_lane(*a, **k):
            raise fleet_lanes.LaneRefused("admission: free RAM below floor")
            yield  # pragma: no cover

    monkeypatch.setattr(vw_lane, "_kit", lambda: (fh, FL))
    line = vw_lane.run("review", "n", "p")
    assert line["retry"] is True and "admission" in line["error"] and fh.calls == []


def test_driver_source_never_kills():
    src = Path(vw_lane.__file__).read_text(encoding="ascii")
    for word in (".kill(", ".terminate(", "os.kill", "taskkill", "TerminateProcess"):
        assert word not in src
