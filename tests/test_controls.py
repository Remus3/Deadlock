"""vw_controls: keybind parsing, the recommended layout, autoexec controls cvars."""
import vw_controls as C

LST = '''"KeyBindings"
{
\t"Name"\t\t"DEFAULT"
\t"Keys"
\t{
\t\t"AbilityMelee"
\t\t{
\t\t\t"Key"\t\t"Q"
\t\t}
\t\t"Item4"
\t\t{
\t\t\t"Key"\t\t"V"
\t\t}
\t\t"AbilityUpgrade1"
\t\t{
\t\t\t"Key"\t\t"1"
\t\t\t"Modifier"\t\t"ALT"
\t\t}
\t\t"Interact"
\t\t{
\t\t\t"Key"\t\t"E"
\t\t\t"Key2"\t\t"NONE"
\t\t}
\t}
}
'''


def test_binds_parse_primary_key_and_modifier():
    b = C.binds(LST)
    assert b == {"AbilityMelee": "Q", "Item4": "V", "AbilityUpgrade1": "ALT+1", "Interact": "E"}


def test_diff_lists_only_differences():
    d = C.diff_binds(C.binds(LST), {"AbilityMelee": "MOUSE5", "Item4": "V"})
    assert d == {"AbilityMelee": ("Q", "MOUSE5")}


def _lst(rows):
    """A citadelkeys text from {action: (Key, Key2)}."""
    body = "".join('\t\t"%s"\n\t\t{\n\t\t\t"Key"\t\t"%s"\n\t\t\t"Key2"\t\t"%s"\n\t\t}\n'
                   % (a, k, k2) for a, (k, k2) in rows.items())
    return '"KeyBindings"\n{\n\t"Keys"\n\t{\n' + body + '\t}\n}\n'


def test_list_target_compares_both_slots():
    # the game file of 2026-10-25 21:52: Cosmetic1 Key E, Key2 5
    text = _lst({"Item4": ("E", "NONE"), "Cosmetic1": ("E", "5")})
    slots = C.key_slots(text)
    assert slots == {"Item4": ["E"], "Cosmetic1": ["5", "E"]}
    want = {"Cosmetic1": ["5"]}
    assert C.diff_binds(C.binds(text), want, slots) == {"Cosmetic1": ("5,E", "5")}
    assert C.conflicts(slots, ["Item4", "Cosmetic1"]) == {"E": ["Item4", "Cosmetic1"]}
    # 5 only, in either slot, is done
    for pair in (("NONE", "5"), ("5", "NONE")):
        done = _lst({"Item4": ("E", "NONE"), "Cosmetic1": pair})
        assert C.diff_binds(C.binds(done), want, C.key_slots(done)) == {}
        assert C.conflicts(C.key_slots(done), ["Item4", "Cosmetic1"]) == {}


def test_hidden_cosmetic1_e_is_accepted_not_flagged():
    # the game file of 2026-10-25 23:00: Cosmetic1 E / 5 (hidden, menu cannot
    # clear it; operator: E with an empty item slot 4 fires nothing),
    # CosmeticMenu 5 = the menu "Cosmetic" row
    rec = C.recommended()
    ok = C._accepted(rec)
    assert ok == {"Cosmetic1": ["E", "5"]}
    assert rec["binds"]["CosmeticMenu"] == "5"
    assert "Cosmetic1" not in rec["binds"]
    text = _lst({"Item4": ("E", "NONE"), "Cosmetic1": ("E", "5"),
                 "CosmeticMenu": ("5", "NONE")})
    slots = C.key_slots(text)
    assert C.conflicts(slots, rec["combat_actions"]) == {"E": ["Item4", "Cosmetic1"]}
    assert C.conflicts(slots, rec["combat_actions"], ok) == {}
    want = {"CosmeticMenu": "5"}
    assert C.diff_binds(C.binds(text), want, slots) == {}
    moved = _lst({"CosmeticMenu": ("NONE", "NONE")})
    assert C.diff_binds(C.binds(moved), want, C.key_slots(moved)) == {"CosmeticMenu": ("NONE", "5")}
    # only the listed (action, key) pairs are exempt
    clash = _lst({"Item4": ("5", "NONE"), "Cosmetic1": ("E", "5")})
    assert C.conflicts(C.key_slots(clash), ["Item4", "Cosmetic1"], ok) == {}
    assert C.conflicts(C.key_slots(clash), ["Item4", "Cosmetic1"], {"Cosmetic1": ["E"]}) == {"5": ["Item4", "Cosmetic1"]}


