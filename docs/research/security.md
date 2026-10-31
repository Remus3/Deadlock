# VW-APP-SEC - security and architecture audit plan

Status: AUDIT PLAN, 2026-10-31. Input to VW-APP-SCAFFOLD (which may start once
this lands) and every later `VW-APP-*` build epic. Requirements and the safety
mapping live in `docs/companion-app.md`; the CLAUDE.md game safety floor
outranks everything here.

Status updates after the audit are in section 7 (newest wins).

How to read the checklist: each item has an ID, the rule, how it is verified
(a test or a gate, never a promise), its owner epic, and a status today.
- PASS: true now in this repo, with the evidence named.
- FAIL: not true yet. For app items this means "no code exists yet"; the owner
  epic must land the named test red-first and turn it green before its
  acceptance is claimed. A FAIL item is never waived; changing an item needs a
  recorded decision (decision, alternatives, why) in this file.
- N/A-BY-DESIGN: the risky feature is excluded; the verify step proves it stays
  excluded.

Sources (read 2026-10-31):
- [E-SEC] Electron, "Security" tutorial, checklist items 1-20
  (electronjs.org/docs/latest/tutorial/security).
- [E-FUSE] Electron, "Electron Fuses" (electronjs.org/docs/latest/tutorial/fuses).
- [E-CTX] Electron, "Context Isolation" and "Process Sandboxing" tutorials.
- [E-REL] Electron release timelines: only the latest three stable majors get
  security fixes (electronjs.org/docs/latest/tutorial/electron-timelines).
- [EB-SIGN] electron-builder, "Code Signing" and "Windows" docs
  (electron.build/code-signing, electron.build/win).
- [EU] electron-updater, "Auto Update" (electron.build/auto-update):
  sha512 check against `latest.yml`, `publisherName` signature check on Windows.
- [MS-SS] Microsoft, SmartScreen reputation for downloaded executables
  (learn.microsoft.com, Microsoft Defender SmartScreen overview).
- [MS-ATS] Microsoft, Artifact Signing (formerly Trusted Signing) overview
  and its identity validation requirements (learn.microsoft.com).
- [CAB] CA/Browser Forum Baseline Requirements for code signing: since
  2023-06-01 OV and EV code-signing keys must live on a hardware module.
- [GH-HARD] GitHub, "Security hardening for GitHub Actions" (pin actions to a
  full commit SHA, least-privilege `permissions`).
- [OWASP-ES] OWASP, Electron security notes / Electronegativity checks.
- Fleet precedent (codes only): RC, EW, RSC and CS shells all set
  `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, deny
  `setWindowOpenHandler` and block `will-navigate`; EW and RC set a CSP in their
  HTML; none sets Electron fuses; RC pins an `undici` override for a transitive
  advisory. See `docs/research/lift.md`.

## 1. Electron hardening ([E-SEC] items, mapped)

- SEC-E1 Load only local, packaged content (custom `app://` protocol from the
  asar); no `http:`/`https:` page is ever loaded into a window. No remote
  content at all ([E-SEC] 1, 18). Verify: a main-process test asserts every
  `loadURL` / `loadFile` target is `app://`; a renderer CSP blocks the rest.
  Owner: VW-APP-SCAFFOLD. Status: FAIL (no code).
- SEC-E2 `nodeIntegration: false`, `nodeIntegrationInWorker: false`,
  `nodeIntegrationInSubFrames: false` on every BrowserWindow ([E-SEC] 2).
  Verify: one `webPreferences` factory; a test asserts every window is built
  from it and the flags. Owner: VW-APP-SCAFFOLD. Status: FAIL (no code).
- SEC-E3 `contextIsolation: true` on every window ([E-SEC] 3, [E-CTX]).
  Verify: same factory test. Owner: VW-APP-SCAFFOLD. Status: FAIL.
- SEC-E4 `sandbox: true` on every renderer, and `app.enableSandbox()` before
  `ready` ([E-SEC] 4). The preload therefore requires only `electron`'s
  `contextBridge` / `ipcRenderer`. Verify: factory test plus a startup
  assertion. Owner: VW-APP-SCAFFOLD. Status: FAIL.
