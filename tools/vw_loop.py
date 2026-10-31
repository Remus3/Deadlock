"""VW lane loop - the scheduled tick (VW-LOOP-ARM).

    python tools/vw_loop.py tick                 one tick (the scheduled task runs this)
    python tools/vw_loop.py queue <lane> --note <label> --prompt-file <file>
                                  [--writes-code] [--kind ...] [--effort ...]
    python tools/vw_loop.py job <job file>       (internal) run one claimed job
    python tools/vw_loop.py register             create / update the scheduled task
    python tools/vw_loop.py status               queue, lanes and the task read-back

Every tick (Windows Task Scheduler, every TICK_MIN minutes, hidden pythonw, a
second instance ignored while one runs):
  a. HALT (ops/loop/control/HALT) -> nothing runs, progress says halted.
  b. Inbox (FLEET-COMMON 14, kit fleet_inbox): scan moon_sync_inbox/ by mtime.
     SKIP / ACK -> mark_seen (a ledger line, no note). WORK (ORDER / FIX /
     RULING) -> enqueue_work, mark_seen, and one `order` lane job is queued for
     it. TRIAGE -> ONE kit spawn (sonnet, effort low, triage_spawn_kwargs);
     NOREPLY / ACK verdicts are recorded only; an ANSWER verdict is recorded
     in ops/loop/control/inbox_answers.jsonl for the session to send in one
     batched note (VW never answers from the tick: CLAUDE.md "Lanes and inbox").
  c. Lane jobs: the oldest queued job file in ops/loop/control/lane_jobs/
     whose lane is free is claimed by an atomic rename to .running and handed
     to a detached `job` worker, so the tick returns at once and the two lanes
     (build, review) run in parallel. The worker runs tools/vw_lane.py run()
     - kit fleet_lanes.run_lane + fleet_headless.spawn(governor="queued"),
     should_yield checked before the job, progress/lane-<i>.json in the main
     checkout, and the lane worktree kept-and-pruned on exit. A skipped job
     (lane refused, should_yield) goes back to the queue for the next tick.
  d. Stale .running files (worker pid dead) go back to the queue once, then
     fail.
Nothing here starts claude except through the kit; route, kill switch, budget
and usage line are the kit's. The tick never merges lane commits into main:
they are kept under refs/fleet-lanes/ and merged by a session. Paths are
resolved at run time; the task XML is written to the gitignored ops/runtime/.
"""

import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops" / "fleet_kit"))
sys.path.insert(0, str(ROOT / "tools"))

import vw_lane  # noqa: E402

CODE = "VW"
TASK_NAME = "VW-LaneLoop"
TICK_MIN = 15
CONTROL_REL = Path("ops/loop/control")
JOBS_REL = CONTROL_REL / "lane_jobs"
ANSWERS_REL = CONTROL_REL / "inbox_answers.jsonl"
HALT_REL = CONTROL_REL / "HALT"
INBOX_REL = Path("moon_sync_inbox")
TASK_XML_REL = Path("ops/runtime/vw_loop_task.xml")
MAX_REQUEUE = 1
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_DETACHED = getattr(subprocess, "DETACHED_PROCESS", 0)
_NEW_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def _now():
    return time.time()


def _stamp(epoch=None):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(_now() if epoch is None else epoch))


def _write_json(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=1), encoding="ascii", newline="\n")
    os.replace(tmp, path)


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="ascii"))
    except (OSError, ValueError):
        return None


def _append(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="ascii", newline="\n") as fh:
        fh.write(json.dumps(doc) + "\n")


# ---------------------------------------------------------------- job queue

def make_job(lane, note, prompt, writes_code=False, kind="build", effort=None, key=None):
    """A job document (validated by vw_lane.plan; pure)."""
    vw_lane.plan(lane, writes_code, kind, effort)
    if not note or not prompt:
        raise ValueError("a job needs a note label and a prompt")
    return {"lane": lane, "note": str(note)[:80], "prompt": prompt,
            "writes_code": bool(writes_code), "kind": kind, "effort": effort,
            "key": key, "requeued": 0, "queued": _stamp()}


def queue_job(root, job, name=None):
    """Write a queued job file; returns its path. A name already queued,
    running or done (same key) is not doubled: returns None."""
    d = Path(root) / JOBS_REL
    d.mkdir(parents=True, exist_ok=True)
    stem = name or "%d-%s" % (time.time_ns(), job["lane"])
    for suffix in (".json", ".running", ".done", ".failed"):
        if (d / (stem + suffix)).exists():
            return None
    path = d / (stem + ".json")
    _write_json(path, job)
    return path


def queued(root):
    """Queued job files, oldest first (by name: a time_ns stem, or a key stem
    whose mtime orders it)."""
    d = Path(root) / JOBS_REL
    if not d.is_dir():
        return []
    return sorted(d.glob("*.json"), key=lambda p: (p.stat().st_mtime, p.name))


