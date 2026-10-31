# VeilWalker companion app - charter (standing order 2026-10-29)

Status: CHARTER. Captured 2026-10-29 from the operator's standing order for all
future sessions. Build work starts when the operator types "continue" (see
"Start and cadence"). Open work lives in `ROADMAP.md` as `VW-APP-*` epics; this
file is the requirement set and the safety mapping they are checked against.

Precedence: the CLAUDE.md "Game safety floor" overrides every line below. Where
the order and the floor meet, the floor wins and the mapping in section 3 says
how the order's intent is met inside it.

## 1. The order as requirements

### 1.1 Product

- R-APP-1 Installable Electron desktop app for Windows 10, installed per user,
  updated from GitHub Releases in the same fashion as MAIN's console project
  (section 2): verified download, staged apply, rollback, no prompt mid-match.
- R-APP-2 Hot-swap update: a downloaded update applies only when no match is
  live and the app is idle (or on natural quit); never a dialog, focus steal or
  restart during a match.
- R-APP-3 Idempotent services: every service (ingest, DB writer, engines, UI
  bridge) can be started twice, killed and restarted with the same end state;
  writes are atomic; no service depends on another's in-memory state.
- R-APP-4 Controlled polling rates: every external poll has a configured rate,
  a ceiling, backoff on error and an ETag / If-Modified-Since cache where the
  source supports it; rates drop when no match is live.
- R-APP-5 Minimal in-match interaction: in a match the app needs no input to be
  useful; anything actionable is glanceable; settings are pre-match.

### 1.2 Surfaces

- R-UI-1 Game overlay: a SEPARATE OS window - transparent, frameless,
  always-on-top, click-through (mouse ignored), no focus - laid over the game.
  It is never injected into or drawn by the game process.
- R-UI-2 Optional second-screen companion window, chosen by the player, showing
  current match information alongside the overlay (larger, interactive).
- R-UI-3 Dashboard window for pre/post-match analysis (E2 depth lives here).
- R-UI-4 Controller input (Xbox, PS4, PS5) when connected: navigates the APP
  only (companion / dashboard), via the Gamepad API inside the app's own
  focused window; never remaps, emits or forwards input to the game.
- R-UI-5 Progressive disclosure: one line by default, depth on demand; never a
  wall of numbers in front of the player.

### 1.3 Three engines (modular, explicit contracts, shared bus)

Each engine is its own module with a versioned input / output schema. Engines
talk only through the bus (publish typed, versioned messages; subscribe to the
types they need); none writes another's tables or reads another's internals.
A malformed message is rejected at the bus with a logged reason, so one engine
cannot corrupt another. Every engine runs and tests alone on recorded fixtures.

- E1 Combat math / build engine (the "Daemon Slayer" pattern, see section 4):
  pure, deterministic combat math for the hero being played - damage, effective
  HP, time-to-kill, ability and item interactions, on/off comparisons of items
  and upgrades - in the live match context of ally and enemy heroes and their
  builds; outputs ranked next-buy / next-upgrade with the math behind each, and
  counter-responses to enemy builds.
  Out: `e1.build_advice.v1` {next_items[], reasons[], counters[], math_refs[]}.
