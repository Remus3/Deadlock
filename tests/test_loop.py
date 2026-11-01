"""vw_loop (VW-LOOP-ARM) and vw_lane --effort (VW-PUBLIC-REVIEW): the tick reads
the inbox through the kit, queues and claims lane jobs, and the lane worktree
is kept-and-pruned on exit. Every root here is tmp_path; nothing live is
touched and nothing is spawned."""
import json
import os
import subprocess
from pathlib import Path

import pytest

import vw_lane
import vw_loop


# ---------------------------------------------------------------- --effort

def test_effort_low_overrides_a_build_job():
    assert vw_lane.plan("review", False, "build", "low")["effort"] == "low"


def test_effort_default_unchanged():
    assert vw_lane.plan("build", False, "build")["effort"] is None
    assert vw_lane.plan("review", False, "triage")["effort"] == "low"


def test_bad_effort_refuses():
    with pytest.raises(ValueError):
        vw_lane.plan("review", False, "build", "max")


def test_order_kind_allowed():
    assert vw_lane.plan("build", True, "order")["kind"] == "order"


def test_cli_passes_effort(tmp_path, monkeypatch):
    seen = {}

    def fake_run(lane, note, prompt, writes_code, kind, effort):
        seen.update(lane=lane, kind=kind, effort=effort)
        return {"rc": 0}
    monkeypatch.setattr(vw_lane, "run", fake_run)
    pf = tmp_path / "p.txt"
    pf.write_text("job", encoding="ascii")
    rc = vw_lane.main(["run", "review", "--note", "public-review", "--prompt-file", str(pf),
                       "--effort", "low"])
    assert rc == 0 and seen == {"lane": "review", "kind": "build", "effort": "low"}


# ---------------------------------------------------------------- prune

class _Git:
    def __init__(self, head="aaa", base="bbb", ancestor=False, dirty=""):
        self.calls, self.head, self.base = [], head, base
        self.ancestor, self.dirty = ancestor, dirty

    def __call__(self, *args):
        self.calls.append(args)
        out, rc = "", 0
        if args[-2:] == ("--verify", "HEAD"):
            out = self.head if "wt" in args[1] else self.base
        elif "merge-base" in args:
            rc = 0 if self.ancestor else 1
        elif "status" in args:
            out = self.dirty
        return subprocess.CompletedProcess(args, rc, out, "")


def test_prune_keeps_new_commits_then_removes(tmp_path):
    wt = tmp_path / "wt-lane-0"
    wt.mkdir()
    g = _Git()
    out = vw_lane.keep_and_prune(tmp_path, wt, "vw-build-1", run=g)
    assert out["ref"] == "refs/fleet-lanes/wt-lane-0-vw-build-1" and out["pruned"]
    ops = [a[2] if a[0] == "-C" else a[0] for a in g.calls]
    assert ops.index("update-ref") < ops.index("worktree")
    assert ("worktree", "prune") == g.calls[-1][2:]


def test_prune_leaves_a_dirty_worktree(tmp_path):
    wt = tmp_path / "wt-lane-1"
    wt.mkdir()
    g = _Git(head="bbb", dirty=" M x.py\n")
    out = vw_lane.keep_and_prune(tmp_path, wt, "r", run=g)
    assert not out["pruned"] and out["ref"] is None and "dirty" in out["reason"]
    assert not any("remove" in a for a in g.calls)


# ---------------------------------------------------------------- job queue

def _job(root, lane="build", name=None):
    return vw_loop.queue_job(root, vw_loop.make_job(lane, "n", "do it"), name=name)


def test_queue_claim_finish(tmp_path):
    p = _job(tmp_path)
    assert vw_loop.queued(tmp_path) == [p]
    c = vw_loop.claim_job(p)
    assert c.suffix == ".running" and vw_loop.claim_job(p) is None
    done = vw_loop.finish_job(c, {"rc": 0}, True)
    assert done.suffix == ".done" and json.loads(done.read_text())["result"]["rc"] == 0


def test_named_job_not_doubled(tmp_path):
    assert _job(tmp_path, name="order-abc")
    assert _job(tmp_path, name="order-abc") is None


def test_pick_one_job_per_free_lane(tmp_path):
    a = _job(tmp_path, "build")
    _job(tmp_path, "build")
    c = _job(tmp_path, "review")
    assert vw_loop.pick_jobs(tmp_path, set()) == [a, c]
    assert vw_loop.pick_jobs(tmp_path, {"build"}) == [c]


