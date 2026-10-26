# Deadlock in-game settings - transcript and recommendation (2026-10-25)

Source: 21 screenshots the operator took of every Settings page on
2026-10-25 21:21-21:25 local (game build 26147187, 2560x1440). The
screenshots are NOT in the repo (they stay on the operator's desktop; they
can show account details). Values below are what the screens showed.

Operator facts: Shadows were changed High -> Med before the screenshots;
the window mode was switched to Borderless Window only to take the
screenshots; the menu has no "particles" and no "anti-aliasing" control.

File mapping: video keys are in `<Steam>/userdata/<id>/1422450/local/cfg/video.txt`
(read with `tools/vw_paths.py`); other settings are cvars in
`user_convars_0_slot0.vcfg` (per account, cloud-synced) or
`machine_convars.vcfg` (per machine) in the same folder. "-" = not located
in those files (keybinds live in the `user_keys_*` / cloud key files; the
reticle values were not found in the local convar files).

## How the keys were confirmed

Diff of `video.txt`: the copy the tool applied at 21:04 (backup
`ops/runtime/backup/20261025-210458/` + the 10 applied keys) against the
file the running game wrote at 21:27:30:
- `setting.r_citadel_shadow_quality` 2 -> 1: the operator's High -> Med, so
  Low 0 / Med 1 / High 2 / Ultra 3.
- `setting.fullscreen_min_on_focus_loss` 1 -> 0: menu "Minimize on focus loss" Off.
- `setting.monitor_index` 0 and `setting.aspectratiomode` 0 were added
  (the Display page was touched: Monitor 1, 16x9).
- Every key `tools/vw_video.py` set earlier still holds its value
  (`vw_video.py check`: nothing to change), including `setting.fullscreen` 1
  / `setting.nowindowborder` 0 (exclusive fullscreen). The file was written
  after the last screenshot, so either the mode was switched back before
  21:27 or the game writes the borderless choice later (on exit). The
  menu is the authority: it must read Fullscreen.
