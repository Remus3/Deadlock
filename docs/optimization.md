# Deadlock optimization - what is set, why, and how to undo it

Machine (read 2026-10-25 from the supervisor's hardware scan): AMD Ryzen 7 7700X
(8 cores / 16 threads), 32 GB DDR5 (5200 MT/s configured), NVIDIA GeForce RTX
5070 (12 GB), one 2560x1440 display at 240 Hz, Windows 10 Pro 22H2, power plan
Balanced. Deadlock build 26147187, installed the same day and never launched
(no video settings file exists yet; Steam cloud supplied the player's own
`user_convars.vcfg` and `user_keys.vcfg`).

Placeholders: `<Steam>` = the Steam install, `<Deadlock>` = the game install
(`<library>/steamapps/common/Deadlock`). `tools/vw_paths.py` resolves both.

## Applied 2026-10-25 (game and Steam state at the time: game NOT running, Steam running)

Each change was made alone, after its backup, and read back.

| # | Change | Read back |
|---|---|---|
| 1 | `<Deadlock>/game/citadel/cfg/autoexec.cfg` created from `config/autoexec.cfg` (no file there before) | SHA-256 of game copy equals repo copy (`695804b67a6a1ece...`); re-applied 2026-10-25 after the tree rename (comment and echo tag DL -> VW only; previous game copy backed up to `ops/runtime/backup/20261025-vw-rename/`), game copy = repo copy `c15f9421bb979b8b...` |
| 2 | HKCU `Software\Microsoft\DirectX\UserGpuPreferences`, value `<Deadlock>\game\bin\win64\deadlock.exe` = `GpuPreference=2;` (high performance; no value before) | `reg query` returned `GpuPreference=2;` |
| 3 | HKCU `Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers`, same value name = `~ DISABLEDXMAXIMIZEDWINDOWEDMODE` (fullscreen optimizations off; no value before) | `reg query` returned `~ DISABLEDXMAXIMIZEDWINDOWEDMODE` |

Backups (local, gitignored, unscrubbed): `ops/runtime/backup/20261025-baseline/`
(`UserGpuPreferences.reg`, `Layers.reg`, `user_convars.vcfg`, `user_keys.vcfg`,
`autoexec.absent.txt`). Scrubbed copies of the two cloud config files:
`config/baseline/`.

## Deferred

- **Steam launch options** (`config/launch_options.txt`: `+exec autoexec`).
  Steam was running, and Steam rewrites `localconfig.vdf` on exit, so the file
  was not edited. Either set it in Steam (Library > Deadlock > Properties >
  General > Launch Options: `+exec autoexec`) or, with Steam closed, run
  `python tools/vw_launch.py apply` (backs up, writes only the LaunchOptions
  value of the existing app block, reads back). Until then the autoexec does
  not run. ROADMAP VW-LAUNCH.
- **Video settings.** The game writes its video file on first launch; none
  exists yet. After one launch and exit: `python tools/vw_video.py check`, then
  `apply` (only keys the game already wrote are changed). The menu values that
  cannot be set from the file are in `config/video.recommended.json` "menu".
  ROADMAP VW-VIDEO.

## Why these values

- `fps_max 237`: the display is 240 Hz. With V-Sync off and a variable refresh
  display, a cap a few frames under refresh keeps every frame inside the VRR
  window, and it caps GPU load (lower latency than a GPU-bound frame queue).
  On a fixed-refresh display it costs 3 fps of 240. `fps_max_ui 120` stops the
  menus from running the GPU flat out.
- `rate 786432`: the highest client rate the Source 2 engine accepts; the
  default can throttle updates in big fights.
- `engine_low_latency_sleep_after_client_tick true`: the frame-pacing option
  Source 2 exposes to players; lowers input latency under a frame cap.
- `con_enable true`: the game's own "Enable Console" option, so the autoexec's
  `echo` line can confirm it ran.
- GPU preference 2: tells Windows to use the discrete GPU even if an
  integrated GPU is enabled later (the 7700X has one).
- Fullscreen optimizations off: exclusive fullscreen behaves as exclusive
  fullscreen; often smoother frame pacing in Source titles. Revert if
  alt-tab gets slower or the overlay misbehaves.
- Video (recommended): latency first (Reflex On + Boost, V-Sync off), then
  readability (particles low, no motion blur, bloom, film grain or depth of
  field), then quality where the 12 GB card has room (textures high).

Not changed, by operator choice: Windows Game Mode (stays off), Windows 10
(stays). Not changed, out of scope here: the power plan (Balanced; the 7700X
boosts fine on it) and the NVIDIA driver profile.

## Rollback

1. autoexec: delete `<Deadlock>/game/citadel/cfg/autoexec.cfg` (send it to the
   Recycle Bin); there was none before. Remove `+exec autoexec` from the launch
   options if set.
2. GPU preference:
   `reg delete "HKCU\Software\Microsoft\DirectX\UserGpuPreferences" /v "<Deadlock>\game\bin\win64\deadlock.exe" /f`
   (or Settings > System > Display > Graphics settings > Deadlock > Remove).
3. Fullscreen optimizations:
   `reg delete "HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers" /v "<Deadlock>\game\bin\win64\deadlock.exe" /f`
   (or deadlock.exe > Properties > Compatibility > untick "Disable fullscreen
   optimizations").
4. Launch options: `ops/runtime/backup/<stamp>/localconfig-<n>.vdf` is the copy
   `vw_launch.py apply` made; restore it with Steam closed, or clear the field
   in Steam.
5. Video: `ops/runtime/backup/<stamp>/<video file>` is the copy
   `vw_video.py apply` made; restore it with the game closed.
Full restore of both registry keys: import the `.reg` files from
`ops/runtime/backup/20261025-baseline/`.

## Re-apply

`powershell -NoProfile -ExecutionPolicy Bypass -File tools\Apply-DeadlockConfig.ps1`
(`-WhatIf` to preview, `-SkipRegistry`, `-SkipLaunchOptions`). It refuses while
the game runs, backs up every file and key it touches, and reads each change
back.
