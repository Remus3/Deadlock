"""dl_lane: spawn options follow FLEET-COMMON 10 (sonnet unless code, low effort for inbox)."""
import pytest

import dl_lane


def test_build_without_code_is_sonnet():
    p = dl_lane.plan("build", False, "build")
    assert p["model"] == "sonnet" and p["effort"] is None and p["governor"] == "queued"


def test_code_job_uses_the_default_model():
    assert dl_lane.plan("build", True, "build")["model"] is None


def test_inbox_is_low_effort():
    assert dl_lane.plan("review", False, "inbox")["effort"] == "low"


def test_bad_lane_or_kind_refuses():
    with pytest.raises(ValueError):
        dl_lane.plan("other", False, "build")
    with pytest.raises(ValueError):
        dl_lane.plan("build", False, "chat")


def test_cap_within_kit_limit():
    import fleet_lanes
    assert 1 <= dl_lane.CAP <= fleet_lanes.LANE_CAP_MAX
