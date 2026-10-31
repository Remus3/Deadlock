# VW-APP-LIFT - sibling and outside design lift table

Status: ASSESSED, 2026-10-31 (read-only survey of the sibling trees; nothing
copied yet). Siblings are named by channel code only. A "reuse" row means the
code is taken near-verbatim with its tests and a provenance note in the
receiving file (sibling code, file role, date); "adapt" means the design is
taken and the code rewritten for VW's constraints; "skip" means it is not
taken, with the reason. Every lifted row is re-checked against the game safety
floor and `docs/research/security.md` by the receiving epic; a sibling's
choice is never a ruling for VW (siblings target other games and other
anti-cheat systems).

Licensing: sibling licenses differ (Apache-2.0, GPL-3.0-or-later, MIT). Code
lifted verbatim from a GPL-3.0 sibling would make the receiving file GPL; so
GPL rows are "adapt" (design only, fresh code) unless the operator, who owns
every tree, records a relicense. This repo's own license governs what lands.

## Lift table

| Feature | Source | Verdict | Receiving epic | Why |
|---|---|---|---|---|
| electron-builder NSIS per-user + electron-updater (GitHub provider), install on natural quit, channel split stable / dev, per-channel feed files | RC | reuse | VW-APP-SCAFFOLD | Proven on this machine; matches charter D-1. Strip RC's product-specific appId / repo / backend bundling. |
| Update cycle with owed restarts, deferred while a game is live, refused on a dev checkout | RC | adapt | VW-APP-SCAFFOLD | The live-game gate is exactly R-APP-2; RC's signal is League's client, VW's is the Deadlock process / match state from classes 1-3. |
| Install discipline: SHA-256 manifest per file, SHA256SUMS asset, self-test before switch, old dir kept as rollback, ETag-cached release check, update window | MAIN | adapt | VW-APP-SCAFFOLD | Charter D-1 adds it on top of electron-updater (SEC-U2). MAIN's updater is a Node server, not Electron, so the code does not port; the discipline does. |
| webPreferences factory: contextIsolation, nodeIntegration false, sandbox true; deny window.open; block will-navigate; subframe navigation guard | RC, EW, RSC, CS | reuse | VW-APP-SCAFFOLD | All four agree; RC adds a subframe guard and a nav_guard test. Extend with SEC-E5 (permissions), SEC-E7 (CSP header) and SEC-E14 (fuses), which no sibling has. |
| Scoped certificate pinning for a self-signed local origin, never a blanket verify callback (callback(0) also disables CT) | CS, RC | skip | - | VW loads only packaged `app://` content (SEC-E1); there is no local HTTPS origin to pin. Revisit only if a local HTTP surface is ever added. |
| Overlay window recipe: transparent, frameless, focusable false, skipTaskbar, setIgnoreMouseEvents, setAlwaysOnTop screen-saver, no navigation, window-open denied | EW | reuse | VW-APP-OVERLAY | Exactly S-2 / SEC-G3; the smallest correct implementation in the fleet. |
| Overlay placement config (anchor, display, scale) and display-change handling; design-px with scale = native_h / 1080 | EW, RC | adapt | VW-APP-OVERLAY | UX U-3 / U-4. Keep-clear zones are VW's own (Deadlock HUD), not League's or BDO's. |
| Click-through zones (hover makes a panel interactive) and drag regions | RC | skip | - | VW's overlay is never interactive in a match (R-APP-5, U-1); depth goes to the companion. Removing hover zones also removes a focus-steal path. |
| Global hotkey toggle and a Win32 hotkey listener writing signal files | RC | skip (for now) | VW-APP-CONTROLLER | A global hotkey can swallow a key the game binds (SEC-G2, S-4). Only an app chord the game does not bind, recorded in `docs/controls.md`, may come later. |
| Starting window and crash guard (relaunch limits) | RC | adapt | VW-APP-SCAFFOLD | Useful for idempotent service restarts (R-APP-3); rewrite around VW's service set. |
| Tray icon: closing the window hides it, quit from the tray | RSC, CS, EW | reuse | VW-APP-COMPANION | Small, tested in three trees; keeps the app out of the way during play. |
| Supervisor: adopt or start the backend, only stop what you started | CS, RSC | adapt | VW-APP-SCAFFOLD | The rule fits R-APP-3; VW's services are in-app (Node), not a separate Python surface, so the process model differs. |
| Companion shell over a local HTTP dashboard (surface testable without Electron) | RSC (its ADR-005) | adapt | VW-APP-COMPANION | Keep the idea that every view renders and tests without Electron; deliver it as packaged pages under `app://` rather than a localhost port (SEC-E1). |
| Shared pure-logic core loaded both as a browser script and by `node --test` (no DOM, no Electron) | EW | reuse | VW-APP-BUS, VW-APP-E1 | Lets engines and view models test alone on fixtures (charter 1.3). |
| SSE bus with hidden-tab pause, keyed rows and per-row staleness TTL | EW | adapt | VW-APP-BUS | VW's bus is in-process typed and versioned with schema rejection (charter 1.3); take the staleness TTL and pause-when-hidden ideas. |
| OCR of the operator's own screen with a review queue before applied values | EW | adapt | VW-APP-INGEST | Class 4 (S-3). The review-queue-then-apply pattern guards against OCR misreads feeding E1 / E3. |
| Watchdog (heartbeat, restart on stall) | EW | adapt | VW-APP-SCAFFOLD | R-APP-3 and the memory-leak watch (charter 1.7); add RSS / handle counters. |
| Combat math service: per-ability / per-item modules with override tables, conditional notes and a changelog | RC (its combat math service) | adapt | VW-APP-E1 | The structure (one module per mechanic, data overrides, pinned fixtures) is the E1 model the charter names; the math is League's and does not carry over. Language: E1 is JS so it runs in-app; RC's is Python. |
| Coach: analyzer, insight / cold-streak detectors, advisory sweeper | RC | adapt | VW-APP-COACH, VW-APP-E2 | Conditioned inputs and stored outputs fit R-COACH-1; detectors map to E2 focus items. Distillation to zero-LLM rules is VW's addition (R-COACH-2). |
| Fleet kit (progress files, checklist, lanes, git lock, suite gate) | MAIN | reuse (vendored) | all | Already vendored and byte-pinned; never edited locally. |
| `undici` override pinned for a transitive advisory | RC, EW, RSC, CS | adapt | VW-APP-SCAFFOLD | SEC-S7: only if `npm audit` flags it at scaffold time, with a dated removal condition. |

