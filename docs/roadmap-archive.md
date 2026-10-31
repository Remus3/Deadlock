# ROADMAP archive - closed items, verbatim, with proving path

## Closed 2026-10-31 (session 2)

- [x] VW-LOOP (superseded by VW-LOOP-ARM, done 2026-10-31): arm a lane loop / inbox responder like the other trees (a
  scheduled tick that reads the inbox and runs `tools/vw_lane.py`), once there
  is recurring work. Until then each session reads the inbox at start and /done.
  Proof: superseded; see VW-LOOP-ARM (36362e5).
- [x] VW-DEPENDABOT: PR #1 (github-actions group, 3 bumps) opened on the first
  push, CI green on it. Never merge a bot PR as-is (operator-only authors):
  apply the same SHA bumps in an operator commit, push at /done, close #1.
  2026-10-31: bumps applied locally (setup-python v7.1.0, codeql init/analyze
  v4.39.1). /done: after the push, `gh pr close 1 --comment` naming that commit.
  Proof: 439612b (.github/workflows/ci.yml, codeql.yml); PR #1 closed at /done session 2 after the push.
- [x] VW-APP-GAME: research game data, public APIs, launch options, ports and
  outputs. Accept: `docs/research/game-data.md` lists each source with class
  (charter 3, 1-4), rate limits, fields, and a ruling ref for any port.
  DONE 2026-10-31: `docs/research/game-data.md` (classes 1-4, limits,
  fields; rulings G-1 no spectating own match, G-2 no lobby control, G-3
  no upload).
  Proof: fb0d231, docs/research/game-data.md.
- [x] VW-APP-HERO: research heroes, items, upgrades, abilities, archetypes,
  counters and their interactions. Accept: a versioned local dataset plus
  fixture tests that pin at least 10 cross-interactions per patch.
  DONE 2026-10-31: `tools/vw_gamedata.py`, `tools/vw_combat.py`, 12 pinned
  interactions at patch 6836 (`tests/fixtures/gamedata/`); D-HERO-1: full
  dataset only in gitignored ops/runtime/gamedata/, one fixture per patch
  tracked (`docs/research/hero-data.md`).
  Proof: 66762ba, docs/research/hero-data.md, tests/test_combat.py, tests/test_gamedata.py.
- [x] VW-APP-WORKSHOP: find whether Deadlock has an official Steam Workshop.
  Accept: a recorded yes / no with sources and a scoped ruling (charter S-6).
  DONE 2026-10-31: NO official Workshop; no mod feature (`docs/research/workshop.md`).
  Proof: c7d21f2, docs/research/workshop.md.
- [x] VW-APP-UX: research legibility, typography, color, theme, focus and
  controller navigation over a live game. Accept: `docs/research/ux.md` with a
  token set (contrast measured) and overlay / companion wireframes. Done
  2026-10-31: `docs/research/ux.md`, `config/app/tokens.json` (46 pairs
  measured by `tools/vw_contrast.py`, `tests/test_ux_tokens.py`),
  `docs/research/wireframes/` (overlay, companion).
  Proof: 2dbacd1, docs/research/ux.md, tests/test_ux_tokens.py.
- [x] VW-APP-SEC: security and architecture audit plan (Electron hardening,
  update signing, supply chain, privacy). Accept: a checklist with each item
  pass / fail / owner epic, and a code-signing decision. Done 2026-10-31:
  `docs/research/security.md` (41 items; signing SIGN-0, unsigned 0.x with
  SHA-256 verify). VW-APP-SCAFFOLD may start.
  Proof: 61303aa, docs/research/security.md.
- [x] VW-APP-LIFT: assess sibling (RC, EW, RSC, CS, MAIN) and outside designs
  for reuse. Accept: a lift table (feature, source code, reuse / adapt / skip,
  why). Done 2026-10-31: `docs/research/lift.md` (21 sibling rows, 7 outside
  rows, receiving epic per row; GPL-sourced rows are adapt-only).
  Proof: 2652060, docs/research/lift.md.
- [x] VW-LOOP-ARM: arm the lane loop (supersedes VW-LOOP's "once there is
  recurring work"). Accept: a scheduled tick runs `tools/vw_lane.py`, reads the
  inbox, writes `progress/lane-<i>.json`, prunes its worktree. after: none.
  DONE 2026-10-31: `tools/vw_loop.py` (tick / queue / job / register /
  status), task VW-LaneLoop every 15 min, hidden, IgnoreNew; read back
  Command pythonw, Arguments `"<tree>/tools/vw_loop.py" tick`, Interval
  PT15M, Status Ready; a manual run ended Last Result 0 with
  progress/vw-loop.json done. Lane worktrees are kept-and-pruned on exit
  (`vw_lane.keep_and_prune`); lane commits wait under refs/fleet-lanes/ for a
  session to merge; triage ANSWERs wait in inbox_answers.jsonl for a session
  to send. Tests: `tests/test_loop.py`.
  Proof: 36362e5, tools/vw_loop.py, tests/test_loop.py.