def test_reap_requeues_once_then_fails(tmp_path):
    c = vw_loop.claim_job(_job(tmp_path))
    doc = json.loads(c.read_text())
    doc["worker_pid"] = 999999
    c.write_text(json.dumps(doc))
    assert vw_loop.reap_stale(tmp_path, alive=lambda pid: False)[0][0] == "requeued"
    c = vw_loop.claim_job(vw_loop.queued(tmp_path)[0])
    doc = json.loads(c.read_text())
    doc["worker_pid"] = 999999
    c.write_text(json.dumps(doc))
    assert vw_loop.reap_stale(tmp_path, alive=lambda pid: False)[0][0] == "failed"


def test_run_job_requeues_a_skipped_job(tmp_path):
    c = vw_loop.claim_job(_job(tmp_path))
    rc = vw_loop.run_job(c, run=lambda *a: {"rc": None, "error": "lane refused", "retry": True})
    assert rc == 0 and len(vw_loop.queued(tmp_path)) == 1


# ---------------------------------------------------------------- inbox

class _D:
    def __init__(self, action, cls="INFO", sender="MAIN", hop=1):
        self.action, self.cls, self.sender, self.hop = action, cls, sender, hop


class _FI:
    SKIP, ACK, WORK, TRIAGE = "skip", "ack", "work", "triage"

    def __init__(self, notes):
        self.notes, self.seen, self.work = notes, [], []

    def scan(self, root, inbox, code):
        assert code == "VW"
        return self.notes

    def mark_seen(self, root, path, d, verdict=None):
        self.seen.append((path.name, d.action, verdict))

    def enqueue_work(self, root, path, d):
        self.work.append(path.name)
        return {"note": path.name, "sha256": "f" * 64}

    def triage_prompt(self, name, body):
        return body

    def parse_verdict(self, text):
        return ("ANSWER", "the answer") if "q?" in text else ("ACK", "")

    def triage_spawn_kwargs(self, floors):
        return {}


def test_inbox_pass_routes_each_class(tmp_path):
    notes = []
    for name, action, body in (("a.md", "skip", ""), ("b.md", "ack", ""),
                               ("c.md", "work", ""), ("d.md", "triage", "q?")):
        p = tmp_path / name
        p.write_text(body or "x", encoding="ascii")
        notes.append((p, _D(action, cls="ORDER" if action == "work" else "INFO")))
    fi = _FI(notes)
    spawned = []
    counts = vw_loop.inbox_pass(tmp_path, tmp_path, fi=fi,
                                spawn_triage=lambda pr, note: spawned.append(note) or
                                {"result": pr})
    assert counts == {"pending": 0, "skip": 1, "ack": 1, "work": 1, "triage": 1, "answer": 1}
    assert len(fi.seen) == 4 and fi.work == ["c.md"] and len(spawned) == 1
    job = json.loads((tmp_path / vw_loop.JOBS_REL / ("order-" + "f" * 16 + ".json")).read_text())
    assert job["kind"] == "order" and job["writes_code"] and job["lane"] == "build"
    ans = (tmp_path / vw_loop.ANSWERS_REL).read_text().splitlines()
    assert json.loads(ans[0])["sent"] is False


def test_inbox_pass_requeues_pending_orders_first(tmp_path):
    note = tmp_path / "p.md"
    note.write_text("x", encoding="ascii")
    fi = _FI([])
    fi.pending_work = lambda root: [
        {"note": "p.md", "sha256": "a" * 64, "cls": "ORDER", "sender": "MAIN"},
        {"note": "gone.md", "sha256": "b" * 64, "cls": "FIX", "sender": "MAIN"}]
    counts = vw_loop.inbox_pass(tmp_path, tmp_path, fi=fi)
    assert counts["pending"] == 2
    jobs = vw_loop.queued(tmp_path)
    assert [p.name for p in jobs] == ["order-" + "a" * 16 + ".json"]
    done = jobs[0].with_suffix(".done")
    jobs[0].rename(done)
    vw_loop.inbox_pass(tmp_path, tmp_path, fi=fi)
    assert vw_loop.queued(tmp_path) == []