- E2 Player analysis / skill-profile engine: from the player's own match
  history and post-match data - actions, participation in key events, accuracy,
  ability and item use, movement, response to objectives, progression over
  time - builds a skill profile (tier per dimension, confidence, trend). Output
  is concrete and explained ("in minutes 8-14 you were absent from 4 of 5 mid
  boss / walker fights; try ...", "hero X fits your profile because ..."),
  never generic ("die less"). Depth is tiered: a headline, then expandable
  detail. Hero-fit suggestions always carry their reasons.
  Out: `e2.skill_profile.v1` {tiers{dimension: tier}, focus_items[], hero_fit[]}.
- E3 Live macro engine: current goal, next goal and how to reach it, using E1's
  next-buy and E2's skill tier, from self, ally, enemy and objective state; when
  conditions change (HP, numbers, timers) it names a retreat or a realistic
  alternative route to victory. Advice is scaled to the player's tier: a
  2-hour player is not handed a 2000-hour player's plan.
  Out: `e3.macro.v1` {goal_now, goal_next, how, abort_if[], alt_route}.

### 1.4 Coach: LLM to zero-LLM

- R-COACH-1 An LLM coach is fed conditioned, structured inputs (engine outputs
  plus match context) and its outputs are stored with those inputs.
- R-COACH-2 Once enough coach data exists, it is distilled into deterministic
  rules / tables so normal use runs with zero LLM calls.
- R-COACH-3 Distilled rules carry the game patch they were made on; a new patch
  marks them for re-review (diffed against patch notes and new data) before they
  are trusted again.

### 1.5 Data

- R-DATA-1 Local database (SQLite, in the app's user-data dir, never tracked)
  for matches, heroes, items, profiles, coach data and distilled rules;
  migrations versioned; backups before a migration.
- R-DATA-2 Sources only per the safety mapping (section 3).

### 1.6 Research tracks (self-initiated, parallel)

- T-GAME: game data, public APIs, launch options, ports, outputs.
- T-HERO: heroes, items, upgrades, abilities, archetypes, counters, and the
  permutations and interactions between them, with tests.
- T-UX: legibility, typography, color, theme, focus and glanceability over a
  live game; controller navigation; modular layout.
- T-SEC: repo, architecture and supply-chain security audit (Electron
  hardening: contextIsolation, sandbox, no remote content, CSP, signed updates).
- T-LIFT: feature lift from sibling trees and outside apps (section 4).
- T-WORKSHOP: whether Deadlock has an official Steam Workshop and what it
  could carry for this app (section 3, ruling S-6).

### 1.7 Process (how the work runs)

- Autonomous: lanes and sub-agents act; decisions go to an adjudicator and are
  recorded; the operator is never waited on except for physical acts,
  passwords and OAuth grants. Operator interjections are done or filed in
  `ROADMAP.md` without halting running work.
- Red-first TDD: a failing test lands before the code that makes it pass.
- Tests: targeted tests per worktree (the touched modules); the whole suite
  only at the batch gate before a code push, through the suite gate.
- Commits batched and coherent through the kit lock; pushes tiered per
  CLAUDE.md; worktrees, scratch and temp under the VW sidecar
  (`<sidecar>/VW/Worktree`, `<sidecar>/VW/Temp`, `<sidecar>/VW/Scratch`) and
  pruned automatically at /done and when a lane ends.
- Parallel orchestration: independent work runs as parallel lanes / agents;
  anything over 5 minutes writes item-12 progress.
- Memory-leak watch: the app and its services expose RSS / handle counts; a
  growth test runs in CI; lanes record peak RSS and stop on a ceiling.
- Self-adversary: a review pass per epic attacks the design; it is limited to
  two rounds per epic and stops when a round finds nothing new (churn limit).
- Quiet main session, context-lean prose, status from progress files and the
  local board only.
- Repo hygiene: file and repo size budgets, moves and cleanups recorded,
  settings adjustable as needs change.

## 2. Pattern reused: MAIN's console updater (read 2026-10-29, read-only)

MAIN's console is NOT an Electron app: it is a Node 24 local server plus a
browser UI. Its install and update mechanism is the pattern to reuse:

- Packager: its own release builder - one zip `<app>-<version>.zip` with a
  `MANIFEST.json` (SHA-256 per file), a `SHA256SUMS.txt` covering the zip and
  `install.ps1`, release notes per version. Published as GitHub Release assets;
  publishing waits for the operator's go.
- Install: `install.ps1` (irm ... | iex, or run locally on a downloaded zip);
  checks every download against its published SHA-256; installs per user under
  LocalAppData Programs; Start menu + Desktop shortcuts, an Apps & features
  entry, user PATH; prerequisites via winget with a hash-checked fallback.
- Updater: no third-party library. One unauthenticated GitHub releases API GET,
  ETag-cached, at most every `checkHours` (default 24); settings
  {auto, channel stable|beta, checkHours, window "04:00-05:00"}; manual mode
  only shows a badge; auto applies only inside the window.
- Apply (hot swap): back up the installed code (zip), build `app/<new>` beside
  the old one from the verified release, 3-way merge local changes, `npm ci`,
  self-test, and only then switch the install marker. A failed self-test leaves
  the marker on the old version (the old dir is never modified, so it IS the
  rollback). User data lives outside every app dir.
- Restart: only when no pane is busy; otherwise the restart waits for the next
  tick (a per-user scheduled task runs the tick).
- Signing: none (integrity by SHA-256 manifests, not Authenticode).

Sibling Electron pattern (RC's shell): electron-builder NSIS (oneClick, per
user) + electron-updater with the GitHub provider; `autoDownload` true,
`autoInstallOnAppQuit` true, never `quitAndInstall` mid-session, update events
console-only (no dialogs, no focus steal over a live game).

VW decision (adjudicated, D-1): electron-builder NSIS per-user +
electron-updater (GitHub provider), install on natural quit or when no match is
live, never mid-match; plus console's discipline - SHA-256 manifest check of the
installed tree, a self-test before the switch, the previous version kept as
rollback, ETag-cached check at a configured rate, stable / beta channel, an
update window. Alternatives: console's custom zip updater alone (no native
installer, more code to own for Electron's binary); Squirrel.Windows (older,
weaker per-user story). Why: Electron ships a binary runtime, which
electron-builder / electron-updater handle natively and RC already runs in this
fleet; console's verify / self-test / rollback discipline closes the gaps.
Code signing: research item in VW-APP-SEC (unsigned NSIS triggers SmartScreen).

VW decision D-1a (VW-APP-SCAFFOLD, 2026-10-31; amends D-1): keep
electron-builder per-user NSIS, but DROP electron-updater; the update path is
VW's own small updater (`app/src/main/updater/`), console's pattern on top of
the NSIS installer. Flow: ETag-cached GET of this repo's releases (rate
`checkHours`, channel stable / beta); download the installer and the
release's `SHA256SUMS.txt`, refuse on any mismatch; also download and verify
the CURRENT version's installer as the rollback image (no verified rollback
image = no update); re-verify both right before apply; apply only on natural
quit or idle, never while `isInMatch()`; run the installer silently with
relaunch; the new build self-tests before any window and, on failure or a
boot loop, re-installs the verified rollback image and skips that version.
Alternatives: electron-updater as in D-1 (sha512 against `latest.yml`, but
no self-test / rollback hook, and a runtime dependency to keep patched);
electron-updater for download plus a VW wrapper for verify / rollback (two
update state machines to reconcile); Squirrel (rejected in D-1). Why: the
charter's verify / self-test / rollback / never-mid-match discipline is the
whole requirement, a few hundred lines own it end to end and test it without
Electron, and the app keeps zero runtime dependencies (SEC-S4). Reverses: a
need for delta updates or for signature-checked updates (SIGN-0 reversed),
where electron-updater's blockmap and `publisherName` check pay for
themselves.

