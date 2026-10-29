"""Release versioning guard (operator order 2026-10-29, docs/release.md).

A proposed release version must be exactly one patch or one minor step from
the latest released tag: 0.2.3 -> 0.2.4 or 0.3.0, never 0.4.99. No time gate.
"""
import subprocess

import pytest

import vw_release


@pytest.mark.parametrize("latest,proposed", [
    ("0.2.3", "0.2.4"),
    ("0.2.3", "0.3.0"),
    ("v0.2.3", "v0.2.4"),
    (None, "0.1.0"),
    (None, "0.0.1"),
])
def test_one_step_is_accepted(latest, proposed):
    assert vw_release.check(latest, proposed) == []


@pytest.mark.parametrize("latest,proposed", [
    ("0.2.3", "0.4.99"),   # the operator's example: several steps in one run
    ("0.2.3", "0.2.5"),    # two patch steps
    ("0.2.3", "0.3.1"),    # minor step that does not reset patch
    ("0.2.3", "0.4.0"),    # two minor steps
    ("0.2.3", "1.0.0"),    # 1.0 is an operator call, not a batch bump
    ("0.2.3", "0.2.3"),    # no step
    ("0.2.3", "0.2.2"),    # backwards
    ("0.2.3", "0.2"),      # not SemVer
    (None, "0.2.0"),       # first release must be 0.1.0 or 0.0.1
])
def test_more_or_less_than_one_step_is_refused(latest, proposed):
    assert vw_release.check(latest, proposed)


def test_latest_tag_picks_highest_semver(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True,
                       capture_output=True)
    git("init", "-q")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
        "--allow-empty", "-m", "x")
    for t in ("v0.1.0", "v0.10.0", "v0.2.0", "archive-x"):
        git("tag", t)
    assert vw_release.latest_tag(tmp_path) == "0.10.0"


def test_no_time_or_day_gate():
    src = open(vw_release.__file__, encoding="ascii").read()
    for word in ("datetime", "time.time", "days", "weekday"):
        assert word not in src
