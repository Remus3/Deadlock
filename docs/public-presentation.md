# Public presentation review (standing order 2026-10-29)

Status: LIVE. Recurring work item `VW-PUBLIC-REVIEW` in `ROADMAP.md`. The
operator wants what an outsider sees on GitHub kept correct and well presented
without asking for it, and without spending a session's time or context on it
at every commit. This file is the scope, the rules, the trigger and the job.

## 1. Scope - what an outsider sees

- `README.md` (the rendered front page) and the root file list.
- The docs an outsider is pointed at: the README's documentation list,
  `docs/optimization.md`, `docs/measurement.md`, `docs/controls.md`, and the
  companion app's user-facing docs once they exist (install, update, privacy,
  what it never does). Internal records (hand-off, ROADMAP, research notes,
  charters) are out of scope except that the README must not lean on them.
- GitHub About: description, website, topics.
- Releases and tags: hand-written release notes, every tag reachable from
  `main`.
- `LICENSE`, `NOTICE`, `SECURITY.md`: present and consistent with the README.

## 2. Rules

- Nothing repeated. Each fact lives in one place; the README links to the doc
  that owns it instead of restating it.
- Professionally curated and spaced: short sections, one idea per paragraph,
  commands in code blocks, no internal fleet jargon (lane, kit, channel,
  hand-off) outside the one "How this repo is built" section.
- Reading comprehension: a newcomer with no background follows it top to
  bottom - what it is, what it never does, how to use it, where the detail is.
- Every claim is checked against HEAD, not memory: commands and flags, paths,
  links, badges, feature list, screenshots.
- House style shared with the sibling trees (MAIN's GH-HYGIENE order
  2026-10-18): a "How this repo is built" section stays; the licence is stated
  plainly and matches `LICENSE`; no AI or bot attribution anywhere
  (FLEET-COMMON 17); no machine path, account id, name or email (CLAUDE.md
  "Paths and privacy"); visibility is never changed without an operator order.
- Read first, change only what is wrong. A pass with no finding changes nothing
  and only advances the state file.

## 3. Cadence - when it runs

Checked at every `/done` (step 3a of `.claude/commands/done.md`), after the
push, by `python tools/vw_lane.py review-due` (exit 0 due, exit 1 not, one line
either way). A cooldown (below) outranks everything else. Due when any holds:

- (a) the pushed range since the last review touches a user-facing surface:
  `README.md`, `LICENSE`, `NOTICE`, `SECURITY.md`, `docs/` (not `docs/research/`
  or archives), `.github/`, a new tag, or a new top-level directory or a new
  `tools/` entry point (a new feature);
- (b) 7 days or more have passed since the last review;
- (c) the state file is missing (first run), or the last run failed.

Not due: nothing is spawned. The check is a git diff of names and a date compare;
it never reads file contents.

Cooldown: a review run ending rc 1 on a usage limit or an auth failure writes
`retry_after`, 6 hours ahead, to the state file. `/done` skips the review while
that is in the future and says so in one line. Any other failure earns no
cooldown, so the next `/done` retries it. Tests: `tests/test_lane.py`.

State file (gitignored, per host): `ops/loop/control/public_review_state.json`

```
{"last_commit": "<sha reviewed>", "last_date": "YYYY-MM-DD",
 "result": "changed|no-change|failed", "updated": "<ISO time>",
 "retry_after": "<ISO time, only after a limit or auth failure>"}
```

## 4. The job

- Started by `/done` in the background, never awaited:
  `python tools/vw_lane.py run review --note public-review --prompt-file <file>`
  (prompt file in the session scratchpad). Sonnet, effort low, kind build.
  `vw_lane.py` today sets effort low only for inbox / triage; an `--effort`
  option is part of the VW-PUBLIC-REVIEW acceptance.
- Reads only: `README.md`, the in-scope docs of section 1, the name-only diff
  since `last_commit`, `gh repo view --json description,homepageUrl,repositoryTopics,licenseInfo`
  and the latest release. It does not read the whole repo (no `tools/`,
  `tests/`, `ops/` contents beyond what a README claim names).
- May set the description, website and topics with `gh repo edit`, then reads
  them back with `gh repo view --json`. Never visibility, branch protection or
  the social preview (report those to the hand-off).
- File edits: committed in its lane through `fleet_gitlock` with no trailer;
  pushed with the next session's `/done` batch (docs-only tier). Never a push
  of its own.
- Ends by writing the state file (HEAD it reviewed, today, result) in the main
  checkout and its progress file `progress/lane-<i>.json`. A failed run leaves
  `last_commit` unchanged, so the next `/done` retries it.
- A failed run is diagnosable after the fact: `vw_lane.py` keeps the stream
  log `ops/runtime/lane_logs/<run_id>.jsonl` and writes
  `<run_id>.fail.json` (rc, is_error, route, limit, result text, stderr);
  the CLI prints its path as `fail_record`. Both are gitignored.
