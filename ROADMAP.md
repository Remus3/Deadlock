# ROADMAP - open work only

- [ ] VW-VIDEO-MENU: menu transcript done 2026-10-25
  (`docs/menu-settings-2026-10-25.md`; no particle or AA control exists).
  Operator, in game: Window mode Fullscreen; Scaling mode Auto -> 1.5x;
  DLSS Model CNN -> Transformer; Fog quality High -> Low; Area lights
  On -> Off; Reduce camera shake Off -> On. Then, with the game closed,
  `python tools/vw_video.py check` (expect no change; else `apply`) and
  diff `video.txt` against `ops/runtime/backup/` to learn the
  `r_citadel_dlss_settings_mode` / `r_dlss_preset` values of 1.5x and
  Transformer (record them; they stay MENU_ONLY until confirmed twice).
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
