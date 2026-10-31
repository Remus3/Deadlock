# ROADMAP - open work only

- [ ] VW-CASTING: Casting mode Quick Cast / Alternate cast Press and Hold 0.15
  / Items Instant Cast are menu-only and no file confirms them
  (`cl_citadel_quickcast_ability1-4` and `cl_citadel_items_quickcast_mode`
  read 0, unchanged since 21:37). Left: operator confirms in the menu; one
  toggle with a before/after read learns the enum. (VW-CONTROLS closed
  2026-10-25 23:16: `vw_controls.py check` all empty, docs/controls.md
  "Final state".)
- [ ] VW-AUTOEXEC-VERIFY: autoexec RUNS (inferred 23:01: process command line
  carries `+exec autoexec`, its sensitivity 1.6 landed). Left: one console
  look (F7) for `[VW] autoexec loaded` and any "Unknown command" line.
- [ ] VW-MEASURE: baseline then each change per `docs/measurement.md`; results
  in `docs/measurements/`. Includes DLSS 1.5x vs 1x (DLAA; switch if 1
  percent lows >= 200 fps) and D3D 11 vs Vulkan.
- [ ] VW-PUBLIC-REVIEW (recurring; standing order 2026-10-29,
  `docs/public-presentation.md`): the GitHub outsider view (README, docs
  index, About description / topics, release notes, app user docs) kept
  non-repeated, curated and newcomer-readable. Trigger: `/done` step 3a.
  Accept: `vw_lane.py` takes `--effort low` for this job (landed 2026-10-31,
  `tests/test_loop.py`); one lane run reads
  only the scoped files plus `gh repo view`, commits fixes through
  fleet_gitlock with no push of its own, reads back any About change, and
  writes `ops/loop/control/public_review_state.json`; a second `/done` with
  no user-facing change inside 7 days spawns nothing. Never closes; each pass
  is recorded by the state file.
