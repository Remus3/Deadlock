"""VW headless lane driver - one job in one lane, through the fleet kit only.

    python tools/vw_lane.py run <lane> --note <label> --prompt-file <file>
                                  [--writes-code] [--kind build|inbox|triage|order]
                                  [--effort low|medium|high]
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
inbox / triage, and --effort sets it for any job (low for the public review,
VW-PUBLIC-REVIEW). Progress: progress/lane-<i>.json in the main checkout.
PRUNE ON EXIT (VW-LOOP-ARM): when the job ends, commits the lane made are
kept under refs/fleet-lanes/<lane worktree>-<run id> (the kit's own keep
namespace) and a CLEAN lane worktree is removed and pruned; a dirty one is a
crashed run's work and is left for a session (the kit refuses to reuse it).
PERMISSIONS (MAIN FIX 2026-11-01 0825): a headless child has nobody to approve a
prompt, so a writes_code job gets acceptEdits plus the named gate, gitlock and
git commands of LANE_COMMANDS (plan()["extra"]). No blanket bypass, no push, no
apply tool (a lane never writes a game file). Read-only jobs get nothing extra.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops" / "fleet_kit"))

CODE = "VW"
LANES = ("build", "review")
CAP = None  # v25: None = the live lane_cap_max (kit clamps any number to it)
TIMEOUT_S = 3600
KINDS = ("build", "inbox", "triage", "order")
EFFORTS = ("low", "medium", "high")
LOG_REL = Path("ops") / "runtime" / "lane_logs"  # gitignored; stream log + fail record
LANE_COMMANDS = (  # what a writes_code lane runs unattended; gitlock only for a commit
    "git status", "git diff", "git log", "git show", "git rev-parse", "git add",
    "python -m pytest", "python tools/vw_privacy.py", "python tools/vw_release.py check",
    "npm test", "npm --prefix app test",
)
LANE_OWNER_COMMANDS = (  # a wildcard in the middle: the rule ends " *", not ":*"
    "python ops/fleet_kit/fleet_suite_gate.py run --owner * -- python -m pytest",
    "python ops/fleet_kit/fleet_gitlock.py run --owner * -- git commit",
)


def lane_permissions():
    """The spawn extra of a writes_code job (pure; tested). The tree's project
    settings run PowerShell as well as Bash, so each command is named for both.
    A rule with a wildcard in the middle does not match in the ":*" form (a live
    lane probe was denied, 2026-11-01), so those rules use the " *" form."""
    rules = ["%s:*" % cmd for cmd in LANE_COMMANDS] + ["%s *" % c for c in LANE_OWNER_COMMANDS]
    tools = ["%s(%s)" % (shell, rule) for rule in rules for shell in ("Bash", "PowerShell")]
    return ("--permission-mode", "acceptEdits", "--allowedTools", ",".join(tools))


def _kit():
    import fleet_headless  # noqa: PLC0415
    import fleet_lanes  # noqa: PLC0415
    return fleet_headless, fleet_lanes


def plan(lane, writes_code, kind, effort=None):
    """The spawn options a job gets (pure; tested). effort None = the kind's
    default (low for inbox / triage, else the model default)."""
    if lane not in LANES:
        raise ValueError("lane must be one of %s" % ", ".join(LANES))
    if kind not in KINDS:
        raise ValueError("kind must be one of %s" % ", ".join(KINDS))
    if effort is not None and effort not in EFFORTS:
        raise ValueError("effort must be one of %s" % ", ".join(EFFORTS))
    if effort is None and kind in ("inbox", "triage"):
        effort = "low"
    return {"model": None if writes_code else "sonnet", "effort": effort,
            "writes_code": bool(writes_code), "kind": kind,
            "governor": "queued", "timeout": TIMEOUT_S,
            "extra": lane_permissions() if writes_code else ()}


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


def run(lane, note, prompt, writes_code=False, kind="build", effort=None):
    fh, fl = _kit()
    opts = plan(lane, writes_code, kind, effort)
    if fl.should_yield(CODE):
        return _skipped("should_yield: another tree waits for a slot")
    run_id = "vw-%s-%d" % (lane, int(time.time()))
    try:
        with fl.run_lane(ROOT, CODE, lane, run_id, cap=CAP) as claim:
            try:
                line = _job(fh, claim, lane, note, prompt, opts, run_id)
            finally:
                kept = keep_and_prune(ROOT, claim["worktree"], run_id)
            line = dict(line)
            line["kept"] = kept
            return line
    except fl.LaneRefused as exc:  # lanes_full, lane_held or admission
        return _skipped("lane refused (%s); retry next tick" % exc)


def log_paths(root, run_id):
    """Where a run's stream log and failure record go (gitignored ops/runtime/)."""
    base = Path(root) / LOG_REL
    return base / ("%s.jsonl" % run_id), base / ("%s.fail.json" % run_id)


