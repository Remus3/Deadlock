# ROADMAP - open work only

- [ ] DL-LAUNCH (priority): set Steam launch options `+exec autoexec`. Steam was
  running at setup (2026-10-25), so localconfig.vdf was not edited. With Steam
  closed: `python tools/dl_launch.py apply`, read back with `check`. Or set it
  in Steam's Properties. Proof: `dl_launch.py check` shows current == wanted.
- [ ] DL-VIDEO: after the first launch and exit, `python tools/dl_video.py check`
  then `apply`; confirm the in-game menu values from
  `config/video.recommended.json` "menu" (Reflex, upscaling, quality).
- [ ] DL-AUTOEXEC-VERIFY: on first launch with the launch option set, the
  console shows `[DL] autoexec loaded`; drop any cvar the console reports as
  unknown.
- [ ] DL-MEASURE: baseline then each change per `docs/measurement.md`; results
  in `docs/measurements/`.
- [ ] DL-LOOP: arm a lane loop / inbox responder like the other trees (a
  scheduled tick that reads the inbox and runs `tools/dl_lane.py`), once there
  is recurring work. Until then each session reads the inbox at start and /done.
- [ ] DL-POWER: measure Balanced vs High performance power plan in game
  (machine-level; MAIN's call, file a note with the numbers).
- [ ] DL-DEPENDABOT: PR #1 (github-actions group, 3 bumps) opened on the first
  push, CI green on it. Never merge a bot PR as-is (operator-only authors):
  apply the same SHA bumps in an operator commit, push at /done, close #1.
