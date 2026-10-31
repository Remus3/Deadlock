"""vw_combat: E1 stacking rules, pinned against the patch fixture.

Each test_x_* pins one cross-interaction (two or more items, or an item and a
hero, combined by a rule) at client version 6836. A new patch adds a new
fixture and re-pins (R-COACH-3); the rules are cited in
docs/research/hero-data.md.
"""
import json
from pathlib import Path

import pytest

import vw_combat as C
import vw_gamedata as G

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "gamedata" / "vw_gamedata_6836.json"


@pytest.fixture(scope="module")
def data():
    return G.Dataset(json.loads(FIXTURE.read_text(encoding="utf-8")))


# --- rules alone (wiki worked examples) ------------------------------------

def test_resist_stacks_multiplicatively():
    assert C.stack_resist([40, 20]) == pytest.approx(52.0)


def test_reduction_subtracts_after_stacking():
    assert C.final_resist([40, 20], [25, 20]) == pytest.approx(12.0)


def test_fire_rate_bonus_additive_slows_multiplicative_with_floor():
    assert C.fire_rate_modifier([18, 20], [25, 28]) == pytest.approx(-8.0)
    assert C.fire_rate_multiplier([18, 20], [25, 28]) == pytest.approx(1 / 1.08)
    assert C.fire_rate_modifier([], [25, 28, 32]) == pytest.approx(-50.0)


def test_spirit_scaling_is_linear():
    assert C.spirit_damage(65, 0.8, 20) == pytest.approx(81.0)


def test_damage_multiplier_from_resist():
    assert C.damage_taken(30) == pytest.approx(0.7)
    assert C.damage_taken(-30) == pytest.approx(1.3)


# --- cross-interactions pinned at patch 6836 --------------------------------

def test_fixture_is_patch_6836(data):
    assert data.client_version == 6836 and data.schema == G.SCHEMA


def test_x01_metal_skin_plus_battle_vest_bullet_resist(data):
    r = C.stack_resist(data.stat("upgrade_metal_skin", "upgrade_regenerating_bullet_shield",
                                 prop="BulletResist"))
    assert r == pytest.approx(27.84)


def test_x02_three_bullet_resist_items(data):
    r = C.stack_resist(data.stat("upgrade_improved_bullet_armor", "upgrade_metal_skin",
                                 "upgrade_regenerating_bullet_shield", prop="BulletResist"))
    assert r == pytest.approx(53.096)


def test_x03_spirit_resist_emblem_plus_locket(data):
    r = C.stack_resist(data.stat("upgrade_magic_shield", "upgrade_restorative_locket",
                                 prop="TechResist"))
    assert r == pytest.approx(24.56)


def test_x04_two_headshot_shreds_vs_bullet_resilience(data):
    resist = data.stat("upgrade_improved_bullet_armor", prop="BulletResist")
    shred = data.stat("upgrade_headshot_booster2", "upgrade_banshee_slugs",
                      prop="BulletResistReduction", conditional=True)
    final = C.final_resist(resist, [abs(s) for s in shred])
    assert final == pytest.approx(8.92)
    assert C.damage_taken(final) == pytest.approx(0.9108)


def test_x05_shred_on_unarmored_target_goes_negative(data):
    shred = data.stat("upgrade_headshot_booster2", prop="BulletResistReduction",
                      conditional=True)
    assert C.damage_taken(C.final_resist([], [abs(s) for s in shred])) == pytest.approx(1.12)


def test_x06_spirit_sap_vs_enchanters_emblem(data):
    resist = data.stat("upgrade_magic_shield", prop="TechResist")
    sap = data.stat("upgrade_spirit_sap", prop="MagicResistReduction", conditional=True)
    assert C.final_resist(resist, [abs(s) for s in sap]) == pytest.approx(9.0)


def test_x07_weapon_damage_items_add(data):
    pct = sum(data.stat("upgrade_clip_size", "upgrade_high_velocity_mag", "upgrade_headhunter",
                        prop="BaseAttackDamagePercent"))
    assert pct == pytest.approx(21.0)


def test_x08_infernus_headshot_through_two_vests(data):
    base = data.weapon("hero_inferno")["bullet_damage"]
    pct = sum(data.stat("upgrade_clip_size", "upgrade_high_velocity_mag", "upgrade_headhunter",
                        prop="BaseAttackDamagePercent"))
    resist = C.stack_resist(data.stat("upgrade_metal_skin", "upgrade_regenerating_bullet_shield",
                                      prop="BulletResist"))
    crit = data.weapon("hero_inferno")["crit_bonus_start"]
    dmg = C.bullet_damage(base, pct, resist=resist, crit=crit)
    assert base == pytest.approx(5.5) and crit == pytest.approx(1.65)
    assert dmg == pytest.approx(5.5 * 1.21 * 0.7216 * 1.65)


def test_x09_fire_rate_rapid_rounds_plus_swift_striker_vs_suppressor_slow(data):
    bonus = data.stat("upgrade_rapid_rounds", "upgrade_blitz_bullets", prop="BonusFireRate")
    assert sum(bonus) == pytest.approx(29.0)
    assert C.fire_rate_multiplier(bonus, [28]) == pytest.approx(1.01)


def test_x10_napalm_with_two_spirit_items(data):
    sp = sum(data.stat("upgrade_improved_spirit", "upgrade_soaring_spirit", prop="TechPower"))
    base, scale = data.spirit_scaled("ability_incendiary_projectile", "Damage")
    assert (sp, base, scale) == (28.0, 40.0, 0.6)
    assert C.spirit_damage(base, scale, sp) == pytest.approx(56.8)


def test_x11_infernus_ehp_rebuttal_and_two_vests(data):
    hp = data.hero("hero_inferno")["max_health"] + sum(
        data.stat("upgrade_melee_rebuttal", prop="BonusHealth"))
    resist = C.stack_resist(data.stat("upgrade_metal_skin", "upgrade_regenerating_bullet_shield",
                                      prop="BulletResist"))
    assert hp == 905
    assert C.effective_hp(hp, resist) == pytest.approx(905 / 0.7216)


def test_x12_conditional_value_needs_opt_in(data):
    assert data.stat("upgrade_weapon_shielding", prop="BulletResist") == []
    assert data.stat("upgrade_weapon_shielding", prop="BulletResist", conditional=True) == [18.0]


def test_at_least_ten_cross_interactions_pinned():
    names = [n for n in globals() if n.startswith("test_x") and n[6:8].isdigit()]
    assert len(names) >= 10
