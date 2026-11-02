# ROADMAP archive - closed items, verbatim, with proving path

## Closed 2026-10-31 (session 3)

- [x] VW-APP-BUS: typed versioned message bus and engine contracts. Accept: a
  malformed message is rejected with a logged reason and no subscriber sees it;
  also SEC-E13's runtime half (IPC from a non-app:// frame refused, payloads
  schema-checked). after: none (SCAFFOLD done; unblocked).
  Done 2026-10-31: `app/src/main/bus/` (in-repo validator, contracts
  `e1.build_advice.v1`, `e2.skill_profile.v1`, `e3.macro.v1`,
  `ui.layout.v1`, bus, IPC bridge `vw:bus:publish`); unknown type / version
  and schema failures rejected with a logged reason before any subscriber;
  subscriber exceptions isolated; renderer refused from a non-app:// frame,
  over 64 KiB, or for engine types. `npm test` 52/52 (bus 18).
  Proof: app/test/bus.test.js, docs/companion-app.md section 7,
  docs/research/security.md SEC-E13.
- [x] VW-APP-DB: local SQLite store with versioned migrations. Accept: migrate
  up from empty and from the previous version idempotently, backup first.
  after: none (SCAFFOLD done; unblocked).
  Done 2026-10-31: `app/src/main/store/` on Node's built-in `node:sqlite`
  (decision D-DB: zero runtime deps; read back loading without flags in
  Node 24.15 and in Electron 45.2.1's main process). DB in
  `<userData>/data/`, `schema_version` table, SHA-256-pinned ordered
  migrations, `VACUUM INTO` backup before any migration (newest 5 kept),
  all-or-nothing apply, DB_TOO_NEW / NOT_VW_DB / MIGRATION_CHANGED refusals;
  opened from `main.js`. `npm test` 51/51 (store 17). Proof:
  app/test/store.test.js, docs/companion-app.md section 8.

- [x] VW-APP-SCAFFOLD: Electron scaffold + installer + GitHub-release updater
  (charter D-1). Accept: a per-user NSIS install from a GitHub release
  self-updates to a newer one with SHA-256 verify, self-test and rollback,
  never mid-match. after: VW-APP-SEC.
  Done 2026-10-31: `app/` (hardened main / sandboxed preload / app://
  renderer on the UX tokens), `app/electron-builder.yml` (per-user NSIS,
  unsigned per SIGN-0, fuses flipped), VW updater per D-1a
  (`app/src/main/updater/`), `npm test` 34/34 incl. SHA-256 mismatch refused,
  rollback on failed self-test, update deferred while in match; local
  `npm run dist` built `dist/VeilWalker-Setup-0.1.0.exe` and the packaged
  `--vw-self-test` passed; CI `.github/workflows/app.yml` (ubuntu + windows)
  and draft-release job `app-release.yml`. The live two-release update run is
  VW-APP-UPDATE-E2E. Proof: app/test/updater.test.js,
  app/test/security.test.js, docs/companion-app.md section 6.

## Closed 2026-10-31 (session 2)

- [x] VW-CVAR-CHECK: use the public API cvar list (VW-APP-GAME) to flag any
  cheat or development-only cvar in `config/autoexec.cfg`. Accept: a check in
  tools with a test; a flagged cvar is removed per the safety floor.
  after: none.
  DONE 2026-10-31: `tools/vw_cvar_check.py` (API list FCVAR_CHEAT bit 14,
  FCVAR_DEVELOPMENTONLY bit 1, plus `cvarlist` dumps); repo and game
  autoexec: 0 cheat, 0 devonly, 3 ok, 5 unknown (engine cvars, follow-up
  VW-CVAR-DUMP); nothing removed.
  Proof: tests/test_cvar_check.py, docs/optimization.md "Cvar flag check".
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
- [x] VW-RUNCAP: two operator asks, both kit-owned (FLEET-COMMON 10; VW never
  edits or resets the kit ledger locally). (a) 500 runs / 24 h, REQUEST to
  MAIN 2026-10-29 0611. (b) Operator order 2026-10-29: when the cap is hit,
  usage percent remains and the session was not told to wrap up / /done,
  record the cap-hit in the usage ledger, reset the rolling count and
  continue; REQUEST to MAIN 2026-10-29 0614 (asks one ruling on a + b).
  Until then VW runs at the kit's 120 and stops at the cap. Accept: MAIN
  answers; adopt the kit version that carries it. after: MAIN.
  DONE 2026-11-01 (MAIN ORDER 2026-11-01 2005 item 1). Kit v26 shipped it: (a)
  granted through the machine config; (b) automatic reset declined by MAIN's
  ruling, `budget reset` is the operator's word. Read back on kit v28:
  `fleet_lanes.py status` "- VW runs cap: 500", `fleet_headless.py budget show
  --code VW` cap 500. Proof: ops/fleet_kit/fleet_lanes.py, v26 ORDER section 7.
- [x] VW-KIT-BOARDID: kit v25 fleet_board.py line 59 (_LINE, ID group
  `{0,15}`) silently drops checklist rows whose ID is over 16 chars (seen:
  VW-AUTOEXEC-VERIFY). FIX note sent to MAIN 2026-10-29 0612. Meanwhile render
  the board via `--progress` JSON (no ID limit). Accept: adopt the kit version
  that raises the limit or fails loudly; a stdin render shows an 18-char ID.
  after: MAIN.
  DONE 2026-11-01 (MAIN ORDER 2026-11-01 2005 item 1). Kit v26 raised it. Read
  back on kit v28: fleet_board.ID_MAX 48; parse_checklist on stdin-shaped text
  keeps the 18-char VW-AUTOEXEC-VERIFY row. Parsed, not rendered: a headless run
  never renders the board (FLEET-COMMON 18). Proof: ops/fleet_kit/fleet_board.py.
- [x] VW-LANE-ORDER-LIVE: MAIN FIX 2026-11-01 0825 items 2 and 3 are unit-tested
  only; no order job has run the close-on-evidence path live. Item 4: MAIN's
  acceptance reads back only on the next ORDER (kit v28). Accept: one real order
  job closes on a kept commit, its WORK row stays pending until a session merges
  and answers, and the result is recorded here.
  Lane read-back 2026-11-01 (kit v28 ORDER, kind order): the lane read and wrote
  its worktree, ran the suite gate and committed. Still open for a session: the
  job's close and its WORK row. Allowlist gaps seen: `python -c` asks for approval
  (conformance() could not run in the lane), and the main checkout's inbox and
  outbox are unreadable from the lane, so the session checks provenance.
  DONE 2026-11-01. Read live on the kit v28 ORDER, the older of the two notes the
  one hand tick found (the 2005 ORDER stayed queued and a session worked it): job
  rc 0 in 141.1 s, kept refs/fleet-lanes/lane-0-vw-build-1793585169 (b2f1994),
  worktree pruned, inbox_answers.jsonl state merge, WORK row pending until
  close-order after a session reviewed and merged it. The blocked branch of the
  close stays unit-tested only. Gaps: VW-LANE-ORDER-GAPS. Proof: b2f1994,
  tools/vw_loop.py, tests/test_loop.py.