def running(root):
    d = Path(root) / JOBS_REL
    return sorted(d.glob("*.running")) if d.is_dir() else []


def claim_job(path):
    """Atomic claim: rename .json -> .running. None if another tick won."""
    target = Path(path).with_suffix(".running")
    if target.exists():
        return None
    try:
        os.rename(path, target)  # fails if the source is gone (another tick won)
    except OSError:
        return None
    return target


def finish_job(path, line, ok):
    """Record the result in the job file and rename it .done / .failed."""
    path = Path(path)
    doc = _read_json(path) or {}
    doc["result"] = {k: line.get(k) for k in ("rc", "error", "cost_usd", "duration_s", "kept")}
    doc["finished"] = _stamp()
    _write_json(path, doc)
    target = path.with_suffix(".done" if ok else ".failed")
    os.replace(path, target)
    return target


def requeue_job(path, reason):
    """A skipped job (lane refused, should_yield) goes back to .json."""
    path = Path(path)
    doc = _read_json(path) or {}
    doc["last_skip"] = str(reason)[:120]
    _write_json(path, doc)
    target = path.with_suffix(".json")
    os.replace(path, target)
    return target


def _pid_alive(pid):
    try:
        import fleet_lanes  # noqa: PLC0415
        return bool(pid) and fleet_lanes.pid_alive(int(pid))
    except (ImportError, ValueError, TypeError):
        return False


def reap_stale(root, alive=_pid_alive):
    """A .running job whose worker pid is dead is re-queued once, then failed."""
    out = []
    for p in running(root):
        doc = _read_json(p) or {}
        pid = doc.get("worker_pid")
        if pid is None:
            # claimed, worker not started yet: older than a tick is stale
            if _now() - p.stat().st_mtime < TICK_MIN * 60:
                continue
        elif alive(pid):
            continue
        if int(doc.get("requeued", 0)) < MAX_REQUEUE:
            doc["requeued"] = int(doc.get("requeued", 0)) + 1
            doc.pop("worker_pid", None)
            _write_json(p, doc)
            out.append(("requeued", requeue_job(p, "worker died")))
        else:
            out.append(("failed", finish_job(p, {"error": "worker died twice"}, False)))
    return out


def busy_lanes(root, lane_state=None):
    """Lane names a live VW job holds: running job files plus the kit's lane rows."""
    names = set()
    for p in running(root):
        doc = _read_json(p) or {}
        if doc.get("lane"):
            names.add(doc["lane"])
    with contextlib.suppress(Exception):
        rows = lane_state() if lane_state else vw_lane.status()["lanes"]
        for row in rows or []:
            if isinstance(row, dict) and row.get("lane") in vw_lane.LANES                     and row.get("state") == "RUNNING":
                names.add(row["lane"])
    return names


def pick_jobs(root, busy):
    """Queued jobs to start now: the oldest per free lane (pure over files)."""
    picks, taken = [], set(busy)
    for p in queued(root):
        doc = _read_json(p)
        if not doc or doc.get("lane") not in vw_lane.LANES or doc["lane"] in taken:
            continue
        taken.add(doc["lane"])
        picks.append(p)
    return picks


# ---------------------------------------------------------------- inbox

def order_prompt(note_path, decision):
    return (
        "VW lane job (kind order). You run headless in a VW lane worktree. Read "
        "CLAUDE.md first; the game safety floor and FLEET-COMMON rules bind you. "
        "Work the %s note from %s at `%s` (read it in full, its section headings "
        "first). Do the work it orders in THIS worktree, run the gates CLAUDE.md "
        "names, commit through ops/fleet_kit/fleet_gitlock.py with no trailer, "
        "never push, never send a note. If the order needs the operator (a "
        "physical act, password or OAuth) or a ruling, write what is needed to "
        "ROADMAP.md and commit that instead. Write progress per FLEET-COMMON 12."
        % (decision.cls, decision.sender, note_path))


