# Deadlock controls - learning sheet

Researched 2026-10-25 (sources at the end). Machine-readable copy:
`config/controls.recommended.json`; sensitivity is applied by
`config/autoexec.cfg`, the reticle in the menu; `python tools/vw_controls.py
check` reads back what the game holds.

## Final state (read back 2026-10-25 23:16, game closed)

`vw_controls.py check`: bind_changes_left, conflicts_now, conflicts_after,
convars_not_yet_saved and reticle_changes_left all empty;
`hidden_accepted` Cosmetic1 5,E.
- Sensitivity 1.6 at 1200 DPI (eDPI 1920, 21.6 cm/360), set by
  `config/autoexec.cfg`; game copy sha256 a38b0d66aec5 = repo copy
  (reticle-free autoexec, applied 23:16, previous copy e6fe29bc57d9 in
  `ops/runtime/backup/20261025-231622/`).
- Reticle: the 13 rows below, set by the operator in the menu; read back
  from the hero-settings `base` block (cyan 0/255/255, pip 2 x 8, gap 3,
  opacity 1, border 1 at 0.8, dot 2 at 1, dot border 1 at 0.8).
- Binds: Melee MOUSE5, Item 1 Q, Item 4 E, Interact V, Ping MOUSE4, menu
  "Cosmetic" row (`CosmeticMenu`) 5; everything else default.
- Cosmetic1 keeps E (and 5): a hidden legacy/default action the menu does
  not show and cannot clear. The operator verified 2026-10-25 that E with
  an empty item slot 4 fires nothing, so it is accepted: listed under
  `accepted_hidden` in `config/controls.recommended.json`, reported as
  `hidden_accepted`, never as a conflict. Reverses: E firing a cosmetic in
  a match.
- Casting (Quick Cast, Press and Hold 0.15, Instant Cast items): menu-only;
  no file confirms it - `cl_citadel_quickcast_ability1-4` and
  `cl_citadel_items_quickcast_mode` read 0, unchanged since 21:37 (enum
  unverified), alt-cast hold time 0.15 (= default). ROADMAP VW-CASTING.

## Keybinds

Only six rows change from the game default (all read back, see Final
state). History of the Cosmetic finding:
Cosmetic, re-read 2026-10-25 22:36 (game closed 22:31): the operator's menu
shows Cosmetic on 5 only, but the keys file (last written 21:52, cloud-synced,
not rewritten at the 22:31 close) still holds `Cosmetic1` Key `E`, Key2 `5`
- so E is live on both Item 4 and Cosmetic (`conflicts_now`). The menu label
"Cosmetic" is `Cosmetic1` (localization `citadel_keybind_cosmetic1`; the
separate `CosmeticMenu` action holds 5). The "stale until the
next close" theory is FALSIFIED (2026-10-25 23:01): the game rewrote the
keys file at 23:00:34 while running and it still holds `Cosmetic1` E / 5;
`CosmeticMenu` holds 5 / NONE. The menu row "Cosmetic" (Keybinds >
Miscellaneous, screenshot 23:0x) shows one key, 5 - that matches
`CosmeticMenu`, so that row is probably not `Cosmetic1` (the localization
reading above is unconfirmed). Resolved 2026-10-25: no menu row shows E (the row is `CosmeticMenu`), the
cloud file stays unedited (floor), and the operator tested E with an empty
item slot 4: nothing fires. `Cosmetic1` E is accepted (Final state); the
check target is `CosmeticMenu` 5.
Set them in Settings > Keybinds (the game keeps binds in a Steam cloud file this
repo may not edit, so the menu is the apply path; `vw_controls.py check` then
shows `bind_changes_left` empty).

