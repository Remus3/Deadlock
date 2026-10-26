# ROADMAP - open work only

- [ ] VW-VIDEO-MENU: the six menu changes are set (read back 2026-10-25
  21:44, game closed; `docs/menu-settings-2026-10-25.md` "Read-back"):
  Fullscreen, Scaling 1.5x, DLSS Transformer, Fog Low, Area lights Off,
  Reduce camera shake On. Left: confirm `r_citadel_dlss_settings_mode` 3
  = 1.5x and `r_dlss_preset` 10 = Transformer a second time (next menu
  read) before they leave MENU_ONLY.
- [ ] VW-CONTROLS: sensitivity 1.6 at 1200 DPI (operator: R110 step 2 of 3; eDPI 1920,
  21.6 cm/360) live - read back 23:01 in user_convars and hero-settings base.
  Binds Melee MOUSE5, Item 1 Q, Item 4 E, Interact V, Ping MOUSE4 set.
  Reticle: the autoexec cannot set it (the cloud citadel_hero_settings.lst
  base block overrides the citadel_crosshair_* cvars; menu showed defaults
  23:01), so the 13 cvar lines were dropped from config/autoexec.cfg;
  operator sets the 13 rows in Settings > Game > Reticle (docs/controls.md).
  Cosmetic: keys file rewritten 23:00:34 with the game running still has
  Cosmetic1 E / 5 ("stale" theory falsified); the menu "Cosmetic" row shows 5
  = CosmeticMenu. Search "cosmetic" in Keybinds and clear an E slot if one
  shows. Also Casting mode Quick Cast, Alternate cast Press and Hold (0.15),
  Items Instant Cast. Then, game closed: apply the new autoexec
  (`tools/Apply-DeadlockConfig.ps1 -SkipRegistry -SkipLaunchOptions`, read
  back by hash) and `python tools/vw_controls.py check`: bind_changes_left,
  convars_not_yet_saved and reticle_changes_left empty.
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
