"""E1 combat math: Deadlock stacking rules as pure functions (no I/O).

Percent inputs and outputs are in percent points (18 means 18%). Rules and
their sources: docs/research/hero-data.md ("Mechanics"). Values come from a
vw.gamedata.v1 dataset (tools/vw_gamedata.py); nothing here knows a patch.
"""

FIRE_RATE_FLOOR = -50.0


def _product_remaining(pcts):
    rem = 1.0
    for p in pcts:
        rem *= 1.0 - p / 100.0
    return rem


def stack_resist(pcts):
    """Resists stack multiplicatively: 1 - prod(1 - r)."""
    return (1.0 - _product_remaining(pcts)) * 100.0


def final_resist(resists, reductions):
    """Stacked reductions (also multiplicative) subtract from stacked resist;
    the result may go negative."""
    return stack_resist(resists) - stack_resist(reductions)


def damage_taken(resist_pct):
    """Damage multiplier for a final resist: 30 -> 0.7, -30 -> 1.3."""
    return 1.0 - resist_pct / 100.0


def effective_hp(hp, resist_pct):
    return hp / damage_taken(resist_pct)


def fire_rate_modifier(bonuses, slows):
    """Bonuses add; slows multiply; the total is floored at -50%."""
    total = sum(bonuses) - (1.0 - _product_remaining(slows)) * 100.0
    return max(total, FIRE_RATE_FLOOR)


def fire_rate_multiplier(bonuses, slows):
    """Bullets-per-second multiplier: 1 + m, or 1 / (1 + |m|) when negative."""
    m = fire_rate_modifier(bonuses, slows) / 100.0
    return 1.0 + m if m >= 0 else 1.0 / (1.0 - m)


def bullet_damage(base, weapon_pct, flat=0.0, falloff=1.0, resist=0.0, crit=1.0):
    """[(base x (1 + sum%)) + flat] x falloff x resist multiplier x crit."""
    return (base * (1.0 + weapon_pct / 100.0) + flat) * falloff * damage_taken(resist) * crit


def spirit_damage(base, scale, spirit_power):
    """Linear spirit scaling: base + spirit power x coefficient."""
    return base + spirit_power * scale
