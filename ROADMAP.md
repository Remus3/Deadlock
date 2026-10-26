# ROADMAP - open work only

- [ ] VW-VIDEO-MENU: the six menu changes are set (read back 2026-10-25
  21:44, game closed; `docs/menu-settings-2026-10-25.md` "Read-back"):
  Fullscreen, Scaling 1.5x, DLSS Transformer, Fog Low, Area lights Off,
  Reduce camera shake On. Left: confirm `r_citadel_dlss_settings_mode` 3
  = 1.5x and `r_dlss_preset` 10 = Transformer a second time (next menu
  read) before they leave MENU_ONLY.
- [ ] VW-CONTROLS: sensitivity 1.1 + cyan reticle applied by the autoexec
  2026-10-25 (`docs/controls.md`); sensitivity 1.1 read back in the saved
  convars 21:44. NOT yet set (read back 21:44: the cloud keys file is
  unchanged since 21:00, casting keys/convars identical to the 21:37
  backup): operator, in game, Settings > Keybinds, six rows (Melee Q ->
  MOUSE5, Item 1 Z -> Q, Item 4 V -> E, Interact E -> V, Ping MOUSE3 ->
  MOUSE4, Cosmetic E -> none); Casting mode Quick Cast, Alternate cast
  Press and Hold (0.15), Items Instant Cast. Confirm the mouse DPI
  (assumed 800; sens = 880 / DPI). Then, game closed,
  `python tools/vw_controls.py check`: `bind_changes_left` and
  `convars_not_yet_saved` both empty (reticle convars also still unsaved).
- [ ] VW-AUTOEXEC-VERIFY: on first launch with the launch option set, the
  console shows `[VW] autoexec loaded`; drop any cvar the console reports as
  unknown.
- [ ] VW-MEASURE: baseline then each change per `docs/measurement.md`; results
  in `docs/measurements/`. Includes DLSS 1.5x vs 1x (DLAA; switch if 1
  percent lows >= 200 fps) and D3D 11 vs Vulkan.
- [ ] VW-LOOP: arm a lane loop / inbox responder like the other trees (a
  scheduled tick that reads the inbox and runs `tools/vw_lane.py`), once there
  is recurring work. Until then each session reads the inbox at start and /done.
- [ ] VW-POWER: measure Balanced vs High performance power plan in game
  (machine-level; MAIN's call, file a note with the numbers).
- [ ] VW-DEPENDABOT: PR #1 (github-actions group, 3 bumps) opened on the first
  push, CI green on it. Never merge a bot PR as-is (operator-only authors):
  apply the same SHA bumps in an operator commit, push at /done, close #1.
