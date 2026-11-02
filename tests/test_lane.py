"""vw_lane: spawn options follow FLEET-COMMON 10 (sonnet unless code, low effort for inbox)."""
import json
from datetime import datetime, timedelta, timezone
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
    assert ("Bash(python ops/fleet_kit/fleet_gitlock.py run --owner * -- git commit *)"
            in tools)
    assert ("PowerShell(python ops/fleet_kit/fleet_suite_gate.py run --owner * -- "
            "python -m pytest *)" in tools)
    assert "Bash(git add:*)" in tools
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


# ---- VW-2: cooldown after a failed public review (MAIN ORDER 2026-11-01 2005)

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
LIMIT_LINE = {"rc": 1, "result": "You have hit your usage limit, resets Nov 3"}


def test_limit_or_auth_failure_reads_rc_1_only():
    assert vw_lane.limit_or_auth_failure(LIMIT_LINE)
    assert vw_lane.limit_or_auth_failure({"rc": 1, "limit": "7-day"})
    assert vw_lane.limit_or_auth_failure({"rc": 1, "stderr": "API Error: 401 OAuth token expired"})
    assert vw_lane.limit_or_auth_failure({"rc": 1, "error": "proxy said 429"})
    assert not vw_lane.limit_or_auth_failure({"rc": 1, "result": "a test failed"})
    assert not vw_lane.limit_or_auth_failure({"rc": 0, "result": "hit your usage limit"})
    assert not vw_lane.limit_or_auth_failure({"rc": None, "error": "429"})


def test_review_skips_inside_the_window_and_is_due_after_it(tmp_path):
    state = vw_lane.record_review_failure(tmp_path, LIMIT_LINE, now=T0)
    assert datetime.fromisoformat(state["retry_after"]) == T0 + timedelta(hours=6)
    assert vw_lane.read_review_state(tmp_path) == state

    due, why = vw_lane.review_decision(state, T0 + timedelta(hours=5, minutes=59))
    assert not due and "cooldown until" in why and "\n" not in why
    due, _why = vw_lane.review_decision(state, T0 + timedelta(hours=6))
    assert due
    due, _why = vw_lane.review_decision(state, T0 + timedelta(hours=7))
    assert due


def test_cooldown_outranks_a_touched_surface_and_keeps_the_last_review(tmp_path):
    path = tmp_path / vw_lane.REVIEW_STATE_REL
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"last_commit": "abc", "last_date": "2026-11-01",
                                "result": "changed"}), encoding="ascii")
    state = vw_lane.record_review_failure(tmp_path, LIMIT_LINE, now=T0)
    assert state["last_commit"] == "abc" and state["last_date"] == "2026-11-01"
    assert not vw_lane.review_decision(state, T0 + timedelta(hours=1), surface=True)[0]
    # After the window the failed run is retried even with nothing else changed.
    assert vw_lane.review_decision(state, T0 + timedelta(hours=7))[0]


def test_other_failures_earn_no_cooldown(tmp_path):
    assert vw_lane.record_review_failure(tmp_path, {"rc": 1, "result": "boom"}, now=T0) is None
    assert vw_lane.read_review_state(tmp_path) is None
    assert vw_lane.review_decision(None, T0)[0]


def test_a_bad_retry_after_does_not_silence_the_review():
    assert vw_lane.review_cooldown({"retry_after": "soon"}, T0) is None
    assert vw_lane.review_cooldown({}, T0) is None
    assert vw_lane.review_decision({"retry_after": "soon"}, T0)[0]


def test_review_decision_keeps_the_existing_cadence():
    fresh = {"last_commit": "abc", "last_date": "2026-10-30", "result": "no-change"}
    assert not vw_lane.review_decision(fresh, T0)[0]
    assert vw_lane.review_decision(fresh, T0, surface=True)[0]
    old = dict(fresh, last_date="2026-10-25")
    assert vw_lane.review_decision(old, T0)[0]


def test_surface_touched_names():
    assert vw_lane.surface_touched(["README.md"])
    assert vw_lane.surface_touched([".github/workflows/ci.yml"])
    assert vw_lane.surface_touched(["docs/optimization.md"])
    assert not vw_lane.surface_touched(["docs/research/x.md", "docs/roadmap-archive.md"])
    assert not vw_lane.surface_touched(["tools/vw_lane.py", "tests/test_lane.py"])
    assert vw_lane.surface_touched(["tools/vw_new.py"], added=["tools/vw_new.py"])


def test_run_records_the_cooldown_only_for_the_public_review(monkeypatch, tmp_path):
    class Claim:
        def __enter__(self):
            return {"index": 0, "worktree": str(tmp_path)}

        def __exit__(self, *exc):
            return False

    class FL:
        LaneRefused = RuntimeError

        @staticmethod
        def should_yield(_code):
            return False

        @staticmethod
        def run_lane(*_a, **_k):
            return Claim()

    monkeypatch.setattr(vw_lane, "_kit", lambda: (None, FL))
    monkeypatch.setattr(vw_lane, "ROOT", tmp_path)
    monkeypatch.setattr(vw_lane, "_job", lambda *_a, **_k: dict(LIMIT_LINE))
    monkeypatch.setattr(vw_lane, "keep_and_prune", lambda *_a, **_k: {"ref": None})
    vw_lane.run("review", "other-note", "p")
    assert vw_lane.read_review_state(tmp_path) is None
    vw_lane.run("review", vw_lane.REVIEW_NOTE, "p")
    assert "retry_after" in vw_lane.read_review_state(tmp_path)