## 3. Safety mapping (mandatory; the floor governs)

Allowed live and offline data sources, and only these:
1. Public / official web APIs: the community Deadlock API (match history,
   builds, hero and item data, assets), the Steam Web API, Valve's published
   patch notes. Rate-limited per R-APP-4, keys never tracked.
2. Post-match data and replays as the game or the APIs publish them.
3. The game's own user-facing outputs (files the game writes that a player can
   read: config, keys, video settings, logs or console output the game itself
   writes to disk), read-only.
4. Screen capture / CV of the operator's own display, external to the game
   process (OS display or window capture, like OBS display capture).

Never: game memory reads, DLL injection, D3D / DXGI / Vulkan hooks, packet
capture or inspection, sending or synthesizing input to the game, writing any
game file beyond the two the floor allows, touching `bin/` or any `.vpk`.

Adjudicated rulings (2026-10-29; decision, alternatives, why, what reverses):
- S-1 Data sources: only the four classes above. Alternatives: memory readers
  (as some overlay products do), packet sniffing. Why: VAC and the floor; the
  four classes cover E1-E3 at lower fidelity, with CV filling live gaps.
  Reverses: never (floor).
- S-2 Overlay: separate OS window, transparent, click-through,
  always-on-top, no focus; exclusive fullscreen may hide it, so the overlay
  targets borderless or the second screen and says so. Alternatives: in-game
  overlay via a present hook (forbidden: hook); Steam overlay browser (cannot
  host an app). Why: only a separate window stays outside the game process.
  Reverses: never for the hook alternative.
- S-3 Screen capture: Windows Graphics Capture or display / window capture
  only. OBS "Game Capture" mode is FORBIDDEN (it injects a hook DLL into the
  game process). Alternatives: OBS Game Capture (forbidden), DXGI desktop
  duplication (allowed, OS-level). Why: capture must never touch the game
  process. Reverses: never for injecting modes.
- S-4 Controllers: app navigation only, read inside the app's own focused
  window; the app never emits, remaps or forwards input, and ignores the pad
  while the game has focus unless the player holds an explicit app chord that
  the game does not bind. Alternatives: global XInput hook / virtual pad
  (forbidden: input to the game). Why: floor, no input to the game.
  Reverses: never for emitting input.