`user_convars_0_slot0.vcfg` and `machine_convars.vcfg` show no setting
change since the first launch (only the settings menu's own scroll state).

## Video

Display
| Setting | Current | Options seen | Key | Recommended |
|---|---|---|---|---|
| Display | Monitor 1 (the 240 Hz panel) | monitor list | `setting.monitor_index` 0 | keep |
| Custom resolution | On | toggle | - | keep |
| Aspect ratio | 16x9 | 16x9, 16x10, 21x9 | `setting.aspectratiomode` 0 | keep |
| Resolution | 2560x1440 (240 Hz) | list | `setting.defaultres` / `defaultresheight`, `refreshrate_numerator/denominator` 240/1 | keep |
| Window mode | Borderless Window (for the screenshots) | dropdown (not opened) | `setting.fullscreen` + `setting.nowindowborder` (1/0 = Fullscreen, 0/1 = Borderless) | **Fullscreen** (see decision 1) |

Performance (Advanced settings: On, `setting.useadvanced` 1)
| Setting | Current | Options seen | Key | Recommended |
|---|---|---|---|---|
| Upscaling technology | NVIDIA DLSS | Stretch, FSR, FSR2 (TAA), NVIDIA DLSS | `setting.r_citadel_upscaling` 4 (enum of the others unverified) | keep NVIDIA DLSS (decision 2) |
| Scaling mode | Auto | 1x (DLAA), 1.5x, 1.7x, 2x, Auto | `setting.r_citadel_dlss_settings_mode` 0; render scale `setting.mat_viewportscale` 0.6667 (= 1.5x) | **1.5x** (decision 2) |
| DLSS Model | CNN | CNN, Transformer | `setting.r_dlss_preset` 6 (enum unverified) | **Transformer** (decision 2) |
| Screen space AO | Off | Off, Low, Med, High, Ultra | `setting.r_citadel_ssao_quality` 0 | keep Off |
| Shadow quality | Med | Low, Med, High, Ultra | `setting.r_citadel_shadow_quality` 1 | keep Med |
| Fog quality | High | Low, High | `setting.r_citadel_fog_quality` 1 (Low = 0) | **Low** |
| Texture quality | High | Low, Med, High | - (`setting.gpu_mem_level` 3 is the detected tier) | keep High |
| Post process bloom | Off | toggle | `setting.r_post_bloom` false | keep Off |
| Effects bloom | Off | toggle | `setting.r_effects_bloom` false | keep Off |
| VSync | Off | toggle | `setting.mat_vsync` 0 | keep Off |
| Area lights | On | toggle | `setting.r_arealights` true | **Off** |
| Depth of field | Off | toggle | `setting.r_depth_of_field` false | keep Off |
| In-game maximum FPS | 237 fps | slider | cvar `fps_max` 237 (machine_convars; also in autoexec) | keep 237 |

Options
| Setting | Current | Key | Recommended |
|---|---|---|---|
| Rendering | Direct3D 11 (-dx11) | launch flag / engine choice | keep D3D 11 (decision 3) |
| NVIDIA Reflex | Enabled + Boost | `setting.r_low_latency` 2 | keep |
| NVIDIA G-Sync | Enabled (read only) | - | keep (driver side) |
| Minimize on focus loss | Off | `setting.fullscreen_min_on_focus_loss` 0 | keep Off |
| Preview rendering changes | On | `citadel_preview_video_settings_changes` true | keep |
| Preview duration | 2 s | `citadel_preview_video_settings_duration` 2 | keep |
| Dashboard maximum FPS | 120 fps | `fps_max_ui` 120 | keep |

HUD Telemetry
| Setting | Current | Key | Recommended |
|---|---|---|---|
| Show frame time and FPS | If conditions are poor | `cl_hud_telemetry_frametime_show` 1 | keep; Always while running VW-MEASURE |
| Frame time alert threshold | 100 ms | `cl_hud_telemetry_frametime_poor` 100 | keep |
| Show ping | If conditions are poor | `cl_hud_telemetry_ping_show` 1 | keep |
| Show network problems | If conditions are poor | `cl_hud_telemetry_net_misdelivery_show` 1 | keep |
| Tick miss rate alert threshold | 2% | `cl_hud_telemetry_net_misdelivery_poor` 2 | keep |
| Show jitter | Never | - | keep |
| Show detailed network quality | Never | `cl_hud_telemetry_net_detailed` 0 | keep |

Not in the menu: particle quality (no control and no file key - the
earlier "Particles Low" was wrong) and a separate anti-aliasing control
(AA comes from the upscaler: DLSS/DLAA or FSR2 TAA; Stretch has none). The
file still carries `setting.r_citadel_antialiasing` 1 with no menu control;
it is left alone.

## Game

Shop: Active item slot popup Off; Auto-purchase items Off; Auto-queue build
Off; Only search names Off (`citadel_shop_search_use_name_only`); Immediate
search focus Off (`citadel_shop_open_focus_search` false); Snap scrolling to
price tiers On (`citadel_shop_scroll_snap_to_tiers` true). Recommended: keep.

Interface: Health numbers On (`citadel_unit_status_show_health_value` true);
Ally health numbers Off (`citadel_unit_status_show_ally_health_value`
false); Critical health effects On (`citadel_unit_status_show_critical_state`
true); Name above health bars Player name; Show cumulative damage Off
(`citadel_damage_text_cumulative_mode` 0); Focus game when unpaused On;
Streamer mode Off; Speedometer On (`speedometer_ui_enable` true); Dev command
console On (`con_enable` true, needed for the autoexec echo).
Recommended: keep all.

Reticle: Line width 2 px, Line height 16 px, Line gap 4 px, Line opacity 50%,
Line border 1 px, Line border gap 0 px, Line border opacity 70%, Dot size
4 px, Dot opacity 70%, Dot border 2 px, Dot border gap 0 px, Dot border
opacity 70%, Fill color #FFFFFF, Border color #000000; Themed hero reticles
On; Reticle motion On; Collapse static reticle Off (greyed). Recommended:
keep (personal aim preference; no performance effect).

Camera Settings: Camera FOV 90 (slider maximum; `citadel_camera_hero_fov`
90); Invert mouse Off (`citadel_camera_pitch_inverted` false); Toggle zoom
Off; Reduce camera shake Off (`citadel_reduce_camera_shake` false).
Recommended: FOV 90 keep; **Reduce camera shake On** (steadier aim and
view under fire, no cost).

## Mouse

Cursor size 1x (`citadel_mouse_cursor_scale` 1); Mouse sensitivity 1.25
(`sensitivity`); Y-axis scaling 1 (`sensitivity_y_scale`); Zoom sensitivity
ratio 1 (`zoom_sensitivity_ratio`). Recommended: keep (personal).

## Audio

Volume: Master 100%, Gameplay 100%, Menu music 100%, Voice chat (incoming)
50%. Output: Output device Default Device; Speaker configuration Headphones;
Play sound in background Off (`snd_mute_losefocus` true). Voice: Input
device "No microphone detected"; Mic trigger threshold 0%; Listen to my mic
Off; Streamlined mic Off; Open mic (team) Off; Open mic (party) Off.
Recommended: keep (Headphones is the right mode for positional audio).

## Communication

Permissions (all checked): Party members Text/Voice/Pings; Allies
Text/Voice/Pings; Opponents Text; Spectated players Text/Pings; Text filter
-> Open Steam Settings. Chat Wheel: Slot 1 Going In, Slot 2 Need Help!,
Slot 3 Thanks, Slot 4 What's the plan?, Contextual Slot 5 On (Slot 5 Good
Job! greyed), Slot 6 Retreat, Slot 7 Heading to lane, Slot 8 Stay Together
(`ping_wheel_phrase_0..7`); HUD ping indicator On
(`player_ping_indicator_enabled`). Recommended: keep.