- SEC-E5 Deny all permission requests by default
  (`session.setPermissionRequestHandler` and `setPermissionCheckHandler` return
  false), with one named exception if VW-APP-INGEST needs display capture, granted
  only to the app's own origin and only via `desktopCapturer` in main
  ([E-SEC] 5). Verify: test enumerates permissions and expects deny.
  Owner: VW-APP-SCAFFOLD (exception: VW-APP-INGEST). Status: FAIL.
- SEC-E6 `webSecurity` never false, `allowRunningInsecureContent` never true,
  `experimentalFeatures` never true, no `enableBlinkFeatures` ([E-SEC] 6, 8, 9,
  10). Verify: a repo grep test fails on any of those tokens in app source.
  Owner: VW-APP-SCAFFOLD. Status: FAIL.
- SEC-E7 Strict CSP on every page, delivered as a response header by the
  `app://` protocol handler and mirrored in a meta tag:
  `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'
  data:; font-src 'self'; connect-src 'self'; base-uri 'none'; form-action
  'none'; frame-ancestors 'none'` - no `unsafe-inline`, no `unsafe-eval`
  ([E-SEC] 7). Network calls happen in main / services, never in a renderer.
  Verify: protocol-handler test reads the header; a page test fails on any
  inline script. Owner: VW-APP-SCAFFOLD. Status: FAIL.
- SEC-E8 No `<webview>`, no `BrowserView` / `WebContentsView` of external
  content; `webviewTag: false` ([E-SEC] 11, 12). Verify: grep test.
  Owner: VW-APP-SCAFFOLD. Status: N/A-BY-DESIGN (until code exists, FAIL on
  the test).
- SEC-E9 Navigation blocked: `will-navigate`, `will-redirect` and
  `will-frame-navigate` prevented for anything not `app://` ([E-SEC] 13).
  Verify: test drives a navigation and expects preventDefault. Owner:
  VW-APP-SCAFFOLD. Status: FAIL.
- SEC-E10 New windows denied: `setWindowOpenHandler(() => ({action: "deny"}))`
  on every webContents, also via `app.on("web-contents-created")` so no window
  escapes it ([E-SEC] 14). Verify: test. Owner: VW-APP-SCAFFOLD. Status: FAIL.