| Key | Action | Change | Why |
|---|---|---|---|
| 1 2 3 4 | Abilities 1-4 | default | universal; ALT+1-4 upgrades stay |
| SPACE | Jump / mantle, cancel ability | default | every guide keeps it |
| SHIFT | Dash | default | thumb-free pinky key; dash-jump = SHIFT then SPACE |
| CTRL | Crouch / slide | default | slide is held while moving |
| Q | Item 1 | was Z | Z is a pinky stretch; Q is the closest free key (pro layout, MikaelS) |
| X | Item 2 | default | |
| C | Item 3 | default | |
| E | Item 4 | was V | E is under the middle finger (Dexerto 2026 and MikaelS) |
| V | Interact | was E | E now holds Item 4 |
| MOUSE5 | Melee (hold = heavy) | was Q | melee mid-spray without leaving WASD (Dexerto, MikaelS) |
| F | Parry / throw held item | default | every source keeps parry on F |
| MOUSE3 | Alternate cast (self cast) | default | |
| MOUSE4 | Ping | was MOUSE3 | default shared MOUSE3 with alt cast |
| 5 | Cosmetic (`CosmeticMenu`) | default | hidden `Cosmetic1` keeps E, verified harmless (Final state) |
| R, TAB, B, G, T, Y | reload, scoreboard, hero sheet, quickbuy, push-to-talk, chat wheel | default | |

Menu-only (no verified cvar values, set by hand):
- Keybinds > Abilities > Casting mode: Quick Cast; Alternate cast mode: Press
  and Hold (hold time 0.15). Items > Active item casting: Instant Cast.
  DISPUTED: Dexerto (2026-07) recommends Quick Cast; the official forum
  reports a few abilities misbehave on it (inputs not buffered during the
  global cooldown). If an ability feels wrong, set that ability back to
  default under Advanced > Hero-Specific Settings.
- Keep "Cancel with ability key" off.

## Sensitivity

- Mouse: Rapique R110 (tri-mode 2.4G / BT1 / BT2; Windows shows a generic
  "2.4G Wireless Receiver"). DPI button cycles 800 -> 1200 -> 1600 (Newegg
  and Fravega listings, TurboVS review; 125 Hz polling). The default step
  and any per-step LED are NOT documented in any source found. SET
  2026-10-25 22:36: the operator says the mouse is on step 2 of 3 = 1200 DPI
  (their call over the inconsistent measurements below) -> sensitivity 1.6,
  same eDPI 1920 and 21.6 cm/360. sensitivity = 1920 / DPI:
  800 -> 2.4, 1200 -> 1.6, 1600 -> 1.2.
- Check the step (2 min, read only): ruler on the pad, run
  `python tools/vw_dpi.py measure` (raw input, so Enhance pointer precision
  does not matter), slide the mouse 10 cm straight right, wait 20 s. It
  prints `nearest_step` and the sensitivity for it. If it is not 800, either
  press the DPI button until a re-run reads 800, or change `sensitivity` in
  `config/autoexec.cfg` to the printed value and re-apply (game closed).
- Measured 2026-10-25 (two 45 s runs, 10 cm slide): counts_x 1337 and 1509
  (counts_y -771 and -2617, so the slides were not straight) -> 340 and 383
  DPI, nearest step 800 both times -> sensitivity 2.4 kept (no change;
  game autoexec.cfg already equal to the repo copy, sha256 570f5bd2c55d).
  Both readings are under half of the lowest documented step: either the
  slide was short or the R110 has an undocumented ~400 step. Re-measure
  with a slower, straighter slide before trusting 800; at 400 the same
  eDPI needs sensitivity 4.8.
- Re-measured 2026-10-25 (third run, 45 s, ruler-guided 10 cm slide, mouse
  held square to the ruler): counts_x 2233, counts_y -2211 (455 events).
  DPI by x alone 567 (no step within 15 percent); DPI by total distance
  sqrt(x^2+y^2) = 3142 counts -> 798, within 0.3 percent of the 800 step.
  The equal x and y say the sensor axis sits about 45 degrees off the shell
  axis, so the total distance is the measure to trust (x alone undercounts;
  this also explains the two low earlier readings). Step 800 confirmed ->
  sensitivity 2.4 kept; no config change, nothing applied.
