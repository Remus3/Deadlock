# VW-APP-UX - legibility, color, theme, focus and controller navigation

Status: RESEARCH DONE, 2026-10-31. Input to VW-APP-OVERLAY, VW-APP-COMPANION
and VW-APP-CONTROLLER. Requirements: `docs/companion-app.md` (R-UI-1..5,
R-APP-5, S-2, S-4). Security constraints on the same windows:
`docs/research/security.md`.

Artifacts:
- Token set: `config/app/tokens.json` (colors, plate alpha, declared pairs,
  measured ratios). Measured by `tools/vw_contrast.py`; held by
  `tests/test_ux_tokens.py` (every pair at or over its floor, recorded ratios
  current).
- Wireframes: `docs/research/wireframes/overlay.svg` (in-match overlay over
  the game) and `docs/research/wireframes/companion.svg` (second screen).

Sources (read 2026-10-31):
- [WCAG] W3C WCAG 2.2: 1.4.3 contrast minimum (4.5:1 text, 3:1 large),
  1.4.6 enhanced (7:1), 1.4.11 non-text contrast (3:1 for focus indicators
  and UI boundaries), 2.4.7 / 2.4.11 focus visible / not obscured, 2.3.3
  animation from interactions; the relative-luminance formula used verbatim
  by `tools/vw_contrast.py`.
- [MS-TYPE] Microsoft Windows app design, typography (Segoe UI type ramp,
  minimum sizes) and high-contrast themes / `forced-colors`.
- [GAMEPAD] W3C Gamepad API (standard mapping, button indices) and
  Chromium's rule that gamepad data reaches only a focused, visible document.
- [XAG] Xbox Accessibility Guidelines (XAG 101 text size, 102 contrast,
  103 additional channels beyond color, 112 UI navigation).
- [GAG] Game Accessibility Guidelines (gameaccessibilityguidelines.com):
  readable default font size, no essential info by color alone, motion
  reduction.
- Fleet precedent (codes only): EW and RC overlays (plate-backed HUD cards,
  screen-saver z-level, config-driven anchor / display / scale). See
  `docs/research/lift.md`.

## 1. Glanceability rules (overlay)

- U-1 Three lines maximum, stacked at one anchor: NOW (E3 goal_now), NEXT
  (E1 next buy or E3 goal_next), and an ABORT line only while an `abort_if`
  holds. One line is the default state (R-UI-5); depth lives on the companion.
- U-2 Each line is a verb first and at most about 32 characters, so it reads
  in one fixation; numbers carry a unit and a direction ("+18% TTK").
- U-3 Keep-clear zones, never drawn over: the crosshair disc (radius 240
  design px around screen center), the game's top-center score / timer band
  and bottom-center health / ability band, and a HUD corner. The default
  anchor is right-middle, 24 px in from the edge. The zone rectangles are
  config, not code, and VW-APP-OVERLAY re-checks them against a capture of the
  live HUD at the operator's resolution before accepting (the wireframe zones
  are placeholders, not measured HUD geometry).
- U-4 Design px are 1920x1080; the overlay scales by display height
  (scale = native_h / 1080), the fleet's proven rule (RC).
- U-5 Motion: a line changes with one 150 ms cross-fade, nothing slides,
  pulses or blinks; an ABORT line appears without animation. With Windows
  "Show animations" off (`prefers-reduced-motion`), no fade at all [WCAG
  2.3.3, GAG].
- U-6 Not color alone [XAG 103, GAG]: each state has a text prefix and a bar:
  ABORT lines start with "!" and carry the danger bar; good / bad deltas carry
  a sign. The palette's good (green) and danger (salmon) also differ in
  lightness, so they stay apart under red-green color deficiency.
- U-7 Exclusive fullscreen may hide any separate window; the overlay targets
  borderless windowed or the second screen and says so in settings (S-2).

## 2. Typography

