"""vw_gamedata: raw API payloads -> compact vw.gamedata.v1 (no network)."""
import json

import pytest

import vw_gamedata as G

RAW_ITEMS = [
    {"id": 1, "class_name": "upgrade_a", "name": "A", "type": "upgrade", "shopable": True,
     "item_slot_type": "vitality", "item_tier": 2, "cost": 1600,
     "description": {"desc": "prose is dropped"}, "image": "https://x/a.png",
     "properties": {
         "BulletResist": {"value": "18", "postfix": "%"},
         "BonusHealth": {"value": "0"},
         "AbilityCastRange": {"value": "12m"},
         "TechResist": {"value": "15", "usage_flags": ["ConditionallyApplied"]},
         "Label": {"value": "not a number"}}},
    {"id": 2, "class_name": "ability_b", "name": "B", "type": "ability",
     "properties": {"Damage": {"value": "40.0", "scale_function": {
         "class_name": "scale_function_tech_damage", "specific_stat_scale_type": "ETechPower",
         "stat_scale": 0.6}}}},
    {"id": 3, "class_name": "citadel_weapon_b", "name": "Gun", "type": "weapon",
     "weapon_info": {"bullet_damage": 5.5, "cycle_time": 0.1, "clip_size": 20,
                     "crit_bonus_start": 1.65, "unused": "x"}},
]
RAW_HEROES = [{"id": 9, "class_name": "hero_b", "name": "B", "hero_type": "brawler",
               "player_selectable": True, "images": {"x": "y"},
               "items": {"weapon_primary": "citadel_weapon_b", "signature1": "ability_b"},
               "starting_stats": {"max_health": {"value": 800}, "max_move_speed": {"value": 7}}}]


@pytest.fixture
def ds():
    return G.Dataset(G.build(RAW_HEROES, RAW_ITEMS, client_version=6836, fetched="2026-10-31"))


def test_build_header_and_no_prose_or_urls():
    doc = G.build(RAW_HEROES, RAW_ITEMS, client_version=6836, fetched="2026-10-31")
    assert doc["schema"] == G.SCHEMA and doc["client_version"] == 6836
    text = json.dumps([doc["heroes"], doc["items"]])
    assert "prose" not in text and "https://" not in text and "Label" not in text


def test_numbers_parsed_zeros_dropped_flags_kept(ds):
    a = ds.item("upgrade_a")
    assert a["stats"] == {"BulletResist": 18.0, "AbilityCastRange": 12.0}
    assert a["conditional"] == {"TechResist": 15.0}
    assert (a["slot"], a["tier"], a["cost"]) == ("vitality", 2, 1600)


def test_spirit_scale_and_weapon(ds):
    assert ds.spirit_scaled("ability_b", "Damage") == (40.0, 0.6)
    assert ds.weapon("hero_b") == {"bullet_damage": 5.5, "cycle_time": 0.1, "clip_size": 20,
                                   "crit_bonus_start": 1.65}


def test_hero_compact(ds):
    h = ds.hero("hero_b")
    assert h["max_health"] == 800 and h["hero_type"] == "brawler"
    assert h["weapon"] == "citadel_weapon_b" and h["abilities"] == ["ability_b"]


def test_stat_multi_and_unknown_raises(ds):
    assert ds.stat("upgrade_a", prop="BulletResist") == [18.0]
    with pytest.raises(KeyError):
        ds.stat("upgrade_missing", prop="BulletResist")


def test_subset_keeps_named_and_hero_kit(ds):
    sub = G.Dataset(G.subset(ds.doc, items=["upgrade_a"], heroes=["hero_b"]))
    assert sorted(sub.doc["items"]) == ["ability_b", "citadel_weapon_b", "upgrade_a"]


def test_schema_mismatch_refused():
    with pytest.raises(ValueError):
        G.Dataset({"schema": "other", "client_version": 1, "items": {}, "heroes": {}})


def test_write_is_atomic_and_versioned(tmp_path):
    doc = G.build(RAW_HEROES, RAW_ITEMS, client_version=6836, fetched="2026-10-31")
    p = G.write(doc, tmp_path)
    assert p.name == "vw_gamedata_6836.json"
    assert json.loads(p.read_text(encoding="utf-8")) == doc
    assert not list(tmp_path.glob("*.tmp"))
    assert G.write(doc, tmp_path).read_bytes() == p.read_bytes()