- A fourth run read 1617 DPI by total distance (nearest step 1600). With
  798 and 1617 disagreeing, the operator ruled step 2 = 1200 (2026-10-25).
  Applied 22:36, game closed: `config/autoexec.cfg` sensitivity 1.6 copied
  to the game by `tools/Apply-DeadlockConfig.ps1 -SkipRegistry
  -SkipLaunchOptions`; game copy read back sha256 e6fe29bc57d9 = repo copy;
  previous game copy (570f5bd2c55d, sens 2.4) in
  `ops/runtime/backup/20261025-223622/`. If aim feels 1.5x slow the mouse is
  on 800 (press the DPI button once); 0.75x fast = 1600.
- Read back 2026-10-25 23:01 (game running since 22:58 with `+exec
  autoexec`): `user_convars` sensitivity 1.5999999 and hero-settings `base`
  mouse_sensitivity 1.5999999 - 1.6 is live. The DPI (1200) is the
  operator's ruling, not measured.
- In-game Mouse sensitivity 1.6 at 1200 DPI (2.4 at 800 until 2026-10-25
  22:36; was 1.25; 1.1 for a few minutes on 2026-10-25 before the pad was
  measured), Y-axis scaling 1, Zoom
  sensitivity ratio 1.
- eDPI 1920 (1200 x 1.6). cm/360 = 360 / (0.022 x 1.6 x 1200) inch = 21.6 cm;
  a 180 = 10.8 cm. Deadlock uses the Source yaw 0.022 (the game saves
  `m_yaw 0.022`), so Deadlock sens = CS2 sens at the same DPI.
- Why 21.6 cm (pad-limited): the usable pad area right of the keyboard is
  about 22 cm wide x 30 cm deep (photo 2026-10-25, scaled by a US banknote,
  15.6 cm wide: ~50 px/cm; the pad runs on under the keyboard but that part
  is unusable; perspective error about +-2 cm). Rule: a 180 must fit in
  half the usable width with room to recentre, a 360 within the width. The
  researched 47 cm/360 (top players 640-880 eDPI: MikaelS 640, shroud 880)
  needs 23.6 cm for a 180 - more than the whole usable width - so the
  sensitivity was raised to the lowest value that fits: 360 in <= 22 cm ->
  sens 2.36, rounded to 2.4 (21.6 cm). That sits inside the converter band
  for this game (20-80 cm/360) but above the pro eDPI range; it is a wrist
  aim setting. A wider pad (e.g. 45 cm or more of free width) would allow
  going back toward 47 cm (sens 1.1). Keep it a full week before changing.
- Raw input: Deadlock reads raw mouse input (no in-game accel option).
  Windows "Enhance pointer precision" is ON on this PC; it only affects the
  desktop and menus. Turning it off (Settings > Mouse > Additional mouse
  options > Pointer Options) makes the menu cursor feel the same as aim.

## Reticle (Settings > Game > Reticle)

Set BY HAND in the menu (13 rows below; done 2026-10-25, read back empty
`reticle_changes_left`). Why not the autoexec (finding 2026-10-25 23:01):
the game launched 22:58 with `+exec autoexec` (process command line) and the
autoexec's sensitivity 1.6 landed, but the Reticle page (screenshot) showed
every row at default. The reticle is stored in the cloud file
`<Steam>/userdata/<id>/1422450/remote/cfg/citadel_hero_settings.lst`, block
`base` (`crosshair_*` keys, plus `mouse_sensitivity`), and the game pushes
that block over the `citadel_crosshair_*` cvars; those cvars are not saved
in `user_convars`. The cvar names themselves are valid (deadlock.wiki
Data:Convars.json lists all 13), so this is an override, not a name error.
The cloud file is read only for this repo (floor), so the 13 cvar lines
were dropped from `config/autoexec.cfg`; sensitivity stays there (the game
mirrors it into `base`).

| Row | Value | Default |
|---|---|---|
| Fill color | cyan #00FFFF (0,255,255) | white |
| Line width | 2 px | 2 |
| Line height | 8 px | 16 |
| Line gap | 3 px | 4 |
| Line opacity | 100% | 50% |
| Line border | 1 px, opacity 80%, black | 1 px, 70% |
| Dot size | 2 px | 4 |
| Dot opacity | 100% | 70% |
| Dot border | 1 px, opacity 80% | 2 px, 70% |

