# VW-APP-HERO - heroes, items, interactions: dataset and pinned rules

Status: DONE 2026-10-31 (patch / client version 6836). Code:
`tools/vw_gamedata.py` (dataset), `tools/vw_combat.py` (E1 stacking rules).
Tests: `tests/test_gamedata.py`, `tests/test_combat.py` (12 cross-interactions
pinned at 6836). Source classes: class 1 only (`docs/research/game-data.md`).

## Decision D-HERO-1: fetch tool + compact schema, no tracked full dataset

- Decision: the full per-patch dataset is BUILT LOCALLY by
  `python tools/vw_gamedata.py fetch` into the gitignored
  `ops/runtime/gamedata/vw_gamedata_<client_version>.json` (about 420 KB:
  44 selectable heroes, 782 items at 6836). The app will write the same file
  into its user-data DB (R-DATA-1). The repo tracks only the tool, the
  schema and one small test fixture per pinned patch
  (`tests/fixtures/gamedata/vw_gamedata_6836.json`, 1 hero kit and 17
  items, numbers and ids only).
- Alternatives: (a) commit the full API dump (6.4 MB items + 1.9 MB heroes) -
  rejected: it is Valve game data, the API's MIT license covers its code
  only, and the dump would break the repo size budget; (b) no local dataset,
  query the API live - rejected: R-APP-3/4 want an offline, versioned, re-
  playable dataset, and engines test on recorded fixtures.
- Why: a compact numeric excerpt is the minimum the tests need. Names and
  numbers are facts of the game, with no prose, art or URLs.
- Reverses: a published license that allows redistribution of the data, or
  an operator ruling that a full tracked dataset is wanted.

## Schema vw.gamedata.v1

Top level: `schema`, `client_version` (int, the patch key for R-COACH-3),
`fetched` (date), `source`, `license`, `heroes{class_name: hero}`,
`items{class_name: item}`.

- hero: `id`, `name`, `hero_type` (mystic / brawler / assassin / marksman;
  null for 6 heroes at 6836), `weapon` (item class), `abilities` (4 signature
  ability classes), and the starting stats `max_health`, `base_health_regen`,
  `max_move_speed`, `sprint_speed`, `stamina`, `light_melee_damage`,
  `heavy_melee_damage` when present.
- item (ability, upgrade or weapon): `id`, `name`, `type`, `slot`
  (weapon / vitality / spirit), `tier`, `cost`, `stats{property: number}`
  (non-zero passive values), `conditional{property: number}` (values flagged
  `ConditionallyApplied`: active effects, procs, conditions),
  `spirit_scale{property: coefficient}` (spirit power scaling), and for a
  weapon `weapon{bullet_damage, cycle_time, clip_size, bullets,
  crit_bonus_start, crit_bonus_end, damage_falloff_start_range,
  damage_falloff_end_range}`.
- Parsing rules: a value string drops a trailing `m`, `%` or `s` unit and is
  parsed as a number; zeros and non-numbers are dropped. A property counts as
  spirit-scaled when its scale function names `ETechPower`, or is
  `scale_function_tech_damage` with no named stat.
- Known gap: the API flag `IntrinsicallyProvidedInAbility` is treated as
  passive. That matches the passive stats of Bullet Resilience and Spirit
  Resilience, but some debuff items (e.g. Mystic Vulnerability) list the
  enemy's resist change under the same property name as a self resist. E1
  must not read a debuff item's `TechResist` as self armour; VW-APP-E1 adds
  a per-item override table, tested against the patch fixture.

## Mechanics rules (E1, `tools/vw_combat.py`)

All read 2026-10-31 from the community wiki (reference only; its pages state
no license, so the rules are restated, not copied):

- Resists stack multiplicatively: `1 - prod(1 - r_i)`. Reductions (shred)
  stack the same way and subtract from the stacked resist; the result may go
  negative (more damage taken). `https://deadlock.wiki/Bullet_Resist`
  (Damage_Resistance page).
- Weapon damage: `[(base x (1 + sum of weapon %)) + flat] x falloff x
  resist multiplier x crit`; base weakpoint crit 1.65x.
  `https://deadlock.wiki/Weapon_Damage`
- Fire rate: bonuses add, slows multiply, the total is floored at -50%; a
  negative total divides the rate by `1 + |m|`. `https://deadlock.wiki/Fire_Rate`
- Spirit damage: `base + spirit power x coefficient`; flat spirit power
  adds. `https://deadlock.wiki/Spirit_Power`
- Effective HP vs a damage type: `hp / (1 - resist)`.

## Interactions pinned at 6836 (tests/test_combat.py)

- x01 Metal Skin 12 + Battle Vest 18 bullet resist = 27.84%.
- x02 + Bullet Resilience 35 = 53.096%.
- x03 Enchanter's Emblem 18 + Restorative Locket 8 spirit resist = 24.56%.
- x04 Weakening Headshot 12 + Crippling Headshot 16 shred vs Bullet
  Resilience 35 = 8.92% resist (0.9108 damage taken).
- x05 Weakening Headshot on a 0-resist target = 1.12 damage taken.
- x06 Spirit Sap 9 vs Enchanter's Emblem 18 = 9% spirit resist.
- x07 Extended Magazine 8 + High-Velocity Rounds 8 + Headhunter 5 = +21%
  weapon damage.
- x08 Infernus bullet 5.5 x 1.21 headshot (1.65) through x01's resist.
- x09 Rapid Rounds 9 + Swift Striker 20 vs a 28% slow = 1.01 fire rate.
- x10 Napalm 40 + 0.6 x (Extra Spirit 10 + Improved Spirit 18) = 56.8.
- x11 Infernus 830 HP + Rebuttal 75 with x01's resist = 905 / 0.7216 EHP.
- x12 Weapon Shielding's 18% bullet resist is conditional and counts only on
  opt-in.

A new patch: `fetch`, `subset` the same names into a new fixture, add a
pinned copy of the tests for that version, and diff the values. A changed
value is a patch-note item for distilled-rule re-review (R-COACH-3).

## Archetypes and counters (research result)

- Archetypes: the game's own `hero_type` (13 mystic, 10 brawler, 9
  assassin, 6 marksman, 6 unset at 6836) and the item slots (84 weapon,
  87 vitality, 79 spirit upgrades) give the archetype axes: gun / spirit /
  vitality build share.
- Counters and synergies are statistical, not in the asset data:
  `/v1/analytics/hero-counter-stats`, `hero-synergy-stats`,
  `lane-matchup-stats`, `item-permutation-stats`, `build-item-stats`
  (class 1, the shared 200 req/min analytics limit, cached 1 h). VW-APP-E1
  stores them per patch next to this dataset; counter math (e.g. shred vs
  armour items) uses the rules above, so a statistical counter can be
  explained by its math reason.
