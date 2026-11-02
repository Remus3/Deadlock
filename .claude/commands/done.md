---
description: End-of-session ritual - gate, commit, push (tiered), roadmap, inbox, and the VW-NEXT-SESSION.txt hand-off rewritten with every unworked item carried forward. Chat output is one line.
argument-hint: [optional one-line session topic]
---

# /done - end-of-session ritual

Run EVERY section, in order, quietly. Session topic, if given: $ARGUMENTS

**/done RUNS UNPROMPTED** once no session-checklist task remains (FLEET-COMMON
items 5 and 13 c).

**THE ONLY CHAT OUTPUT OF /done IS ONE LINE:**

```
Done ritual complete, safe to clear
```

or, if a section stopped the ritual, one line naming the failure that stopped
it. No banner, no gate table, no checklist, no review, no hand-off text.

**THE MAIN SESSION DISPATCHES THE WHOLE RITUAL TO ONE SUB-AGENT** (kit v10
subagent-first hook). Its prompt carries this file's sections in order, the
session topic, the counter `n` and the checklist tasks the session printed.
The sub-agent ends with exactly the one line above (or the failure line); the
main session relays only that line.

## Pre-flight - checklist and inbox

- Every task on the printed `Session <n> checklist` is DONE or CARRIED into
  `VW-NEXT-SESSION.txt` (section 6). A task that is neither stops the ritual.
- Inbox: list `moon_sync_inbox/` by mtime; `fleet_inbox.classify(name, "VW")`
  each new note. ACK / INFORMATION / TERMINAL / ANSWER: record, never answer.
  ORDER / FIX / RULING: done this session or carried as a hand-off item.

## 1. Gate

```
python tools/vw_privacy.py scan
python ops/fleet_kit/fleet_suite_gate.py run --owner <id> -- <absolute python> -m pytest -q
```

`<id>` is the caller's claims owner id (`<session_id>.<agent_id>`). A gate
timeout fails closed. RED this session introduced: fix and re-run, never commit
over it.

## 2. Commit

- Stage file by file; never `git add -A`. Nothing from `ops/runtime/`, no raw
  game backup (only `config/baseline/` copies made by `vw_privacy.py scrub`).
- `python ops/fleet_kit/fleet_gitlock.py run --owner <id> -- git commit -F <file>`
  (message file in the session scratchpad; ASCII; no trailer of any kind).
- Never `--amend`, never `--no-verify`.

## 3. Push - batched, tiered (CLAUDE.md "Commit and push")

ONE push per session, here:
`python ops/fleet_kit/fleet_gitlock.py run --owner <id> -- git push origin main`.
The pre-push hook runs the identity gate and the privacy scan; a push that
printed an error is the failure line. Then `gh run list --branch main --limit 3`:
record the run the push triggered as green, red or pending (a docs-only push
fires no `ci` run; that is not a failure). Never force-push.

## 3a. Public presentation trigger (VW-PUBLIC-REVIEW, `docs/public-presentation.md`)

After the push, run `python tools/vw_lane.py review-due`: exit 0 is due, exit 1
is not, and it prints one line. Skipped inside a cooldown (`retry_after` in
`ops/loop/control/public_review_state.json`, written when a review ended rc 1 on
a limit or auth failure): carry that one line into the hand-off. Otherwise due
when the file is missing, the last run failed, `<last_commit>..origin/main` names
a user-facing surface (README.md, LICENSE, NOTICE, SECURITY.md, docs/ outside
research and archives, .github/, a new top-level dir or tools/ entry point), a
tag was added since, or `last_date` is 7 or more days old. Due: start
`python tools/vw_lane.py run review --note public-review --prompt-file <file>`
in the BACKGROUND with the job of `docs/public-presentation.md` section 4;
never wait for it. Not due: do nothing. Names and dates only; read no file
contents for this check.

## 4. ROADMAP.md

Open work only. Add what this session opened; move closed items, verbatim, to
`docs/roadmap-archive.md` with the proving path.

## 5. Game state read-back (only if this session touched the game)

`python tools/vw_paths.py`, `python tools/vw_launch.py check`,
`python tools/vw_video.py check`: record the readings (redacted) in the hand-off.

## 6. Rewrite `VW-NEXT-SESSION.txt` - CARRY FORWARD EVERY ITEM NOT ACTED ON

- Read the CURRENT file first; every item not acted on is carried, verbatim or
  tighter. An item leaves only when done (and the commit or doc says so) or
  retracted (and the file says why).
- Read n from the one column-0 `SESSION: <n>` line; write exactly one
  `SESSION: <n+1>` line, the LAST line of the new file.
- Raw text, ASCII, LF. PUBLIC repo: no path, id, name or email; siblings by
  channel code only. `python tools/vw_privacy.py scan` must stay clean.
- Commit it through fleet_gitlock (section 2) and push it with the batch.

## 7. Board (local only, kit v23)

`python ops/fleet_kit/fleet_board.py render --session <n>` with the last
printed checklist on stdin renders `ops/loop/control/board/board.html`. No
Artifact or ArtifactData call.

## 8. The done marker, then the one line

Only after the commit, the push and the hand-off are READ BACK:

```
python ops/fleet_kit/fleet_done.py mark --session <n> --status done
```

If a section stopped the ritual:
`python ops/fleet_kit/fleet_done.py mark --session <n> --status failed --reason "<step>"`.

Then print exactly `Done ritual complete, safe to clear`, or the one failure
line. Nothing before it, nothing after it.