- [ ] VW-POWER: measure Balanced vs High performance power plan in game
  (machine-level; MAIN's call, file a note with the numbers).

## Companion app (standing order 2026-10-29; charter `docs/companion-app.md`)

Order: research epics first, all parallel; then build in the order below
(`after:` names the dependencies). Every epic is checked against the charter's
safety mapping (section 3) before it closes.

Research epics: all six closed 2026-10-31 (docs/roadmap-archive.md).
Follow-ups from research:
- [ ] VW-APP-CONLOG: check whether the `-condebug` launch option makes the game
  write `console.log` (a game output, charter class 3). Accept: one launch
  with the option, the file path and a redacted sample recorded in
  `docs/research/game-data.md`; launch option edited only while Steam is
  closed. after: operator launch.
- [ ] VW-CVAR-DUMP: the API cvar list covers the client / server dll only,
  so the engine cvars in the autoexec (`con_enable`, `fps_max`, `fps_max_ui`,
  `rate`, `engine_low_latency_sleep_after_client_tick`) read `unknown` in
  `vw_cvar_check.py`. Left: operator, in game, runs `cvarlist` in the console
  and saves the text to the gitignored `ops/runtime/cvarlist.txt` (steps in
  `docs/optimization.md` "Cvar flag check"); then
  `vw_cvar_check.py check --live --dump ops/runtime/cvarlist.txt` and any
  cheat / devonly cvar is removed per the floor. after: operator launch.

Build:
- [ ] VW-APP-SCAFFOLD: Electron scaffold + installer + GitHub-release updater
  (charter D-1). Accept: a per-user NSIS install from a GitHub release
  self-updates to a newer one with SHA-256 verify, self-test and rollback,
  never mid-match. after: VW-APP-SEC.
- [ ] VW-APP-DB: local SQLite store with versioned migrations. Accept: migrate
  up from empty and from the previous version idempotently, backup first.
  after: VW-APP-SCAFFOLD.
- [ ] VW-APP-BUS: typed versioned message bus and engine contracts. Accept: a
  malformed message is rejected with a logged reason and no subscriber sees it.
  after: VW-APP-SCAFFOLD.
- [ ] VW-APP-INGEST: data ingestion services (charter 3 classes only) with
  controlled polling. Accept: each source has a rate, ceiling, backoff and
  cache, and a restart leaves the same DB state. after: VW-APP-GAME, VW-APP-DB.
- [ ] VW-APP-E1: combat math / build engine. Accept: pinned math fixtures per
  hero and item on/off comparisons; `e1.build_advice.v1` from recorded match
  context. after: VW-APP-HERO, VW-APP-BUS.
- [ ] VW-APP-E2: player analysis / skill-profile engine. Accept: from recorded
  matches, tiers per dimension and explained focus items with time frames, no
  generic advice (a test rejects template-only output). after: VW-APP-INGEST,
  VW-APP-BUS.
- [ ] VW-APP-E3: live macro engine. Accept: from recorded match states, goal
  now / next / how / abort_if / alt_route that change with tier and state.
  after: VW-APP-E1, VW-APP-E2.
- [ ] VW-APP-OVERLAY: separate transparent click-through always-on-top window
  (charter S-2). Accept: no focus taken, mouse ignored, shows E3 one-liner;
  test asserts the window flags. after: VW-APP-SCAFFOLD, VW-APP-UX.
- [ ] VW-APP-COMPANION: optional second-screen companion window. Accept:
  player picks the display; shows live E1 / E3 detail; off by default.
  after: VW-APP-OVERLAY.
- [ ] VW-APP-CONTROLLER: Xbox / PS4 / PS5 navigation of the app only (charter
  S-4). Accept: navigates companion / dashboard when focused; ignored while the
  game has focus; nothing emitted. after: VW-APP-COMPANION.
- [ ] VW-APP-COACH: LLM coach on conditioned inputs, stored, then distilled to
  zero-LLM rules tagged by patch. Accept: with the LLM disabled the distilled
  rules answer the recorded set; a patch change flags them for review.
  after: VW-APP-E1, VW-APP-E2, VW-APP-E3.
- [ ] VW-LOOP-SCOPE: loop scope decision 2026-10-31 (session 2): the tick
  does NOT merge lane commits (kept under refs/fleet-lanes/, a session
  merges), triage ANSWERs wait in ops/loop/control/inbox_answers.jsonl for a
  session to send, and 2 lanes run at once (build, review) though the
  machine cap reads 7. Alternatives: auto-merge on green, more lanes. Why:
  every main-branch change stays reviewed by a session; reversible. Each
  session start: merge refs/fleet-lanes/* and send pending answers.
  Reverses: a clean week of lane runs, then a ruling to auto-merge.
- [ ] VW-RUNCAP: two operator asks, both kit-owned (FLEET-COMMON 10; VW never
  edits or resets the kit ledger locally). (a) 500 runs / 24 h, REQUEST to
  MAIN 2026-10-29 0611. (b) Operator order 2026-10-29: when the cap is hit,
  usage percent remains and the session was not told to wrap up / /done,
  record the cap-hit in the usage ledger, reset the rolling count and
  continue; REQUEST to MAIN 2026-10-29 0614 (asks one ruling on a + b).
  Until then VW runs at the kit's 120 and stops at the cap. Accept: MAIN
  answers; adopt the kit version that carries it. after: MAIN.
- [ ] VW-KIT-BOARDID: kit v25 fleet_board.py line 59 (_LINE, ID group
  `{0,15}`) silently drops checklist rows whose ID is over 16 chars (seen:
  VW-AUTOEXEC-VERIFY). FIX note sent to MAIN 2026-10-29 0612. Meanwhile render
  the board via `--progress` JSON (no ID limit). Accept: adopt the kit version
  that raises the limit or fails loudly; a stdin render shows an 18-char ID.
  after: MAIN.