def inbox_pass(root, inbox=None, spawn_triage=None, fi=None):
    """Step b. Returns counts {"skip", "ack", "work", "triage", "answer"}."""
    if fi is None:
        import fleet_inbox as fi  # noqa: PLC0415
    inbox = Path(inbox) if inbox else Path(root) / INBOX_REL
    counts = dict.fromkeys(("skip", "ack", "work", "triage", "answer"), 0)
    for path, d in fi.scan(root, inbox, CODE):
        if d.action in (fi.SKIP, fi.ACK):
            fi.mark_seen(root, path, d)
            counts["skip" if d.action == fi.SKIP else "ack"] += 1
        elif d.action == fi.WORK:
            row = fi.enqueue_work(root, path, d)
            fi.mark_seen(root, path, d)
            sha = (row or {}).get("sha256") or ""
            job = make_job("build", "order " + path.name[:60], order_prompt(path, d),
                           writes_code=True, kind="order", key={"note": path.name, "sha256": sha})
            queue_job(root, job, name="order-%s" % (sha[:16] or str(time.time_ns())))
            counts["work"] += 1
        else:
            counts["triage"] += 1
            verdict, answer = _triage(root, path, d, fi, spawn_triage)
            fi.mark_seen(root, path, d, verdict=verdict)
            if verdict == "ANSWER":
                counts["answer"] += 1
                _append(Path(root) / ANSWERS_REL, {
                    "ts": _stamp(), "note": path.name, "to": d.sender, "cls": d.cls,
                    "hop": d.hop, "answer": answer[:4000], "sent": False})
    return counts


def _triage(root, path, d, fi, spawn_triage):
    try:
        body = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "ACK", ""
    prompt = fi.triage_prompt(path.name, body)
    if spawn_triage is None:
        import fleet_headless as fh  # noqa: PLC0415

        def spawn_triage(prompt, note):
            return fh.spawn(root, CODE, prompt, note=note, governor="queued", kind="triage",
                            halt_file=str(Path(root) / HALT_REL),
                            **fi.triage_spawn_kwargs(True))
    try:
        line = spawn_triage(prompt, "triage " + path.name[:60])
    except Exception as exc:  # Refused, budget, route: fail quiet, note stays unseen
        raise _TriageRefused(str(exc)) from exc
    return fi.parse_verdict(line.get("result") or "")


class _TriageRefused(RuntimeError):
    pass


# ---------------------------------------------------------------- tick

def _pythonw():
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return str(w if w.is_file() else exe)


def launch_worker(root, job_path, popen=subprocess.Popen):
    """Start the detached hidden `job` worker for a claimed job; record its pid."""
    p = popen([_pythonw(), str(Path(root) / "tools" / "vw_loop.py"), "job", str(job_path)],
              cwd=str(root), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL, close_fds=True,
              creationflags=_NO_WINDOW | _DETACHED | _NEW_GROUP)
    doc = _read_json(job_path) or {}
    doc["worker_pid"] = p.pid
    doc["started"] = _stamp()
    _write_json(job_path, doc)
    return p.pid


def _progress(root, pct, step, status, checklist):
    with contextlib.suppress(Exception):
        import fleet_headless as fh  # noqa: PLC0415
        fh.write_progress(root, "vw-loop", pct, step, 0 if status != "running" else 60,
                          status, checklist=checklist)


def _checklist(root):
    rows = []
    for p in running(root) + queued(root):
        doc = _read_json(p) or {}
        rows.append({"id": doc.get("note", p.stem)[:40], "task": "%s lane: %s" % (
            doc.get("lane"), doc.get("note")), "state": "running" if p.suffix == ".running"
            else "queued", "eta_s": vw_lane.TIMEOUT_S})
    return rows


def tick(root=ROOT, inbox_pass_fn=inbox_pass, launch=launch_worker, lane_state=None):
    """One tick (a-d). Returns a summary dict (also the progress step)."""
    root = Path(root)
    if (root / HALT_REL).exists():
        _progress(root, 100, "halted (HALT file)", "done", _checklist(root))
        return {"halted": True}
    _progress(root, 10, "tick: inbox", "running", _checklist(root))
    summary = {"halted": False, "inbox": None, "started": [], "reaped": []}
    try:
        summary["inbox"] = inbox_pass_fn(root)
    except _TriageRefused as exc:
        summary["inbox"] = {"refused": str(exc)[:120]}
    summary["reaped"] = [(k, Path(p).name) for k, p in reap_stale(root)]
    for p in pick_jobs(root, busy_lanes(root, lane_state)):
        c = claim_job(p)
        if c is None:
            continue
        try:
            launch(root, c)
            summary["started"].append(c.name)
        except OSError as exc:
            requeue_job(c, "launch failed: %s" % exc)
    step = "tick ok: inbox %s, started %d" % (summary["inbox"], len(summary["started"]))
    _progress(root, 100, step[:120], "done", _checklist(root))
    return summary


def run_job(job_path, run=None):
    """The detached worker: run one claimed job through vw_lane.run()."""
    run = run or vw_lane.run
    job_path = Path(job_path)
    doc = _read_json(job_path)
    if not doc:
        return 1
    line = run(doc["lane"], doc["note"], doc["prompt"], doc.get("writes_code", False),
               doc.get("kind", "build"), doc.get("effort"))
    if line.get("retry"):
        requeue_job(job_path, line.get("error"))
        return 0
    ok = line.get("rc") == 0 and not line.get("error")
    finish_job(job_path, line, ok)
    key = doc.get("key")
    if ok and doc.get("kind") == "order" and key:
        with contextlib.suppress(Exception):
            import fleet_inbox  # noqa: PLC0415
            fleet_inbox.mark_work_done(ROOT, key, "lane job done")
    return 0 if ok else 1