def test_recommended_layout_has_no_combat_conflicts():
    rec = C.recommended()
    assert C.conflicts(rec["binds"], rec["combat_actions"]) == {}
    # the full default table with the recommendation applied stays conflict free
    defaults = {"AbilityMelee": "Q", "Ability1": "1", "Ability2": "2", "Ability3": "3",
                "Ability4": "4", "Item1": "Z", "Item2": "X", "Item3": "C", "Item4": "V",
                "HeldItem": "F", "Roll": "SHIFT", "Crouch": "CTRL", "Mantle": "SPACE",
                "Reload": "R", "Ping": "MOUSE3", "AltCast": "MOUSE3", "Interact": "E",
                "Cosmetic1": "E", "PurchaseQuickbuy": "G", "PushToTalk": "T",
                "ChatWheel": "Y", "OpenHeroSheet": "B", "Scoreboard": "TAB"}
    merged = dict(defaults, **rec["binds"])
    assert C.conflicts(merged, rec["combat_actions"], C._accepted(rec)) == {}


def test_autoexec_sets_every_checked_controls_cvar():
    rec = C.recommended()
    auto = C.autoexec_cvars(C.AUTOEXEC.read_text(encoding="ascii"))
    for k in rec["convars_checked"]:
        assert k in auto, k
    assert set(rec["convars_checked"]) == {"sensitivity", "sensitivity_y_scale",
                                           "zoom_sensitivity_ratio"}
    # the reticle is not set by cvar: the hero-settings file overrides it
    assert not any(k.startswith("citadel_crosshair_") for k in auto)


HERO = '''<!-- kv3 encoding:text:version{x} format:generic:version{y} -->
{
\tbase =
\t{
\t\tcrosshair_pip_height = "16"
\t\tcrosshair_color_r = "0"
\t\tmouse_sensitivity = "1.5999999"
\t}
\theroes =
\t{
\t}
}
'''


def test_hero_base_and_reticle_diff():
    base = C.hero_base(HERO)
    assert base == {"crosshair_pip_height": "16", "crosshair_color_r": "0",
                    "mouse_sensitivity": "1.5999999"}
    want = {"_README": "x", "crosshair_pip_height": 8, "crosshair_color_r": 0,
            "crosshair_dot_size": 2}
    assert C.diff_reticle(base, want) == {"crosshair_pip_height": "16 -> 8",
                                          "crosshair_dot_size": "default -> 2"}
    assert C.hero_base("{}") == {}


def test_reticle_targets_are_the_documented_cyan_set():
    ret = C.recommended()["reticle"]
    assert (ret["crosshair_color_r"], ret["crosshair_color_g"], ret["crosshair_color_b"]) == (0, 255, 255)
    assert ret["crosshair_pip_height"] == 8 and ret["crosshair_pip_gap"] == 3


def test_sensitivity_in_converter_band_and_fits_the_pad():
    rec = C.recommended()
    sens = float(C.autoexec_cvars(C.AUTOEXEC.read_text(encoding="ascii"))["sensitivity"])
    cm = C.cm_per_360(sens, rec["dpi_assumed"])
    # converter band 20-80 cm/360; a 360 fits the usable pad width (docs/controls.md)
    assert 20 <= cm <= 80 and cm == rec["cm_per_360"]
    assert cm <= rec["usable_pad_cm"][0]


def test_cm_per_360_formula():
    assert C.cm_per_360(1.0, 800) == 52.0  # 360 / (0.022 * 800) in = 51.95 cm