Why: every current guide says high-contrast color (cyan, green or pink), a
small centre, a thin dark outline and full opacity; the default is a 50 %
white cross that vanishes on bright skies. Themed hero reticles stay on (they
show the hero's ammo and charge state).

## Other settings worth keeping

Already set: FOV 90 (maximum), Speedometer on, Health numbers on, Reduce
camera shake on (video pass), hit marker 0.1 s (default). Leave "Show
cumulative damage" Off while learning so every hit shows its own number.

## One-week practice plan (15-20 min before playing)

- Day 1-2: Sandbox (Play > Sandbox). Movement only: dash-jump (SHIFT then
  SPACE), slide (CTRL while running) into dash, mantle chains. Then 20 parries:
  have a bot melee you and press F on the wind-up.
- Day 3-4: Sandbox with a hitscan hero. Track a strafing bot at mid range for
  5 x 1 minute; reload with R between rounds. Melee on MOUSE5 after every
  clip (light then heavy hold).
- Day 5: items. Buy a defensive active, fire it from Q/E while dashing; use
  MOUSE4 ping on every enemy you see.
- Day 6-7: Practice vs bots, one hero, full match. Last-hit troopers with
  gun + melee, call targets with MOUSE4.
Change sensitivity only after day 7, by 10 percent at most.

## Rollback

1. Sensitivity and reticle: remove the "Controls" block from
   `config/autoexec.cfg` and re-run `tools/Apply-DeadlockConfig.ps1`
   (game closed); then restore the old values in the menu (sensitivity 1.25,
   reticle reset arrow) - or, with the game closed, copy the backups in
   `ops/runtime/backup/20261025-213740-controls/` back (game autoexec, local and
   cloud convars, keys files; SHA256SUMS inside). Sensitivity 1.6 -> 2.4
   only: copy `ops/runtime/backup/20261025-223622/autoexec.cfg` back (game
   closed) and revert `sensitivity` in the repo copy.
2. Keybinds: Settings > Keybinds > reset (circular arrow), or rebind the six
   rows above to their old keys. The original cloud file is backed up in
   `ops/runtime/backup/20261025-210408-firstlaunch/remote/cfg/`.

## Sources (fetched 2026-10-25)

- deadlock.wiki Data:Convars.json and Console page (edited 2026-10-18):
  citadel_crosshair_* names and defaults (pip_width 2, pip_height 16,
  pip_gap 4, pip_opacity 0.5, dot_size 4 ...), matching the menu.
- Valve Developer Community, List of Deadlock console commands (build of
  2026-04).
- ProSettings.net, MikaelS (updated 2025-03-26): 800 DPI, sens 0.8, items
  Q/X/C/E, melee MOUSE5, parry F, self cast MOUSE3, cyan-green reticle.
- Dexerto, best Deadlock keyboard and mouse settings (updated 2026-07-15):
  items Z/X/C/E, Quick Cast, Press and Hold 0.15, Instant Cast items.
- metabot.gg, best Deadlock settings (updated 2026-10-15): clutch active on a
  side button, high-contrast small reticle, keep a sens for a week.
- Rapique R110 DPI steps (fetched 2026-10-25): Newegg listing ("800-1200-1600
  3-level DPI", DPI button), Fravega listing (tri-mode, 800/1200/1600),
  TurboVS review (125 Hz, dedicated DPI button). No manual found.
- Sportskeeda, shroud's settings (2024): 800 DPI, sens 1.1.
- mouse-sensitivity.com Deadlock converter: 20-80 cm/360 band; csdb.gg:
  Deadlock yaw 0.022 (same as CS2). DISPUTED: recharge.com claims 0.044; the
  game's own saved m_yaw is 0.022, so 0.022 is used. Verify once: one full
  21.6 cm swipe should turn exactly 360 degrees.
- Dexerto crosshairs (2024-09, early access): negative pip_gap closes the gap,
  dot slightly off-centre at some sizes - may be outdated.
- playdeadlock forums: Quick Cast buffering and "Ability Default" threads.