def _order_job_file(root, sha="d" * 64):
    key = {"note": "o.md", "sha256": sha, "cls": "ORDER", "to": "MAIN", "hop": 1}
    job = vw_loop.make_job("build", "o", "p", writes_code=True, kind="order", key=key)
    return vw_loop.claim_job(vw_loop.queue_job(root, job, name="order-" + sha[:16]))


def _real_inbox(monkeypatch, root, sha="d" * 64):
    """The kit's ledger under tmp, with one queued WORK row for o.md."""
    import fleet_inbox as fi
    note = root / "o.md"
    note.write_text("x", encoding="ascii")
    monkeypatch.setattr(fi, "_sha256", lambda p: sha)
    fi.enqueue_work(root, note, _D("work", cls="ORDER"))
    return fi


def _answers(root):
    path = root / vw_loop.ANSWERS_REL
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines()]


def test_order_prompt_carries_the_note_text(tmp_path):
    note = tmp_path / "o.md"
    note.write_text("# From MAIN - ORDER\nDo the marker-4711 thing.\n", encoding="ascii")
    prompt = vw_loop.order_prompt(note, _D("work", cls="ORDER"))
    assert "marker-4711" in prompt and str(tmp_path) not in prompt
    assert "owner id" in prompt and "deny" in prompt


def test_order_prompt_is_bounded_under_the_kit_argv_limit(tmp_path):
    import fleet_headless
    note = tmp_path / "o.md"
    note.write_text("x" * (vw_loop.ORDER_NOTE_MAX + 500), encoding="ascii")
    prompt = vw_loop.order_prompt(note, _D("work", cls="ORDER"))
    assert "truncated" in prompt and len(prompt) < fleet_headless.ARGV_PROMPT_MAX


def test_order_rc0_without_a_kept_commit_stays_pending_and_retries(tmp_path, monkeypatch):
    fi = _real_inbox(monkeypatch, tmp_path)
    c = _order_job_file(tmp_path)
    rc = vw_loop.run_job(c, run=lambda *a: {"rc": 0, "error": None, "kept": {"ref": None}},
                         root=tmp_path)
    assert rc == 1 and len(fi.pending_work(tmp_path)) == 1
    assert [p.name for p in vw_loop.queued(tmp_path)] == ["order-" + "d" * 16 + ".json"]
    assert _answers(tmp_path) == []


def test_order_is_retried_twice_then_reported_blocked_and_stays_pending(tmp_path, monkeypatch):
    fi = _real_inbox(monkeypatch, tmp_path)
    c = _order_job_file(tmp_path)
    tries = []

    def fake(*a):
        tries.append(1)
        return {"rc": 0, "error": None, "kept": {"ref": None}}
    while c is not None:
        vw_loop.run_job(c, run=fake, root=tmp_path)
        left = vw_loop.queued(tmp_path)
        c = vw_loop.claim_job(left[0]) if left else None
    assert len(tries) == 1 + vw_loop.MAX_ORDER_RETRIES
    assert list((tmp_path / vw_loop.JOBS_REL).glob("*.failed"))
    assert len(fi.pending_work(tmp_path)) == 1
    owed = _answers(tmp_path)
    assert [a["state"] for a in owed] == ["blocked"] and owed[0]["sent"] is False
    assert "BLOCKED" in owed[0]["answer"] and owed[0]["to"] == "MAIN"


def test_order_with_a_kept_commit_tells_the_session_and_stays_pending(tmp_path, monkeypatch):
    fi = _real_inbox(monkeypatch, tmp_path)
    c = _order_job_file(tmp_path)
    ref = "refs/fleet-lanes/lane-0-r"
    rc = vw_loop.run_job(c, run=lambda *a: {"rc": 0, "error": None, "kept": {"ref": ref}},
                         root=tmp_path)
    assert rc == 0 and list((tmp_path / vw_loop.JOBS_REL).glob("*.done"))
    assert len(fi.pending_work(tmp_path)) == 1
    owed = _answers(tmp_path)
    assert owed[0]["state"] == "merge" and ref in owed[0]["answer"]


def test_order_failed_run_with_is_error_counts_as_failed(tmp_path, monkeypatch):
    _real_inbox(monkeypatch, tmp_path)
    c = _order_job_file(tmp_path)
    line = {"rc": 0, "error": None, "is_error": True, "kept": {"ref": "refs/fleet-lanes/x"}}
    assert vw_loop.run_job(c, run=lambda *a: line, root=tmp_path) == 1
    assert _answers(tmp_path) == []