- S-5 Console port (`-netconport`): NOT used. Research item only (VW-APP-GAME).
  It is a write-capable channel into the game console; using it needs a
  separate adjudicated ruling backed by Valve's stated position, and even then
  read-only listening at most, never commands. Alternatives: read the game's
  console log file if the game writes one (allowed, class 3). Reverses: a
  recorded ruling citing Valve's stance that netcon listening is permitted in
  matchmaking.
- S-6 Workshop / mods: only an official Steam Workshop for Deadlock, if one
  exists, and only for content the game itself loads through it; VPK addons and
  any file under `bin/` or a `.vpk` are excluded by the floor. Research decides
  whether an official channel exists. Reverses: Valve ships an official
  Workshop (then a new ruling scopes it).
- S-7 Game state integration (a `gamestate_integration_*.cfg` like other
  Source 2 games): if Deadlock supports it, writing that cfg is a third
  game-side file the floor does not list, so it is NOT written; it needs an
  operator amendment of the floor. Alternatives: classes 1-4. Reverses: the
  operator amends the floor's file list.
- S-8 Run cycle cap: the operator asked for 500 headless runs per 24 h;
  FLEET-COMMON 10 and the byte-pinned kit (RUNS_CAP 120) cap at 120. VW runs at
  120 and has asked MAIN for a kit change (request note 2026-10-29). Never
  edited locally. Reverses: a kit version that raises or configures the cap.

## 4. Sibling feature lift (read-only survey 2026-10-29; codes only)

- RC: live League coaching dashboard - "Daemon Slayer" combat DPS math
  service (the E1 model the order names), LLM coach integration, item /
  composition advisors, an Electron shell with electron-builder +
  electron-updater (section 2), a lane widget. Lift: E1 structure, coach
  conditioning and storage, shell updater code.
- EW: Electron app with a dashboard window and a separate transparent
  click-through always-on-top overlay window (screen-saver level, no
  navigation, window-open denied, config-driven anchor / display / scale).
  Lift: the overlay window recipe and its placement config.
- RSC: Electron companion shell over a local dashboard (its ADR-005), stdlib
  Python services. Lift: companion-window ADR and service layout.
- CS: Electron shell. Lift: assess in VW-APP-LIFT.
- MAIN: console install / update discipline (section 2); fleet kit.
VW-APP-LIFT does the full assessment and records what is reused.

## 5. Start and cadence

- This charter session only captured the order. When the operator types
  "continue", the session arms VW-LOOP lanes and starts the VW-APP research
  epics in parallel, then builds in ROADMAP order.
- Commit / push / prune point: /done (batched; push per CLAUDE.md tiers);
  lanes prune their worktree on exit.

## 6. App scaffold (VW-APP-SCAFFOLD, built 2026-10-31)

Layout, all under `app/` (Node 24, npm 11, CommonJS):
- `src/main/main.js`: Electron main. `app.enableSandbox()`, single instance,
  `app://vw/` protocol serving only `src/renderer/` with the SEC-E7 CSP
  header, permissions denied, navigation / new windows / webviews blocked,
  one IPC handler (`vw:get-info`) that checks the sender frame is `app://`.
- `src/main/webprefs.js`: the one webPreferences factory (contextIsolation,
  sandbox, no nodeIntegration of any kind, webSecurity on, no webview).
- `src/preload/preload.js`: sandboxed; exposes `window.vw.getInfo()` only.
- `src/renderer/`: dashboard shell on the VW-APP-UX dark tokens;
  `tokens.css` is generated from `config/app/tokens.json`
  (`npm run tokens`; a test fails on drift).
- `src/main/matchGate.js`: `isInMatch()` gate. Stub (TODO VW-APP-INGEST):
  no provider = not in match; a provider that throws = in match (fail
  closed, the update waits).
- `src/main/updater/`: D-1a updater (feed, sha, state, updater core,
  platform wiring); state in `<userData>/updates/state.json`, written
  atomically.
- `src/main/selftest.js`: the post-update self-test, also run as
  `VeilWalker.exe --vw-self-test [--vw-self-test-out=<file>]` (exit 0 / 1).
- `electron-builder.yml`: per-user NSIS (oneClick, no elevation), unsigned
  (SIGN-0), `publish: null`; `scripts/after-pack.js` flips the SEC-E14 fuses
  (read back on the 0.1.0 build: RunAsNode off, NODE_OPTIONS off, inspect off,
  embedded asar integrity on, only-load-from-asar on, file-protocol extra
  privileges off, cookie encryption on).