## Outside designs

| Feature | Source | Verdict | Receiving epic | Why |
|---|---|---|---|---|
| Overlay-platform companion apps that read game state through a platform SDK | Commercial overlay platforms (Overwolf-style) | skip | - | Their in-game overlays inject into the game process; forbidden by the floor (S-2). |
| Post-match build and stat pages, hero / item win-rate tables | Community stat sites built on the community Deadlock API | adapt | VW-APP-INGEST, VW-APP-E2 | Same class-1 data the charter allows; take presentation ideas, fetch the data ourselves with R-APP-4 rates. Their aggregates are inputs, never ground truth for E1's math. |
| A tracking overlay library that follows a target window with out-of-context WinEvent hooks | `electron-overlay-window` (npm) | skip (for now) | VW-APP-OVERLAY | Out-of-context WinEvent hooks do not inject, but the library adds a native addon (SEC-G1 allow-list) for a need that display-anchored placement already meets. Revisit with a recorded reason if borderless placement proves unstable. |
| Windows Graphics Capture / `desktopCapturer` display capture | Electron, Windows | reuse | VW-APP-INGEST | The only allowed capture path (S-3, SEC-G4). |
| Game-capture hook modes | OBS Game Capture and similar | skip | - | Injects a DLL into the game (S-3, floor). |
| SQLite binding: `better-sqlite3` (native addon) vs Node's built-in `node:sqlite` | npm / Node | decide in VW-APP-DB | VW-APP-DB | Trade-off: mature native addon (rebuild per Electron ABI, SEC-S4 budget) vs no dependency but newer API in Electron's Node. Recorded there with decision / alternatives / why. |
| Controller UI navigation patterns (focus ring, spatial grid, LB / RB columns) | Xbox Accessibility Guidelines, console dashboards | adapt | VW-APP-CONTROLLER | Taken into `docs/research/ux.md` section 4. |

## What reverses a verdict

A "skip" row reverses only with a recorded decision in the receiving epic that
names the new need and passes the floor; the injection-based rows (overlay
platforms, game-capture hooks) never reverse. A "reuse" row drops to "adapt"
when the source changes license or a security item (security.md) fails on it.
