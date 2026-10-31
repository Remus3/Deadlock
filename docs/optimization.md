# Deadlock optimization - what is set, why, and how to undo it

Machine (read 2026-10-25 from the supervisor's hardware scan): AMD Ryzen 7 7700X
(8 cores / 16 threads), 32 GB DDR5 (5200 MT/s configured), NVIDIA GeForce RTX
5070 (12 GB), one 2560x1440 display at 240 Hz, Windows 10 Pro 22H2, power plan
Balanced. Deadlock build 26147187, installed the same day; Steam cloud
supplied the player's own `user_convars.vcfg` and `user_keys.vcfg`. First
launched by the operator the same evening to create the video file.

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

## Applied 2026-10-25, after the first launch (game NOT running, Steam NOT running)

The operator launched the game once and changed a few settings to make it write
its files. Raw copies of every generated file (local `video.txt`,
`machine_convars.vcfg`, `user_convars_0_slot0.vcfg`, `user_keys_*`, the cloud
`remote/` files and the game cfg `autoexec.cfg`, `boot.vcfg`,
`citadel_hero_settings.lst`), with a `SHA256SUMS` list, are in
`ops/runtime/backup/20261025-210408-firstlaunch/` (gitignored, unscrubbed).

The video file is per Steam account, not in the install:
`<Steam>/userdata/<id>/1422450/local/cfg/video.txt` (format "video.cfg",
Version 20). `tools/vw_paths.py` now finds it there and redacts the account id.

| # | Change | Read back |
|---|---|---|
| 4 | `video.txt`, 10 keys (below), by `python tools/vw_video.py apply`; backup `ops/runtime/backup/20261025-210458/video.txt` | file re-read: all 10 keys hold the new value (`readback_bad` empty), `check` then shows nothing left to change; CRLF kept |
| 5 | Steam `localconfig.vdf` apps/1422450 `LaunchOptions` = `+exec autoexec` (no value before), by `python tools/vw_launch.py apply`; backup `ops/runtime/backup/20261025-210507/localconfig-0.vdf` | `vw_launch.py check` current == wanted; diff against the backup is that one added line, inside the 1422450 block |
| 1 | autoexec (unchanged since the rename) | game copy SHA-256 == repo copy `c15f9421bb979b8b...` |

Video keys, operator's first-launch value -> applied value:
- `setting.fullscreen` 0 -> 1 and `setting.nowindowborder` 1 -> 0 (borderless
  window -> exclusive fullscreen)
- `setting.refreshrate_numerator` / `_denominator` 0/0 (desktop default) ->
  240/1 (the display runs exactly 240 Hz)
- `setting.r_low_latency` 1 -> 2 (Reflex On -> On + Boost)
- `setting.r_citadel_ssao_quality` 3 -> 0 (ambient occlusion off)
- `setting.r_citadel_motion_blur` 1 -> 0
- `setting.r_depth_of_field` true -> false
- `setting.r_effects_bloom` true -> false, `setting.r_post_bloom` true -> false

Unchanged (already as recommended): 2560x1440, `mat_vsync` 0.

Menu transcript 2026-10-25 (21 screenshots of every Settings page, game
running; `docs/menu-settings-2026-10-25.md`): the game has NO particle
quality and NO separate anti-aliasing control (AA comes from the upscaler),
so the earlier "Particles Low" and "Anti-Aliasing" lines were dropped.
Decisions recorded there: exclusive Fullscreen 240 Hz (not Borderless; operator
choice 2026-10-26, borderless was only for screenshots; applied and read back
2026-10-26), NVIDIA DLSS
at 1.5x (Quality, pinned instead of Auto) with the Transformer model, Fog
Low, Area lights Off, Shadows Med (the operator's change, `video.txt`
`r_citadel_shadow_quality` 2 -> 1), Reduce camera shake On. Three keys
joined "keys" (`r_citadel_shadow_quality` 1, `r_citadel_fog_quality` 0,
`r_arealights` false); the upscaler keys stay menu-only (`tools/vw_video.py`
MENU_ONLY refuses them). Not applied by file: the game was running
(`vw_video.py check` would change fog 1 -> 0 and area lights true -> false);
the menu changes are ROADMAP VW-VIDEO-MENU.

Observed: after the first launch `machine_convars.vcfg` already held the
autoexec values (`fps_max 237`, `fps_max_ui 120`, `rate 786432`,
`con_enable true`), none of which were in the pre-launch cloud
`user_convars.vcfg` - the game appears to have run `autoexec.cfg` even before
the launch option was set. VW-AUTOEXEC-VERIFY confirms with the console echo.

## Applied 2026-10-25, controls (game NOT running)

| # | Change | Read back |
|---|---|---|
| 6 | `config/autoexec.cfg` gains the controls block (sensitivity 1.1, reticle cvars; `docs/controls.md`), copied to the game cfg; backup of the game autoexec, local and cloud convars and key files in `ops/runtime/backup/20261025-213740-controls/` (SHA256SUMS) | game copy SHA-256 == repo copy `617b53d2345d360f...` |
| 7 | 21:58: `sensitivity` 1.1 -> 2.4 (pad-limited, 21.6 cm/360; `docs/controls.md`), copied to the game cfg; backup of the previous game autoexec in `ops/runtime/backup/20261025-215845-sens/` | game copy SHA-256 == repo copy `570f5bd2c55d00e0...` |

Keybinds are not written by any tool (Steam cloud file); `docs/controls.md`.

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
- Video (recommended): latency first (exclusive fullscreen, Reflex On +
  Boost, V-Sync off, DLSS Quality so the GPU keeps headroom under the 237
  cap), then readability (no AO, motion blur, bloom, depth of field; fog
  low, area lights off), then quality where the 12 GB card has room
  (textures high). Reasons per setting: `docs/menu-settings-2026-10-25.md`.

Not changed, by operator choice: Windows Game Mode (stays off), Windows 10
(stays). Not changed, out of scope here: the power plan (Balanced; the 7700X
boosts fine on it) and the NVIDIA driver profile.

## Cvar flag check (VW-CVAR-CHECK, 2026-10-31)

`python tools/vw_cvar_check.py check --live` lists every statement of the repo
autoexec (and, read only, the game copy) as `ok`, `cheat`, `devonly`,
`unknown` or `command`, and exits 1 when a cheat or development-only cvar is
present. Flag source: the community API cvar list for the current patch
(`vw_cvar_check.py fetch`, cached in the gitignored
`ops/runtime/gamedata/raw/`), plus any `cvarlist` dump passed with `--dump`.

Result at patch 6836 (repo copy == game copy, SHA-256 `a38b0d66aec57179...`):
0 cheat, 0 devonly; `sensitivity`, `sensitivity_y_scale`,
`zoom_sensitivity_ratio` ok; `echo` a command; `con_enable`, `fps_max`,
`fps_max_ui`, `rate`, `engine_low_latency_sleep_after_client_tick` unknown,
because the API list carries only the client and server dll cvars, not the
engine's. Nothing removed; the game file was not written.

To close the unknowns (ROADMAP VW-CVAR-DUMP): in game, open the console (F7
with `con_enable true`), run `cvarlist`, copy the output into
`ops/runtime/cvarlist.txt` (gitignored; lines `name : value : flags : help`),
then run `python tools/vw_cvar_check.py check --live --dump
ops/runtime/cvarlist.txt`. A dump line whose flags carry `cheat` or `dev` is
flagged. If the console will not copy, try `con_logfile` before `cvarlist`
(not yet confirmed to exist in Deadlock). A flagged cvar is removed from
`config/autoexec.cfg`, recorded here, and re-applied with the game closed.

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
4. Launch options: with Steam closed, copy
   `ops/runtime/backup/20261025-210507/localconfig-0.vdf` back over
   `<Steam>/userdata/<id>/config/localconfig.vdf`, or clear the field in Steam
   (Library > Deadlock > Properties > General > Launch Options).
5. Video: with the game closed, copy
   `ops/runtime/backup/20261025-210458/video.txt` back over
   `<Steam>/userdata/<id>/1422450/local/cfg/video.txt` (that is the operator's
   first-launch file; the same file is also in `20261025-210408-firstlaunch/local/`),
   or change the values in the in-game menu.
Full restore of both registry keys: import the `.reg` files from
`ops/runtime/backup/20261025-baseline/`.

## Re-apply

`powershell -NoProfile -ExecutionPolicy Bypass -File tools\Apply-DeadlockConfig.ps1`
(`-WhatIf` to preview, `-SkipRegistry`, `-SkipLaunchOptions`). It refuses while
the game runs, backs up every file and key it touches, and reads each change
back.
