"""vw_lane: spawn options follow FLEET-COMMON 10 (sonnet unless code, low effort for inbox)."""
import fleet_headless
import pytest
import vw_lane


def test_build_without_code_is_sonnet():
    p = vw_lane.plan("build", False, "build")
    assert p["model"] == "sonnet" and p["effort"] is None and p["governor"] == "queued"


def test_code_job_uses_the_default_model():
    assert vw_lane.plan("build", True, "build")["model"] is None


def test_writes_code_job_gets_named_permissions_and_no_blanket_bypass():
    extra = vw_lane.plan("build", True, "order")["extra"]
    assert extra[:3] == ("--permission-mode", "acceptEdits", "--allowedTools")
    assert len(extra) == 4
    tools = extra[3].split(",")
    assert ("Bash(python ops/fleet_kit/fleet_gitlock.py run --owner * -- git commit:*)"
            in tools)
    assert ("PowerShell(python ops/fleet_kit/fleet_suite_gate.py run --owner * -- "
            "python -m pytest:*)" in tools)
    text = " ".join(extra)
    assert "bypass" not in text.lower() and "push" not in text
    assert "vw_video" not in text and "vw_launch" not in text
    fleet_headless.check_door(False, extra, True)  # the kit's door takes this shape


def test_read_only_job_gets_no_extra_permissions():
    assert vw_lane.plan("review", False, "build", "low")["extra"] == ()


def test_job_passes_the_planned_permissions_to_spawn(monkeypatch, tmp_path):
    monkeypatch.setattr(vw_lane, "ROOT", tmp_path)
    fh = _FakeKit({"rc": 0, "error": None, "is_error": False})
    opts = vw_lane.plan("build", True, "order")
    vw_lane._job(fh, {"index": 0, "worktree": str(tmp_path)}, "build", "n", "p", opts, "r")
    assert fh.kw["extra"] == opts["extra"]


def test_inbox_is_low_effort():
    assert vw_lane.plan("review", False, "inbox")["effort"] == "low"


def test_bad_lane_or_kind_refuses():
    with pytest.raises(ValueError):
        vw_lane.plan("other", False, "build")
    with pytest.raises(ValueError):
        vw_lane.plan("build", False, "chat")


def test_cap_follows_the_kit():
    # v25: no hard-coded cap; None = the live lane_cap_max (default 3 here).
    assert vw_lane.CAP is None
    assert vw_lane.cap() == 3


class _FakeKit:
    """Stands in for fleet_headless: records spawn kwargs, returns a canned line."""

    def __init__(self, line):
        self.line, self.kw, self.progress = line, None, []

    def spawn(self, root, code, prompt, **kw):
        self.kw = kw
        return dict(self.line)

    def write_progress(self, root, task, pct, step, eta, status):
        self.progress.append(status)


def _run_job(monkeypatch, tmp_path, line):
    monkeypatch.setattr(vw_lane, "ROOT", tmp_path)
    fh = _FakeKit(line)
    opts = vw_lane.plan("review", False, "build", "low")
    out = vw_lane._job(fh, {"index": 0, "worktree": str(tmp_path)}, "review", "n", "p",
                       opts, "vw-review-1")
    return fh, out


def test_job_captures_log_and_stderr(monkeypatch, tmp_path):
    fh, out = _run_job(monkeypatch, tmp_path, {"rc": 0, "error": None, "is_error": False})
    log, _fail = vw_lane.log_paths(tmp_path, "vw-review-1")
    assert fh.kw["log_path"] == str(log) and fh.kw["return_stderr"] is True
    assert "runtime" in log.parts  # gitignored ops/runtime/
    assert fh.progress[-1] == "done" and "fail_record" not in out


def test_failed_job_writes_a_fail_record(monkeypatch, tmp_path):
    import json
    fh, out = _run_job(monkeypatch, tmp_path, {"rc": 1, "error": None, "is_error": True,
                                               "result": "API Error: 502", "stderr": "boom"})
    _log, fail = vw_lane.log_paths(tmp_path, "vw-review-1")
    rec = json.loads(fail.read_text(encoding="utf-8"))
    assert rec["result"] == "API Error: 502" and rec["stderr"] == "boom" and rec["rc"] == 1
    assert out["fail_record"] == "ops/runtime/lane_logs/vw-review-1.fail.json"
    assert fh.progress[-1] == "failed"


def test_is_error_with_rc_zero_counts_as_failed(monkeypatch, tmp_path):
    fh, out = _run_job(monkeypatch, tmp_path, {"rc": 0, "error": None, "is_error": True})
    assert fh.progress[-1] == "failed" and "fail_record" in out