- Face: Segoe UI (system font on Windows 10; no web font download, matches
  SEC-E7's CSP `font-src 'self'`). Numbers use `font-variant-numeric:
  tabular-nums` so values do not jitter as they change.
- Sizes (design px at 1080p): overlay NOW 28 / 600 weight, other lines 24;
  never under 20 [XAG 101 sets a 28 px floor at 1080p for TV distance; at a
  desk monitor 24 px is the working floor, and 20 is the absolute minimum].
  Companion: card title 30, body 22, labels 20. Dashboard: body 16 css px,
  scalable with the Windows text-size setting.
- Overlay text also carries a 1 px dark outline (`paint-order: stroke`) as a
  second defence where the plate meets a bright frame edge.

## 3. Color and theme (token set)

Three groups in `config/app/tokens.json`:
- `overlay.*`: a near-black plate `#0a0d12` at alpha 0.82 under every card,
  with text and state colors. Because the game frame behind the plate is
  unknown and moving, each overlay pair is measured twice, with the plate
  composited over pure black and over pure white, the two extremes; any real
  frame lands between them.
- `dark.*`: companion and dashboard default theme (bg, surface, text, muted,
  accent, good, warn, danger, focus, border).
- `light.*`: the same roles for a light theme (dashboard, daytime use).

Floors: primary text 7:1 [WCAG 1.4.6, AAA], every other text role 4.5:1
[WCAG 1.4.3], focus ring and borders 3:1 [WCAG 1.4.11]. AAA for the main line
because it is read in a glance over a moving, bright scene.

Measured (WCAG 2.x ratios, `python tools/vw_contrast.py check`, 2026-10-31):
- Overlay, plate over black / over white: text 18.22 / 10.73; muted 11.96 /
  7.04; accent 11.36 / 6.69; good 12.32 / 7.25; warn 13.19 / 7.76; danger
  8.64 / 5.08; focus 13.96 / 8.22. Worst overlay pair: danger over a white
  frame, 5.08 (floor 4.5).
- Dark theme on bg / on surface: text 16.56 / 15.07; muted 8.58 / 7.81;
  accent 9.56 / 8.70; good 10.21 / 9.29; warn 11.19 / 10.19; danger 7.38 /
  6.72; focus 13.28 / 12.08; border 3.77 / 3.44.
- Light theme on bg / on surface: text 17.22 / 18.29; muted 7.32 / 7.77;
  accent 5.97 / 6.35; good 5.79 / 6.15; warn 5.58 / 5.93; danger 6.19 / 6.57;
  focus 6.01 / 6.39; border 3.38 / 3.59.
The token file's `measured` block is the authority; the test fails when a
color changes without re-measuring (`vw_contrast.py update`).

High contrast: when Windows reports a high-contrast theme
(`nativeTheme.shouldUseHighContrastColors`, CSS `forced-colors: active`) the
companion and dashboard drop their palette for system colors [MS-TYPE]; the
overlay keeps its plate (it is not a system surface) but switches to text and
focus only, no tinted state colors.

## 4. Focus and controller navigation (S-4)

- Focus ring: 4 px solid `focus` token with a 2 px gap, always visible on the
  focused card, never clipped by a scroll edge [WCAG 2.4.7, 2.4.11]. Keyboard
  and pad share it.
- Model: the companion is three columns of cards (MACRO, BUILD, MATCH, see the
  wireframe); the dashboard is a list / detail view. Navigation is spatial
  inside a column (up / down) and by column (LB / RB, or left / right at a
  column edge) [XAG 112]. A: expand / select; B: back / collapse; Start:
  settings; View / Share: toggle the companion detail level. Nothing wraps
  silently; the end of a column gives a short edge highlight.
- Labels: the hint bar shows Xbox glyphs (A B X Y, LB RB) or PlayStation
  glyphs (cross circle square triangle, L1 R1) chosen from the Gamepad API
  `id` string; standard mapping indices are the same for both [GAMEPAD].
- Gate: the app reads the pad only while one of its own windows is focused
  (`BrowserWindow.isFocused()` checked on every poll, on top of Chromium's own
  focused-document rule [GAMEPAD]); with the game focused, pad input is
  ignored. The overlay is never focusable, so it never reads the pad. Any app
  chord while the game has focus needs the S-4 explicit chord rule and a
  `docs/controls.md` entry. The app never emits, remaps or forwards input
  (SEC-G2).
- Poll: `requestAnimationFrame` only while focused; repeat delay 400 ms, then
  120 ms per step for a held direction; stick dead zone 0.35.

## 5. Modular layout

- Cards are the unit: each engine output type maps to one card component
  (`e3.macro.v1` -> MACRO, `e1.build_advice.v1` -> BUILD, match context ->
  MATCH, `e2.skill_profile.v1` -> dashboard PROFILE). A card renders a
  headline line, then expands to detail; no card reads another's data.
- Layout is config (column order, which cards, overlay anchor, display,
  scale), validated against a schema; an invalid layout falls back to the
  default and logs why.
- Every surface shows data freshness and source class (companion footer in
  the wireframe), so a stale value is never mistaken for a live one.

## 6. Hand-off to the build epics

- VW-APP-OVERLAY: U-1..U-7, window flags SEC-G3, tokens `overlay.*`, keep-clear
  zones measured on a live HUD capture, scale rule U-4.
- VW-APP-COMPANION: wireframe `companion.svg`, tokens `dark.*` / `light.*`,
  high-contrast fallback, display chooser (R-UI-2).
- VW-APP-CONTROLLER: section 4, gate test (pad ignored while unfocused).
