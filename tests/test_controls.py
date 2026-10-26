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
    assert C.conflicts(merged, rec["combat_actions"]) == {}


def test_autoexec_sets_every_checked_controls_cvar():
    rec = C.recommended()
    auto = C.autoexec_cvars(C.AUTOEXEC.read_text(encoding="ascii"))
    for k in rec["convars_checked"]:
        assert k in auto, k
    assert all(k.startswith("citadel_crosshair_") or k in
               {"sensitivity", "sensitivity_y_scale", "zoom_sensitivity_ratio"}
               for k in rec["convars_checked"])


def test_sensitivity_lands_in_the_researched_band():
    rec = C.recommended()
    sens = float(C.autoexec_cvars(C.AUTOEXEC.read_text(encoding="ascii"))["sensitivity"])
    cm = C.cm_per_360(sens, rec["dpi_assumed"])
    assert 35 <= cm <= 60 and cm == rec["cm_per_360"]


def test_cm_per_360_formula():
    assert C.cm_per_360(1.0, 800) == 52.0  # 360 / (0.022 * 800) in = 51.95 cm