- SEC-E11 `shell.openExternal` only from main, only for an allow-list of
  `https://` URLs (patch notes, the repo's release page), never with a
  renderer-supplied string ([E-SEC] 15). Verify: unit test of the allow-list.
  Owner: VW-APP-COMPANION. Status: FAIL.
- SEC-E12 Current Electron: a supported stable major (latest three per
  [E-REL]), exact version pinned in `package.json` and the lockfile; a CI check
  fails when the pinned major falls out of support ([E-SEC] 16). Owner:
  VW-APP-SCAFFOLD. Status: FAIL.
- SEC-E13 IPC: preload exposes a small, typed `contextBridge` API (no raw
  `ipcRenderer`, no `send(channel)` passthrough); main validates `event.sender`
  / `senderFrame.url` is `app://` and validates every payload against the bus
  schema ([E-SEC] 17, 20). Verify: test sends from a fake frame and a
  malformed payload; both refused with a logged reason. Owner: VW-APP-BUS
  (preload shape: VW-APP-SCAFFOLD). Status: FAIL.
- SEC-E14 Fuses flipped at package time with `@electron/fuses`
  ([E-FUSE], [E-SEC] 19): RunAsNode off, EnableNodeOptionsEnvironmentVariable
  off, EnableNodeCliInspectArguments off, EnableEmbeddedAsarIntegrityValidation
  on, OnlyLoadAppFromAsar on, GrantFileProtocolExtraPrivileges off,
  EnableCookieEncryption on. Verify: a post-pack test reads the fuse wire of
  the built exe. Owner: VW-APP-SCAFFOLD. Status: FAIL. Note: no fleet sibling
  does this yet; it is new work, and worth reporting to MAIN once proven.
- SEC-E15 Single instance (`requestSingleInstanceLock`); a second launch focuses
  the dashboard, never during a match (R-APP-2). Owner: VW-APP-SCAFFOLD.
  Status: FAIL.
- SEC-E16 No remote module, no `@electron/remote`. Verify: dependency test.
  Owner: VW-APP-SCAFFOLD. Status: N/A-BY-DESIGN.

## 2. Game safety floor, as app checks

These restate the floor so a test can hold it; the floor is the authority.
- SEC-G1 No native module that opens the game process (no `OpenProcess`,
  `ReadProcessMemory`, `CreateRemoteThread`, `SetWindowsHookEx` on the game,
  no DLL in the game). Verify: dependency allow-list test (no native addons
  except ones listed here with a reason) plus a source grep for those Win32
  names. Owner: VW-APP-SCAFFOLD. Status: FAIL (no code).
- SEC-G2 No input emitted: no `robotjs`, `nut.js`, `SendInput`, virtual pad
  driver, `globalShortcut` that swallows a key the game binds. A global
  shortcut, if any, must be a chord the game does not bind and is listed in
  `docs/controls.md`. Owner: VW-APP-CONTROLLER (and SCAFFOLD for the grep).
  Status: FAIL.
- SEC-G3 Overlay window flags: `transparent`, `frame: false`, `focusable:
  false`, `skipTaskbar`, `setIgnoreMouseEvents(true)`, `setAlwaysOnTop(true,
  "screen-saver")`, separate OS window (S-2). Verify: the window-flags test
  named in VW-APP-OVERLAY's acceptance. Owner: VW-APP-OVERLAY. Status: FAIL.
- SEC-G4 Capture only via Windows Graphics Capture / `desktopCapturer`
  (S-3); no game-capture hook. Owner: VW-APP-INGEST. Status: FAIL.
- SEC-G5 Game files read-only: the app's only game-side reads are class-3
  outputs; the app writes no game file at all (the autoexec stays the repo
  tool's job). Verify: an fs wrapper that refuses writes under `<Deadlock>`.
  Owner: VW-APP-INGEST. Status: FAIL.
- SEC-G6 No console port, no game-state-integration cfg (S-5, S-7). Verify:
  grep test for `netconport` / `gamestate_integration`. Owner: VW-APP-INGEST.
  Status: N/A-BY-DESIGN.

## 3. Update path and code signing

- SEC-U1 Updates only from this repo's GitHub Releases over HTTPS (feed pinned
  by owner/repo in `electron-builder.yml`); no other provider, no generic URL.
  Owner: VW-APP-SCAFFOLD. Status: FAIL.
- SEC-U2 electron-updater's sha512 check of the downloaded installer against
  `latest.yml` ([EU]) PLUS a VW `SHA256SUMS.txt` release asset checked before
  apply, PLUS the installed-tree SHA-256 manifest and self-test before the
  switch (charter D-1). Verify: test feeds a tampered installer and a tampered
  manifest; both refused, old version kept. Owner: VW-APP-SCAFFOLD.
  Status: FAIL.
- SEC-U3 Apply only on natural quit or when no match is live and the app is
  idle; no dialog, no focus steal (R-APP-2). Owner: VW-APP-SCAFFOLD.
  Status: FAIL.
- SEC-U4 Release builds come from CI on a tag, not from a dev box, so the
  artifact is reproducible from the tagged tree; `vw_release.py check` passes
  first. Owner: VW-APP-SCAFFOLD. Status: FAIL.
- SEC-U5 Code-signing decision: see section 6. Status: DECIDED.

## 4. Supply chain

- SEC-S1 GitHub Actions pinned to full commit SHAs with a version comment
  ([GH-HARD]). Status: PASS (`.github/workflows/ci.yml`, `codeql.yml`; bumps via
  Dependabot, applied as operator commits). Owner: repo.
- SEC-S2 Workflow `permissions: contents: read` by default; a release job gets
  `contents: write` only on its own job. Status: PASS for the existing
  workflows; the release job is VW-APP-SCAFFOLD's (FAIL until written).
- SEC-S3 npm: lockfile committed, installs only with `npm ci`,
  `--ignore-scripts` by default with an allow-list for the few packages that
  need install scripts (electron, electron-builder deps). Owner:
  VW-APP-SCAFFOLD. Status: FAIL.
- SEC-S4 Dependency budget: runtime deps limited to `electron-updater` plus
  what the DB and bus epics justify in writing (SQLite binding choice recorded
  in VW-APP-DB); every addition named here with a reason. Owner: each epic.
  Status: FAIL (no app deps yet; the budget applies from the first).
- SEC-S5 Dependabot extended to `npm` for the app directory, grouped, never
  auto-merged; `npm audit --omit=dev` (high and above) fails CI. Owner:
  VW-APP-SCAFFOLD. Status: FAIL.
- SEC-S6 CodeQL covers JavaScript once app code exists (today: Python).
  Status: PASS for Python (`codeql.yml`); JS is VW-APP-SCAFFOLD's (FAIL).
- SEC-S7 Transitive advisories handled by an `overrides` entry with a dated
  comment and a removal condition (fleet precedent: an `undici` override in
  four siblings). Owner: VW-APP-SCAFFOLD. Status: FAIL.

## 5. Privacy and data

- SEC-P1 No machine path, user name, Steam id, email or token in any tracked
  file; leak gate on commit and push. Status: PASS (`tools/vw_privacy.py`,
  `tests/test_privacy.py`, `.githooks/`). Owner: repo.
- SEC-P2 The SQLite DB, logs, captures and coach data live in the app's
  user-data dir, never in the repo; the repo's `.gitignore` also covers any
  in-tree dev data dir. Owner: VW-APP-DB. Status: FAIL (no app yet).
- SEC-P3 API keys (Steam Web API, LLM) stored with Electron `safeStorage`
  (DPAPI on Windows), never in plain JSON, never logged. Owner: VW-APP-INGEST
  (Steam key), VW-APP-COACH (LLM key). Status: FAIL.
- SEC-P4 Screen captures are processed in memory and discarded; nothing
  stored unless the player turns on a named debug setting, which stores to the
  user-data dir with a size cap and an age purge. Owner: VW-APP-INGEST.
  Status: FAIL.
- SEC-P5 Coach calls send only conditioned engine outputs and match context;
  no Steam id, name or raw capture leaves the box. Verify: a payload test
  against a recorded set. Owner: VW-APP-COACH. Status: FAIL.
- SEC-P6 Logs redact paths under the user profile and any id shape the leak
  gate knows. Owner: VW-APP-SCAFFOLD. Status: FAIL.
- SEC-P7 No telemetry, no crash upload. Crash dumps stay local. Owner:
  VW-APP-SCAFFOLD. Status: N/A-BY-DESIGN.

## 6. Code-signing decision (adjudicated 2026-10-31)

Decision: SIGN-0. Ship 0.x releases UNSIGNED (no Authenticode). Integrity and
authenticity rest on (a) HTTPS from this repo's GitHub Releases, (b)
electron-updater's sha512 against `latest.yml`, (c) the VW `SHA256SUMS.txt`
asset and installed-tree SHA-256 manifest with self-test and rollback
(SEC-U2), (d) CI-built tagged releases (SEC-U4). electron-updater's Windows
`publisherName` check is therefore not configured, and the docs say so.

Alternatives considered:
- Microsoft Artifact Signing (formerly Trusted Signing) [MS-ATS]: cheapest real
  Authenticode (monthly fee), cloud-held key, works from GitHub Actions; needs
  a validated legal identity (individual or organization) - an operator-only
  act and a recurring cost. Builds SmartScreen reputation over time.
- OV / EV certificate from a public CA [CAB]: keys on a hardware token or cloud
  HSM since 2023-06; higher cost; EV no longer grants instant SmartScreen
  reputation [MS-SS]. Worst fit for a CI-built single-user app.
- SignPath Foundation (free OSS signing): needs an application and approval and
  a public OSS project meeting its criteria; possible later, not now.
- Self-signed certificate: gives no SmartScreen or trust benefit on another
  machine and adds a key to guard; rejected.

Why: the only install target is the operator's own PC, installed from the
operator's own public repo. SmartScreen's one-time "unrecognized app" prompt
on first install is the whole cost of SIGN-0 and is acceptable there; updates
run through electron-updater, whose downloaded installer carries no
Mark-of-the-Web, so SmartScreen is not expected to prompt again
(VW-APP-SCAFFOLD verifies this on its first real update and records it). Every signing path needs an operator identity
validation and money for a benefit (reputation for strangers) the app does not
need yet. Fleet precedent agrees: MAIN's console ships unsigned with SHA-256
manifests; RC's shell ships without a signing config.

What reverses it: (1) the app is offered to anyone besides the operator; or
(2) SmartScreen or Defender blocks the operator's own install or update
outright; or (3) an anti-cheat or Windows policy starts requiring signed
companion processes. Then: Artifact Signing [MS-ATS] in the release job, with
`publisherName` set for electron-updater, and SEC-U5 is re-decided here.

## 7. Status update 2026-10-31 (VW-APP-SCAFFOLD, `app/`)

Tests are `app/test/*.test.js` (node:test, `npm test`, CI `app.yml`).
- SEC-E1 PASS: app:// only; `security.test.js` asserts every `loadURL` is
  ORIGIN-based, no `loadFile`, and app:// resolution never leaves
  `src/renderer/` (encoded traversal refused).
- SEC-E2 / E3 / E4 PASS: one factory (`src/main/webprefs.js`), a test checks
  every `new BrowserWindow(` uses it and the flags; `app.enableSandbox()`
  asserted in main.
- SEC-E5 PASS (static): request and check handlers both deny; a runtime
  enumeration test needs Electron and lands with VW-APP-INGEST's exception.
- SEC-E6 / E8 / E16 PASS: forbidden-token grep over `app/src`.
- SEC-E7 PASS: header from the protocol handler equals the meta CSP; page
  test rejects inline script, handlers, styles and remote URLs.
- SEC-E9 / E10 PASS (static): will-navigate / will-redirect /
  will-frame-navigate / window-open / webview guards wired via
  `web-contents-created`; a driven-navigation test needs the runtime
  (VW-APP-UPDATE-E2E run or a later Electron test harness).
- SEC-E12 PASS: Electron 45.2.1 pinned exact; CI fails when the major leaves
  the latest-three window.
- SEC-E13 PARTIAL: preload shape PASS (fixed API, test); sender-frame check
  wired; payload schema checks are VW-APP-BUS.
- SEC-E14 PASS: fuses flipped in `scripts/after-pack.js`, read back on the
  0.1.0 build; the packaged exe self-test passed with asar integrity on. A
  CI post-pack fuse read is a follow-up inside VW-APP-UPDATE-E2E.
- SEC-E15 PASS: single-instance lock; second launch focuses only when not
  in a match.
- SEC-G1 / G2 / G6 PASS (grep part): no Win32 process / input APIs, no FFI or
  input packages, no globalShortcut, no netconport / gamestate tokens.
- SEC-U1 PASS: GitHub releases API of the baked-in repo only; asset URLs
  must be https on github.com / *.githubusercontent.com (also after
  redirect). Feed lives in `build/feed.json`, not `electron-builder.yml`,
  because the owner/repo is never tracked (privacy rule).
- SEC-U2 PASS (D-1a): electron-updater is not used, so its sha512 leg is
  replaced by the VW `SHA256SUMS.txt` check of BOTH the new installer and the
  current version's installer (the rollback image), re-verified at apply;
  self-test before the switch; failed self-test or boot loop re-installs the
  rollback image. Tests: mismatch refused, tamper-at-apply refused, rollback
  image tampered refused, rollback on failed self-test.
- SEC-U3 PASS: apply only on natural quit or idle and never while
  `isInMatch()`; no dialog. Test: deferred while in match. The live-match
  provider is VW-APP-INGEST (stub, fail closed on error).
- SEC-U4 PASS: `app-release.yml` builds on the tag in CI, self-tests the
  packaged exe, drafts the release; the operator publishes.
- SEC-S2 PASS: the release job alone has `contents: write`.
- SEC-S3 PASS: lockfile committed, `npm ci` in CI, `.npmrc`
  `ignore-scripts=true`, Electron's runtime fetch is an explicit script.
- SEC-S4 PASS: zero runtime dependencies; dev only: electron,
  electron-builder, @electron/fuses (packaging).
- SEC-S5 PASS: Dependabot npm for `/app`, grouped; `npm audit --omit=dev
  --audit-level=high` in CI (0 found at 0.1.0; 15 moderate in dev-only
  build tooling, not shipped).
- SEC-S6 PASS: CodeQL matrix gains `javascript-typescript`.
- SEC-S7 N/A for now: no runtime advisory to override.
- SEC-P6 PASS (basic): `src/main/log.js` redacts the profile path, account
  name and Steam64 ids; logs stay in user data.
- SEC-P7 N/A-BY-DESIGN holds: no telemetry or crash upload code.
