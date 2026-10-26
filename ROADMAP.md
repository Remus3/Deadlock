# ROADMAP - open work only

- [ ] VW-VIDEO-FULLSCREEN: video.txt written 2026-10-25 23:15 reads
  borderless (`fullscreen` 0, `nowindowborder` 1, refresh 0/0);
  `vw_video.py check` would_change those 4 keys back to exclusive
  fullscreen 240/1 (set and read back at 21:46). Left: find out whether the
  menu was switched on purpose; if not, `vw_video.py apply` with the game
  closed and read back. (VW-VIDEO-MENU closed: DLSS enum second read 23:15
  `r_citadel_dlss_settings_mode` 3 = 1.5x, `r_dlss_preset` 10 = Transformer.)
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
- [ ] VW-LOOP: arm a lane loop / inbox responder like the other trees (a
  scheduled tick that reads the inbox and runs `tools/vw_lane.py`), once there
  is recurring work. Until then each session reads the inbox at start and /done.
- [ ] VW-POWER: measure Balanced vs High performance power plan in game
  (machine-level; MAIN's call, file a note with the numbers).
- [ ] VW-DEPENDABOT: PR #1 (github-actions group, 3 bumps) opened on the first
  push, CI green on it. Never merge a bot PR as-is (operator-only authors):
  apply the same SHA bumps in an operator commit, push at /done, close #1.
