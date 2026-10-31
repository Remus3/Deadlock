"""Versioned local hero / item dataset from the community Deadlock API.

    python tools/vw_gamedata.py fetch [--out DIR]     fetch latest patch, build, write
    python tools/vw_gamedata.py subset --src F --items a,b --heroes h --out DIR

The dataset (schema vw.gamedata.v1) is numbers and identifiers only: no
descriptions, images or URLs. Full datasets are Valve game data served by a
third party, so they are written to the gitignored ops/runtime/gamedata/ and
never tracked (decision D-HERO-1, docs/research/hero-data.md). Only small
test fixtures made by `subset` are tracked.

Network use (R-APP-4): one GET per endpoint per run, with If-Modified-Since
when a previous fetch stored a Last-Modified value.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.deadlock-api.com"
SCHEMA = "vw.gamedata.v1"
OUT = ROOT / "ops" / "runtime" / "gamedata"
CONDITIONAL_FLAG = "ConditionallyApplied"
WEAPON_KEYS = ("bullet_damage", "cycle_time", "clip_size", "bullets", "crit_bonus_start",
               "crit_bonus_end", "damage_falloff_start_range", "damage_falloff_end_range")
HERO_STATS = ("max_health", "base_health_regen", "max_move_speed", "sprint_speed",
              "stamina", "light_melee_damage", "heavy_melee_damage", "bullet_armor_damage_reduction",
              "tech_armor_damage_reduction")
ABILITY_SLOTS = ("signature1", "signature2", "signature3", "signature4")


def _num(v):
    """'18' / '12m' / '-0.5s' / 3 -> float; anything else -> None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().rstrip("m%s")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _spirit_scale(prop):
    sf = prop.get("scale_function") or {}
    scale = sf.get("stat_scale")
    if scale is None:
        return None
    kind = sf.get("specific_stat_scale_type")
    if kind == "ETechPower" or (sf.get("class_name") == "scale_function_tech_damage"
                                and kind is None):
        return float(scale)
    return None


def compact_item(raw):
    stats, conditional, spirit = {}, {}, {}
    for key, prop in (raw.get("properties") or {}).items():
        if not isinstance(prop, dict):
            continue
        val = _num(prop.get("value"))
        if val is None or val == 0:
            continue
        flags = prop.get("usage_flags") or []
        (conditional if CONDITIONAL_FLAG in flags else stats)[key] = val
        scale = _spirit_scale(prop)
        if scale is not None:
            spirit[key] = scale
    out = {"id": raw.get("id"), "name": raw.get("name"), "type": raw.get("type"),
           "stats": stats, "conditional": conditional}
    if spirit:
        out["spirit_scale"] = spirit
    for src, dst in (("item_slot_type", "slot"), ("item_tier", "tier"), ("cost", "cost")):
        if raw.get(src) is not None:
            out[dst] = raw[src]
    if raw.get("type") == "weapon":
        wi = raw.get("weapon_info") or {}
        out["weapon"] = {k: wi[k] for k in WEAPON_KEYS if k in wi}
    return out


def compact_hero(raw):
    ss = raw.get("starting_stats") or {}
    items = raw.get("items") or {}
    out = {"id": raw.get("id"), "name": raw.get("name"), "hero_type": raw.get("hero_type"),
           "weapon": items.get("weapon_primary"),
           "abilities": [items[s] for s in ABILITY_SLOTS if s in items]}
    for k in HERO_STATS:
        v = ss.get(k)
        if isinstance(v, dict) and _num(v.get("value")) is not None:
            n = _num(v["value"])
            out[k] = int(n) if n.is_integer() else n
    return out


def build(raw_heroes, raw_items, client_version, fetched=None):
    heroes = {h["class_name"]: compact_hero(h) for h in raw_heroes
              if h.get("player_selectable", True) and not h.get("disabled")}
    items = {i["class_name"]: compact_item(i) for i in raw_items if i.get("class_name")}
    return {"schema": SCHEMA, "client_version": int(client_version),
            "fetched": fetched or date.today().isoformat(),
            "source": API + " (/v1/assets/heroes, /v1/assets/items)",
            "license": "Valve game data via a third-party API; not redistributed (D-HERO-1)",
            "heroes": dict(sorted(heroes.items())), "items": dict(sorted(items.items()))}


def subset(doc, items=(), heroes=()):
    """Named items plus each named hero and its weapon / abilities."""
    keep = set(items)
    hs = {}
    for h in heroes:
        hero = doc["heroes"][h]
        hs[h] = hero
        keep.update([hero["weapon"]] + hero["abilities"])
    out = dict(doc)
    out["heroes"] = dict(sorted(hs.items()))
    out["items"] = {k: doc["items"][k] for k in sorted(keep) if k in doc["items"]}
    return out


def write(doc, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"vw_gamedata_{doc['client_version']}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=True) + "\n",
                   encoding="ascii", newline="\n")
    os.replace(tmp, path)
    return path


class Dataset:
    def __init__(self, doc):
        if doc.get("schema") != SCHEMA:
            raise ValueError(f"schema {doc.get('schema')!r} is not {SCHEMA}")
        self.doc = doc
        self.schema = doc["schema"]
        self.client_version = doc["client_version"]

    def item(self, class_name):
        return self.doc["items"][class_name]

    def hero(self, class_name):
        return self.doc["heroes"][class_name]

    def weapon(self, hero_class):
        return self.item(self.hero(hero_class)["weapon"])["weapon"]

    def stat(self, *class_names, prop, conditional=False):
        """Values of prop on each named item that has it (passive only unless
        conditional=True, which reads the conditional values too)."""
        out = []
        for cn in class_names:
            it = self.item(cn)
            for src in ("stats", "conditional") if conditional else ("stats",):
                if prop in it[src]:
                    out.append(it[src][prop])
        return out

    def spirit_scaled(self, class_name, prop):
        it = self.item(class_name)
        return it["stats"][prop], it["spirit_scale"][prop]


def _get(path, out_dir):
    """GET with If-Modified-Since; a 304 is served from the raw cache."""
    raw_dir = Path(out_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cache = raw_dir / (re.sub(r"[^A-Za-z0-9.-]+", "_", path.strip("/")) + ".json")
    meta_path = raw_dir / "fetch_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    req = urllib.request.Request(API + path, headers={"User-Agent": "VeilWalker-gamedata"})
    if meta.get(path) and cache.exists():
        req.add_header("If-Modified-Since", meta[path])
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
            modified = r.headers.get("Last-Modified")
    except urllib.error.HTTPError as e:
        if e.code != 304:
            raise
        return json.loads(cache.read_bytes().decode("utf-8"))
    cache.write_bytes(data)
    if modified:
        meta[path] = modified
        meta_path.write_text(json.dumps(meta, indent=1) + "\n", encoding="ascii", newline="\n")
    return json.loads(data.decode("utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--out", default=str(OUT))
    s = sub.add_parser("subset")
    s.add_argument("--src", required=True)
    s.add_argument("--items", default="")
    s.add_argument("--heroes", default="")
    s.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        versions = _get("/v1/assets/client-versions", a.out)
        latest = max(versions)
        q = f"?client_version={latest}"
        doc = build(_get("/v1/assets/heroes" + q, a.out), _get("/v1/assets/items" + q, a.out),
                    latest)
        print(write(doc, a.out))
    else:
        doc = json.loads(Path(a.src).read_text(encoding="utf-8"))
        part = subset(doc, [x for x in a.items.split(",") if x],
                      [x for x in a.heroes.split(",") if x])
        print(write(part, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