def write_failure(path, line):
    """Record why a run failed (rc, error, is_error, result text, stderr) so a
    failed lane run is diagnosable after the fact (VW-REVIEW-FAIL). Never raises."""
    keep = ("rc", "error", "is_error", "subtype", "route", "limit", "duration_s",
            "num_turns", "model", "effort", "note")
    rec = {k: line.get(k) for k in keep}
    for k in ("result", "stderr"):
        v = line.get(k)
        rec[k] = v[-8000:] if isinstance(v, str) else v
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(rec, indent=1, default=str) + "\n",
                              encoding="utf-8", newline="\n")
    except OSError:
        pass
    return rec


def _job(fh, claim, lane, note, prompt, opts, run_id="vw-run"):
    task = "lane-%d" % claim["index"]
    log, fail = log_paths(ROOT, run_id)
    fh.write_progress(ROOT, task, 5, "%s: %s" % (lane, note[:60]), opts["timeout"], "running")
    line = fh.spawn(ROOT, CODE, prompt, note=note, writes_code=opts["writes_code"],
                    timeout=opts["timeout"], cwd=claim["worktree"], model=opts["model"],
                    effort=opts["effort"], governor=opts["governor"], kind=opts["kind"],
                    slot_id=task, progress_task=task, log_path=str(log),
                    return_stderr=True, extra=opts["extra"],
                    halt_file=str(ROOT / "ops" / "loop" / "control" / "HALT"))
    ok = line.get("rc") == 0 and not line.get("error") and not line.get("is_error")
    if not ok:
        line = dict(line)
        line["fail_record"] = (LOG_REL / fail.name).as_posix()  # repo-relative
        write_failure(fail, line)
    fh.write_progress(ROOT, task, 100, "%s: %s" % (lane, "done" if ok else "failed"), 0,
                      "done" if ok else "failed")
    return line


def _git_run(*args):
    _fh, fl = _kit()
    git = fl.find_git(cwd=ROOT)
    if not git:
        return subprocess.CompletedProcess(args, 1, "", "git not found")
    return fl._git(*args, git=git)


def keep_and_prune(repo, worktree, run_id, run=None):
    """Keep the lane's commits under refs/fleet-lanes/, then remove a clean lane
    worktree and prune its registration. Returns {"ref", "pruned", "reason"}.
    Never cleans a dirty worktree; never raises (a failed prune is retried by
    the kit's ensure_worktree on the next run)."""
    run = run or _git_run
    out = {"ref": None, "pruned": False, "reason": None}
    wt = Path(worktree)
    try:
        if not wt.exists():
            run("-C", str(repo), "worktree", "prune")
            out["reason"] = "no worktree"
            return out
        head = run("-C", str(wt), "rev-parse", "--verify", "HEAD")
        base = run("-C", str(repo), "rev-parse", "--verify", "HEAD")
        if head.returncode == 0 and base.returncode == 0:
            h = head.stdout.strip()
            if h != base.stdout.strip() and run("-C", str(repo), "merge-base", "--is-ancestor",
                                                h, base.stdout.strip()).returncode != 0:
                ref = "refs/fleet-lanes/%s-%s" % (wt.name, run_id)
                if run("-C", str(repo), "update-ref", ref, h).returncode != 0:
                    out["reason"] = "could not keep lane commits; worktree left"
                    return out
                out["ref"] = ref
        st = run("-C", str(wt), "status", "--porcelain")
        if st.returncode != 0 or st.stdout.strip():
            out["reason"] = "dirty worktree left for a session"
            return out
        if run("-C", str(repo), "worktree", "remove", str(wt)).returncode != 0:
            out["reason"] = "worktree remove failed"
            return out
        run("-C", str(repo), "worktree", "prune")
        out["pruned"] = True
    except (OSError, subprocess.SubprocessError) as exc:
        out["reason"] = "prune error: %s" % str(exc)[:80]
    return out


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
    r.add_argument("--kind", default="build", choices=KINDS)
    r.add_argument("--effort", default=None, choices=EFFORTS)
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        print(json.dumps(status(), indent=1, default=str))
        return 0
    prompt = Path(a.prompt_file).read_text(encoding="utf-8")
    line = run(a.lane, a.note, prompt, a.writes_code, a.kind, a.effort)
    print(json.dumps({k: line.get(k) for k in ("rc", "error", "is_error", "cost_usd",
                                                "duration_s", "fail_record")}))
    return 0 if line.get("rc") == 0 and not line.get("error") and not line.get("is_error")         else 1


if __name__ == "__main__":
    sys.exit(main())