def test_close_order_needs_the_answer_in_the_outbox(tmp_path, monkeypatch):
    fi = _real_inbox(monkeypatch, tmp_path)
    assert vw_loop.close_order(tmp_path, "o.md", "a.md")["ok"] is False
    assert len(fi.pending_work(tmp_path)) == 1
    (tmp_path / vw_loop.OUTBOX_REL).mkdir()
    (tmp_path / vw_loop.OUTBOX_REL / "a.md").write_text("x", encoding="ascii")
    assert vw_loop.close_order(tmp_path, "o.md", "a.md") == {"ok": True, "closed": 1}
    assert fi.pending_work(tmp_path) == []
    assert vw_loop.close_order(tmp_path, "o.md", "a.md")["ok"] is False


def test_a_build_job_still_closes_on_rc(tmp_path):
    c = vw_loop.claim_job(_job(tmp_path))
    assert vw_loop.run_job(c, run=lambda *a: {"rc": 0, "error": None}, root=tmp_path) == 0
    assert list((tmp_path / vw_loop.JOBS_REL).glob("*.done"))


def test_pick_jobs_orders_first(tmp_path):
    first = _job(tmp_path, "build")
    order = vw_loop.queue_job(tmp_path, vw_loop.make_job("build", "o", "p", kind="order"),
                              name="order-" + "c" * 16)
    os.utime(order, (first.stat().st_mtime + 5, first.stat().st_mtime + 5))
    assert vw_loop.pick_jobs(tmp_path, set()) == [order]


def test_tick_halt_runs_nothing(tmp_path):
    (tmp_path / vw_loop.HALT_REL).parent.mkdir(parents=True)
    (tmp_path / vw_loop.HALT_REL).write_text("")
    called = []
    out = vw_loop.tick(tmp_path, inbox_pass_fn=lambda r: called.append(1),
                       launch=lambda r, p: called.append(2))
    assert out == {"halted": True} and not called


def test_tick_inbox_then_launches_jobs(tmp_path):
    _job(tmp_path, "build")
    _job(tmp_path, "review")
    launched = []
    out = vw_loop.tick(tmp_path, inbox_pass_fn=lambda r: {"ack": 0},
                       launch=lambda r, p: launched.append(p.name), lane_state=lambda: [])
    assert len(out["started"]) == 2 == len(launched)
    assert all(n.endswith(".running") for n in launched)
    prog = json.loads((tmp_path / "ops/loop/control/progress/vw-loop.json").read_text())
    assert prog["status"] == "done"


# ---------------------------------------------------------------- schedule

def test_task_xml_shape():
    root = Path(r"X:\tree")
    xml = vw_loop.task_xml(r"X:\py\pythonw.exe", root, start="2026-01-01T00:00:00")
    assert "<Interval>PT15M</Interval>" in xml and "IgnoreNew" in xml
    assert "<Hidden>true</Hidden>" in xml
    # Expected path built from the same Path type as task_xml uses, so the
    # separator matches the host (backslash on Windows, "/" on the CI runner).
    script = root / "tools" / "vw_loop.py"
    assert '"%s" tick' % script in xml.replace("&quot;", '"')


def test_task_xml_script_path_posix(monkeypatch):
    # Simulates the ubuntu CI host on any box: posix Path joins with "/".
    from pathlib import PurePosixPath
    monkeypatch.setattr(vw_loop, "Path", PurePosixPath)
    xml = vw_loop.task_xml("/usr/bin/python3", PurePosixPath("/srv/tree"),
                           start="2026-01-01T00:00:00")
    assert '"/srv/tree/tools/vw_loop.py" tick' in xml.replace("&quot;", '"')


def test_read_back_parses_query():
    xml = ("<Command>w.exe</Command><Arguments>\"t.py\" tick</Arguments>"
           "<Interval>PT15M</Interval>")

    def q(*args):
        out = xml if "/xml" in args else "Status:   Ready\nNext Run Time:  1:00:00 PM\n"
        return subprocess.CompletedProcess(args, 0, out, "")
    back = vw_loop.read_back(q)
    assert back["Command"] == "w.exe" and back["Interval"] == "PT15M" and back["Status"] == "Ready"


def test_no_absolute_path_in_source():
    src = Path(vw_loop.__file__).read_text(encoding="ascii")
    for bad in ("E:\\", "C:\\Users", "/e/"):
        assert bad not in src
