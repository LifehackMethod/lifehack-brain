"""Phase 4 step 4.2 (Vision 2.7 and 3.10): which diary does a staged item go to.
Each item carries a part of life: from its label's life_part (setup/labels.json), else its sender's `domain` fact.
setup/routing.json maps part of life -> desk; the diary NAME is formed by the pattern (default "<desk>-Diary") from the
desk. No part of life, or one no desk owns -> the main diary. Never guessed from free text. Desk names are NOT in this
file: they come from the table in setup/."""
import json

import gc_settings

NONE_WORDS = ("", "none", "null")


def _load(name, path=None):
    """One setup file: the person's (gc_settings) unless a path is given."""
    if path is None:
        return gc_settings.load(name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_table(path=None):
    return _load("routing.json", path)


def diary_name(desk, table):
    pattern = table.get("diary_pattern") or "{desk}-Diary"
    return pattern.replace("{desk}", desk)


def _clean(v):
    v = (str(v).strip() if v is not None else "")
    return None if v.lower() in NONE_WORDS else v


def sender_domain_fact(con, address):
    """The `domain` fact on the sender's address, its domain, or a rule applying to either. None if there is none."""
    addr = (address or "").strip().lower()
    if "<" in addr and ">" in addr:
        addr = addr[addr.index("<") + 1:addr.index(">")].strip()
    if "@" not in addr:
        return None
    dom = addr.rsplit("@", 1)[1]
    parts = dom.split(".")
    keys = ["address:" + addr] + ["domain:" + ".".join(parts[i:]) for i in range(len(parts) - 1)]
    for k in keys:
        rows = con.execute("SELECT f.value FROM kg_things t JOIN kg_current_facts f ON f.thing_id=t.id AND f.fact_key='domain' "
                           "WHERE t.key=? ORDER BY f.id DESC", (k,)).fetchall()
        for (v,) in rows:
            if _clean(v):
                return _clean(v)
        rows = con.execute("SELECT f.value FROM kg_things tg JOIN kg_current_links l ON l.to_id=tg.id AND l.kind='applies_to' "
                           "JOIN kg_things r ON r.id=l.from_id AND r.kind='rule' "
                           "JOIN kg_current_facts f ON f.thing_id=r.id AND f.fact_key='domain' WHERE tg.key=? ORDER BY f.id DESC", (k,)).fetchall()
        for (v,) in rows:
            if _clean(v):
                return _clean(v)
    return None


def part_of_life(item, labels, con=None):
    """item: {"label": <label name or None>, "sender": <address or None>}. The label's life_part wins; else the sender's
    domain fact (needs con). -> a part-of-life word or None."""
    lab = (labels or {}).get("labels", {}).get(item.get("label") or "")
    if lab and _clean(lab.get("life_part")):
        return _clean(lab["life_part"])
    if con is not None and item.get("sender"):
        return sender_domain_fact(con, item["sender"])
    return None


def route(part, table):
    """-> the diary name. The main diary unless the table names a desk for exactly this part of life."""
    desk = None
    if _clean(part):
        for k, v in (table.get("parts_to_desk") or {}).items():
            if k.casefold() == str(part).strip().casefold():
                desk = _clean(v)
                break
    return diary_name(desk, table) if desk else table["main_diary"]


def route_item(item, labels, table, con=None):
    part = part_of_life(item, labels, con)
    return {"part_of_life": part, "diary": route(part, table)}
