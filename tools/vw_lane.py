"""VW headless lane driver - one job in one lane, through the fleet kit only.

    python tools/vw_lane.py run <lane> --note <label> --prompt-file <file>
                                  [--writes-code] [--kind build|inbox|triage]
    python tools/vw_lane.py status

A run claims a repo lane (kit fleet_lanes.run_lane: lane lock
ops/loop/control/lanes/<i>.lock, its own clean worktree at the kit's
worktree_path - the sidecar root <sidecar>/VW/Worktree/lane-<i> when that
folder exists), then makes ONE kit fleet_headless.spawn call in that worktree,
holding one machine-wide governor slot for the call only (governor="queued").
Kit v25 (LANE-CAP): the lane cap and the governor slot count are not
hard-coded here; both follow the live machine config (fleet_lanes.load_config,
~/.fleet/lanes.json; cap=None = lane_cap_max, default 3). VW's two lane NAMES
(build, review; exclusive) still bound how many VW jobs run at once. Before a
job starts (its cycle boundary) the driver asks fleet_lanes.should_yield(VW)
and, on True, does not start it; an admission refusal is like lanes_full -
retry next tick. Nothing here ever kills or signals a running worker.
Route, kill switch, budget, usage line and status file are the kit's
(FLEET-COMMON 10). Model: sonnet unless the job writes code; effort low for
inbox / triage. Progress: progress/lane-<i>.json in the main checkout.
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops" / "fleet_kit"))

CODE = "VW"
LANES = ("build", "review")
CAP = None  # v25: None = the live lane_cap_max (kit clamps any number to it)
TIMEOUT_S = 3600


def _kit():
    import fleet_headless  # noqa: PLC0415
    import fleet_lanes  # noqa: PLC0415
    return fleet_headless, fleet_lanes


def plan(lane, writes_code, kind):
    """The spawn options a job gets (pure; tested)."""
    if lane not in LANES:
        raise ValueError("lane must be one of %s" % ", ".join(LANES))
    if kind not in ("build", "inbox", "triage"):
        raise ValueError("kind must be build, inbox or triage")
    return {"model": None if writes_code else "sonnet",
            "effort": "low" if kind in ("inbox", "triage") else None,
            "writes_code": bool(writes_code), "kind": kind,
            "governor": "queued", "timeout": TIMEOUT_S}


def cap():
    """The effective per-tree lane cap, read live from the machine config."""
    _fh, fl = _kit()
    return fl.lane_cap(CAP, fl.load_config())


def slots():
    """The governor slots VW may hold (spawn's governor_slot cap=None): the
    live lane_cap_max clamped to the live governor_width."""
    _fh, fl = _kit()
    cfg = fl.load_config()
    return min(fl.lane_cap(CAP, cfg), int(cfg["governor_width"]))


def _skipped(reason):
    """A job that did not start (retry next tick); never a kill."""
    return {"rc": None, "error": reason, "retry": True, "cost_usd": None, "duration_s": 0}


def run(lane, note, prompt, writes_code=False, kind="build"):
    fh, fl = _kit()
    opts = plan(lane, writes_code, kind)
    if fl.should_yield(CODE):
        return _skipped("should_yield: another tree waits for a slot")
    run_id = "vw-%s-%d" % (lane, int(time.time()))
    try:
        with fl.run_lane(ROOT, CODE, lane, run_id, cap=CAP) as claim:
            return _job(fh, claim, lane, note, prompt, opts)
    except fl.LaneRefused as exc:  # lanes_full, lane_held or admission
        return _skipped("lane refused (%s); retry next tick" % exc)


def _job(fh, claim, lane, note, prompt, opts):
    task = "lane-%d" % claim["index"]
    fh.write_progress(ROOT, task, 5, "%s: %s" % (lane, note[:60]), opts["timeout"], "running")
    line = fh.spawn(ROOT, CODE, prompt, note=note, writes_code=opts["writes_code"],
                    timeout=opts["timeout"], cwd=claim["worktree"], model=opts["model"],
                    effort=opts["effort"], governor=opts["governor"], kind=opts["kind"],
                    slot_id=task, progress_task=task,
                    halt_file=str(ROOT / "ops" / "loop" / "control" / "HALT"))
    ok = line.get("rc") == 0 and not line.get("error")
    fh.write_progress(ROOT, task, 100, "%s: %s" % (lane, "done" if ok else "failed"), 0,
                      "done" if ok else "failed")
    return line


def status():
    _fh, fl = _kit()
    return {"code": CODE, "cap": cap(), "slots": slots(),
            "should_yield": fl.should_yield(CODE),
            "lanes": fl.repo_lane_state(ROOT, cap=CAP),
            "worktree_0": str(fl.worktree_path(ROOT, CODE, 0))}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vw_lane")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("lane", choices=LANES)
    r.add_argument("--note", required=True)
    r.add_argument("--prompt-file", required=True)
    r.add_argument("--writes-code", action="store_true")
    r.add_argument("--kind", default="build", choices=("build", "inbox", "triage"))
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        print(json.dumps(status(), indent=1, default=str))
        return 0
    prompt = Path(a.prompt_file).read_text(encoding="utf-8")
    line = run(a.lane, a.note, prompt, a.writes_code, a.kind)
    print(json.dumps({k: line.get(k) for k in ("rc", "error", "cost_usd", "duration_s")}))
    return 0 if line.get("rc") == 0 and not line.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
