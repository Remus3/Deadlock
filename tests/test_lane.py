"""vw_lane: spawn options follow FLEET-COMMON 10 (sonnet unless code, low effort for inbox)."""
import pytest

import vw_lane


def test_build_without_code_is_sonnet():
    p = vw_lane.plan("build", False, "build")
    assert p["model"] == "sonnet" and p["effort"] is None and p["governor"] == "queued"


def test_code_job_uses_the_default_model():
    assert vw_lane.plan("build", True, "build")["model"] is None


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