- Update feed: owner/repo is never tracked (privacy rule);
  `scripts/write-feed.js` bakes it into the gitignored `build/feed.json`
  from `VW_UPDATE_REPO`, `GITHUB_REPOSITORY` or the origin remote. No feed
  or a dev run = updater off.
- `.npmrc`: `ignore-scripts=true` (SEC-S3); `npm run electron:install`
  fetches the Electron runtime for `npm start`.

Commands (in `app/`): `npm ci`, `npm test` (node:test), `npm start`,
`npm run dist` (NSIS installer in `dist/`), `npm run sums`
(`dist/SHA256SUMS.txt`).

CI: `.github/workflows/app.yml` runs the app tests on ubuntu and windows,
the token-sync check, `npm audit --omit=dev --audit-level=high` and the
Electron support-window check. `.github/workflows/app-release.yml` builds
on a `v0.*` tag whose version equals `app/package.json`, self-tests the
packaged exe and attaches the installer and `SHA256SUMS.txt` to a DRAFT
release; publishing it is the operator's go. Dependabot covers `app/` npm;
CodeQL covers JavaScript.

Release asset contract: `VeilWalker-Setup-<version>.exe` plus
`SHA256SUMS.txt` (`<sha256>  <name>` lines) on the release tagged
`v<version>`; a release without both is ignored by the updater.

Open: VW-APP-UPDATE-E2E (the live two-release run) and VW-APP-WATCHDOG
(a build that dies before main.js runs) in `ROADMAP.md`.

## 7. Message bus and engine contracts (VW-APP-BUS, built 2026-10-31)

Code: `app/src/main/bus/` (pure Node, zero runtime dependencies, no
electron import); proof `app/test/bus.test.js`.
- `schema.js`: a small in-repo validator (kinds string / number / boolean /
  array / object / map, `nullable`). Every string and array has an upper
  bound; objects are closed (an unknown key is an error); `__proto__`,
  `constructor`, `prototype` keys are refused; errors are `<path>: <reason>`
  and never echo the input value.
- `contracts.js`: the registry. Type = `<engine>.<name>.v<n>`; engines
  `e1`, `e2`, `e3`, `ui`. Registered v1 types:
  - `e1.build_advice.v1` {hero?, patch?, next_items[{item, rank, gain_pct,
    reason}], reasons[], counters[{threat, response}], math_refs[]}; rule:
    each next item's `reason` indexes an existing reason; `math_refs` name
    the pure functions used (e.g. `vw_combat.effective_hp`).
  - `e2.skill_profile.v1` {tiers{dimension: {tier 1-5, confidence 0-1,
    trend up|flat|down}}, focus_items[{text, from_min, to_min}],
    hero_fit[{hero, reasons[1..]}]}; rule: a time frame runs forward.
  - `e3.macro.v1` {goal_now, goal_next, how, abort_if[], alt_route|null}.
  - `ui.layout.v1` {cards[MACRO|BUILD|MATCH|PROFILE], overlay_anchor,
    scale 0.75-2} (docs/research/ux.md section 5): the only type a renderer
    may publish. Engine outputs are main-side only.
  A new version is a new entry beside the old one; a published schema is
  never edited.
- `bus.js`: `createBus({log})` -> `publish({type, payload}, {source})`,
  `subscribe(type, fn)` (returns unsubscribe; an unregistered type throws).
  An unknown type, an unknown version of a known type (the reason names the
  registered versions), a malformed envelope or a schema / rule failure is
  rejected with one logged `bus reject` line and no subscriber runs. Each
  subscriber gets one deep-frozen copy; a throwing or rejecting subscriber is
  logged (`bus subscriber error`) and the rest still run. Re-entrant
  publishes stop at depth 8.
- `ipc.js` (SEC-E13 runtime half): channel `vw:bus:publish`, registered in
  `main.js`; the preload adds `window.vw.publish(message)` (invoke only).
  Main refuses, logged, before the bus: a sender frame that is not `app://`,
  a message over 64 KiB or not serialisable, an engine type from the
  renderer; then the bus validates as above.

Decisions (VW-APP-BUS, adjudicated in-lane): in-repo validator over a JSON
Schema library (SEC-S4 zero runtime dependencies; alternatives ajv,
zod - rejected as runtime deps); synchronous in-process delivery over an
async queue (deterministic tests and ordering; an async subscriber's
rejection is still caught); renderer may publish an explicit allow-list
(`renderer: true` per contract) over all types (untrusted input must not
forge engine output); JSDoc types, no TypeScript build (the scaffold has
none).