# ---------------------------------------------------------------- schedule

def task_xml(python_w, root, tick_min=TICK_MIN, start=None):
    """The Task Scheduler definition (pure; paths passed in at run time)."""
    start = start or time.strftime("%Y-%m-%dT%H:%M:00", time.localtime(_now() + 120))

    def esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;"))
    script = Path(root) / "tools" / "vw_loop.py"
    return (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
        '  <RegistrationInfo>\n'
        '    <Description>VW lane loop tick (inbox triage, lane jobs, worktree prune) '
        'every %d minutes.</Description>\n'
        '  </RegistrationInfo>\n'
        '  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType>'
        '<RunLevel>LeastPrivilege</RunLevel></Principal></Principals>\n'
        '  <Settings>\n'
        '    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n'
        '    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n'
        '    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>\n'
        '    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n'
        '    <StartWhenAvailable>true</StartWhenAvailable>\n'
        '    <Hidden>true</Hidden>\n'
        '  </Settings>\n'
        '  <Triggers><TimeTrigger><StartBoundary>%s</StartBoundary>'
        '<Repetition><Interval>PT%dM</Interval></Repetition></TimeTrigger></Triggers>\n'
        '  <Actions Context="Author"><Exec>\n'
        '    <Command>%s</Command>\n'
        '    <Arguments>"%s" tick</Arguments>\n'
        '    <WorkingDirectory>%s</WorkingDirectory>\n'
        '  </Exec></Actions>\n'
        '</Task>\n' % (tick_min, start, tick_min, esc(python_w), esc(script), esc(root)))


def _schtasks(*args):
    return subprocess.run(["schtasks", *args], capture_output=True, text=True,
                          timeout=60, creationflags=_NO_WINDOW)


def read_back(query=None):
    """The registered task's command, arguments, interval and state, or None."""
    query = query or _schtasks
    r = query("/query", "/tn", TASK_NAME, "/xml")
    if r.returncode != 0:
        return None
    import re  # noqa: PLC0415
    out = {}
    for tag in ("Command", "Arguments", "WorkingDirectory", "Interval",
                "MultipleInstancesPolicy", "Hidden", "Enabled"):
        m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), r.stdout, re.S)
        out[tag] = m.group(1).strip() if m else None
    s = query("/query", "/tn", TASK_NAME, "/fo", "LIST")
    for line in (s.stdout or "").splitlines():
        if line.startswith(("Status:", "Next Run Time:")):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def register(root=ROOT):
    xml = task_xml(_pythonw(), Path(root).resolve())
    path = Path(root) / TASK_XML_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(xml, encoding="utf-16")
    r = _schtasks("/create", "/tn", TASK_NAME, "/xml", str(path), "/f")
    if r.returncode != 0:
        return {"ok": False, "error": (r.stderr or r.stdout).strip()[:200]}
    back = read_back() or {}
    want_args = '"%s" tick' % (Path(root).resolve() / "tools" / "vw_loop.py")
    ok = back.get("Command") == _pythonw() and back.get("Arguments") == want_args \
        and back.get("Interval") == "PT%dM" % TICK_MIN
    return {"ok": ok, "read_back": back}


def status_doc(root=ROOT):
    d = Path(root) / JOBS_REL
    counts = {}
    if d.is_dir():
        for p in d.iterdir():
            counts[p.suffix] = counts.get(p.suffix, 0) + 1
    return {"task": read_back(), "jobs": counts, "halt": (Path(root) / HALT_REL).exists()}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vw_loop")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tick")
    q = sub.add_parser("queue")
    q.add_argument("lane", choices=vw_lane.LANES)
    q.add_argument("--note", required=True)
    q.add_argument("--prompt-file", required=True)
    q.add_argument("--writes-code", action="store_true")
    q.add_argument("--kind", default="build", choices=vw_lane.KINDS)
    q.add_argument("--effort", default=None, choices=vw_lane.EFFORTS)
    j = sub.add_parser("job")
    j.add_argument("path")
    sub.add_parser("register")
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "tick":
        print(json.dumps(tick(), default=str))
        return 0
    if a.cmd == "queue":
        prompt = Path(a.prompt_file).read_text(encoding="utf-8")
        p = queue_job(ROOT, make_job(a.lane, a.note, prompt, a.writes_code, a.kind, a.effort))
        print(str(p))
        return 0 if p else 1
    if a.cmd == "job":
        return run_job(a.path)
    doc = register() if a.cmd == "register" else status_doc()
    print(json.dumps(doc, indent=1, default=str))
    return 0 if doc.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
