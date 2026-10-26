# ROADMAP - open work only

- [ ] VW-VIDEO-MENU: in the in-game Settings > Video confirm what the file does
  not set (`config/video.recommended.json` "menu"): shadow Medium, particles
  Low, anti-aliasing; upscaling stays DLSS Quality (game's pick) until
  VW-MEASURE says native holds 1 percent lows >= 160 fps. Then re-run
  `python tools/vw_video.py check` (expect no change) and record the keys the
  menu wrote, so they can join "keys".
- [ ] VW-AUTOEXEC-VERIFY: on first launch with the launch option set, the
  console shows `[VW] autoexec loaded`; drop any cvar the console reports as
  unknown.
- [ ] VW-MEASURE: baseline then each change per `docs/measurement.md`; results
  in `docs/measurements/`.
- [ ] VW-LOOP: arm a lane loop / inbox responder like the other trees (a
  scheduled tick that reads the inbox and runs `tools/vw_lane.py`), once there
  is recurring work. Until then each session reads the inbox at start and /done.
- [ ] VW-POWER: measure Balanced vs High performance power plan in game
  (machine-level; MAIN's call, file a note with the numbers).
- [ ] VW-DEPENDABOT: PR #1 (github-actions group, 3 bumps) opened on the first
  push, CI green on it. Never merge a bot PR as-is (operator-only authors):
  apply the same SHA bumps in an operator commit, push at /done, close #1.