## Keybinds (all current; recommended: keep, personal)

Abilities: Casting mode Ability Default; Ability 1-4 = 1, 2, 3, 4; Cancel
ability SPACE; Cancel with ability key Off; Upgrade ability 1-4 = ALT+1..4;
Alternate cast mode Alternate Cast Button; Alternate cast = a mouse button.
Items: Active item casting Item Default; Item 1-4 = Z, X, C, V.
Movement: W/S/A/D; Jump/mantle SPACE; Zipline/rope SPACE; Dash SHIFT;
Crouch/slide CTRL; Toggle crouch/toggle slide unbound; Down dash unbound;
Fly up SHIFT; Fly down CTRL.
Combat: Fire left mouse; Zoom/alt-fire right mouse; Reload R; Melee Q;
Melee parry/throw held item F.
In-Game Menus: Open shop B; Interact E; Purchase quickbuy G; HUD detail view
TAB; Extra info ALT; Avoid hero = a mouse button.
Communication: Chat (all) SHIFT+ENTER; Chat (team) ENTER; In-world ping
unbound; In-world ping (long hold) chat wheel = a mouse button, Wheel delay
0.23 s (`citadel_show_chat_wheel_time`); Chat wheel unbound; Quick ping 1
unbound (phrase Going In).
Audio: Toggle mute unbound; Voice chat (team) T; Voice chat (party) unbound.
Miscellaneous: Pause P; Teammate 1-5 camera F1-F5; Cosmetic 5; Reset camera
unbound; Dev console F7.
Hideout: Show recent news N; Cancel matchmaking C; Accept request Z; Reject
request X; Move Hideout camera in / out = mouse wheel up / down.
Shop: Buy/sell search result ENTER; Search items BACKSPACE; Builds /
Popular / All Items / Weapon / Spirit / Vitality tab = 1-6; Scroll up / down
= arrow up / down.
Spectator/Replay: Spectate next / prev target = left / right mouse; Switch
teams SPACE; Camera mode C; Fly up SHIFT; Fly down CTRL; Spectate in-eye /
chase cam = wheel up / down; Toggle free cursor J; Dual-team minimap F1;
Target's minimap F2; Hidden King minimap F3; Archmother minimap F4;
Spectate player 1-12 = 1-9, 0, -, =.
Replay-Specific: Increase replay speed =; Decrease replay speed -; Pause
replay P.

## Controller, Language, Accessibility, Advanced

