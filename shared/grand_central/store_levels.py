"""store_levels.py: Phase 3 step 3.4. The one place later steps (3.5 relation to the person, 3.8 scoring) ask for a level."""


def levels_above_me(con, person_key=None):
    """Level above the person (Vision 3.7.4 rule 9), read from the view v_levels_above_me. Computed, never stored.
    -> (level or None, source 'owner' | 'chain' | 'unknown') for one person_key, or {person_key: (level, source)} for everyone.
    None counts for nothing in any score. Works with or without reports_to lines (none -> unknown, never a guess)."""
    if person_key is not None:
        r = con.execute("SELECT level, source FROM v_levels_above_me WHERE person_key=?", (person_key,)).fetchone()
        return (r[0], r[1]) if r else (None, "unknown")
    return {k: (lv, s) for k, lv, s in con.execute("SELECT person_key, level, source FROM v_levels_above_me")}