Controller: not detected; Button prompts Automatic; Universal controller
glyphs On. Language: In-game text English; Alternate hero build language
None (`citadel_secondary_language_builds` -1). Accessibility: Show
subtitles Off (sub-options all checked, greyed); Custom subtitles Off;
Custom UI colors Off; Reduce flashing effects Off; Auto-fire, Auto-move,
Auto-mantle forwards / backwards / in air all Off
(`cl_citadel_auto_*` false). Advanced: Hero-specific settings Off
(`citadel_hero_specific_settings_enabled` false); Spectator & Replay
Camera: Follow spectated player's view On; viewed hero close-up opacity
41%, fade start 50, full-fade 20; other unit close-up opacity 40%, fade
start 100, full-fade 20; Custom spectator camera Off; pivot forward / side
0 / 0, height 86; crouching pivot forward / side 0 / 0, height 55; camera
forward / side / vertical -135 / -34 / 0; near-wall -10 / -10 / 10; zoomed
-110 / -34 / 0; field of view 90; zoomed field of view 45.
Recommended: keep all (no performance or latency effect; Reduce flashing
effects stays the operator's choice).

## Decisions (decision, alternatives, why, what reverses it)

1. Window mode: **Fullscreen (exclusive)**. Alternatives: Borderless Window;
   Windowed. Why: Deadlock renders through D3D 11 here, and fullscreen
   optimizations are OFF for deadlock.exe (docs/optimization.md change 3),
   so a borderless window is composed by DWM instead of flipped straight
   to the screen: about a frame more latency at 240 Hz, and G-Sync only
   works in it if the driver is set to windowed G-Sync. Exclusive
   fullscreen gives direct scan-out, G-Sync in the driver's default mode
   and the lowest latency with Reflex + Boost and the 237 cap. Borderless
   with fullscreen optimizations back on can be promoted to independent
   flip and come close, but that promotion silently drops when an overlay
   draws on top. Reverses: alt-tab trouble that costs more than the
   latency (then Borderless and remove the Layers flag together).
2. Upscaler: **NVIDIA DLSS, Scaling mode 1.5x (Quality), DLSS Model
   Transformer**. Alternatives: native without AA (Stretch at full
   resolution: shimmering edges, no AA control exists to fix it); DLAA
   (1x: sharpest, but costs the GPU headroom that keeps the 237 cap in
   big fights); FSR / FSR2 (softer than DLSS on an RTX card); Auto (picks
   1.5x at 1440p today - the file shows render scale 0.6667 - but can
   change silently, which would confound VW-MEASURE). Transformer over CNN:
   clearer in motion and less ghosting; RTX 50 tensor cores run it at
   little cost. Why: Deadlock is CPU-bound on a 7700X in fights; DLSS
   Quality keeps the RTX 5070 below full load so frames are cap-limited,
   which is where Reflex gives the lowest latency. Reverses: VW-MEASURE
   showing 1 percent lows >= 200 fps at 1x (DLAA) - then DLAA.
   The earlier recommendation "Upscaling Off (native)" was wrong: there
   is no Off, and native means no anti-aliasing.
3. Rendering API: keep **Direct3D 11**. Alternative: Vulkan (offered by
   the game). Why: D3D 11 is the game's default and is what Reflex + Boost
   and the measured baseline use; Vulkan is a separate VW-MEASURE item, not
   a blind switch. Reverses: a measured win for Vulkan in 1 percent lows.
4. Fog Low and Area lights Off: both cost GPU time and add haze or light
   glare that lowers target clarity; neither affects gameplay information.
   Reverses: a measured gain under 2 percent and a visible loss of depth
   cues the operator dislikes.
5. Shadows Med (operator's choice, kept): Low drops shadows that show enemy
   positions around corners; High/Ultra cost GPU for no competitive gain.
6. Particles and anti-aliasing: removed from the recommendation (no such
   menu controls; AA is decision 2).

## Read-back 2026-10-25 21:44 (operator: "those 6 settings are set")

Game and Steam closed; files the game wrote at 21:44, diffed against the
21:04 and 21:37 backups.
| Menu change | File value | Confirmed |
|---|---|---|
| Window mode Fullscreen | `setting.fullscreen` 1, `setting.nowindowborder` 1 | yes (see note) |
| Scaling mode 1.5x | `setting.r_citadel_dlss_settings_mode` 0 -> 3, `setting.mat_viewportscale` 0.666667 | yes |
| DLSS Model Transformer | `setting.r_dlss_preset` 6 -> 10 | yes |
| Fog quality Low | `setting.r_citadel_fog_quality` 0 | yes |
| Area lights Off | `setting.r_arealights` false | yes |
| Reduce camera shake On | `citadel_reduce_camera_shake` false -> true (user convars, local and cloud) | yes |

Note: first launch wrote Borderless as 0 / 1; switching back from Borderless
to Fullscreen set `fullscreen` 1 and left `nowindowborder` 1. `vw_video.py
apply` (21:46, backup under `ops/runtime/backup/`) set `nowindowborder` 0,
the documented exclusive-fullscreen pair 1 / 0; read back, check: no change
left. Enum values learned once (1.5x = 3, Transformer = 10); they stay
MENU_ONLY until a second read confirms them.
Keybinds and casting modes: not changed (keys file unchanged since 21:00;
casting keys and convars identical to the 21:37 backup). Sensitivity 1.1 is
saved.
