"""store_diary.py: Phase 4 step 4.4. The diary index (table diary_index, migration 028).

The entry FILES are the truth and are only ever READ here (opened 'rb', never written). The index is derived from them: refresh_index
walks a diary's folder and indexes every dated entry (YYYY/MM/DD.md and YYYY/MM/DD-RESCUED...md); reviews and the genesis page have
a period, not a day, so they are not indexed. What an entry's front matter carries is indexed as is: `mentions: [keys]`, `staged: [ids]`,
`confidence: low|medium|high`. Keys are NEVER guessed from prose; an entry with none gets an empty list. Keys are stored as written, and
resolved to their survivors when asked (entries_mentioning), so a merge after the entry was indexed still finds it.
Functions take a connection (like store_pages). Read only through these or gc, never SQL.
"""
import json
import os
import re
import time

import store_graph as sg

_DATED = re.compile(r"^(\d{4})/(\d{2})/(\d{2})(-RESCUED[^/]*)?\.md$")


def diary_name(desk_id, cfg=None):
    """A desk's diary name. ONE source: diary_names.py (the pattern and the desk list live in setup/desks.json)."""
    import diary_names
    return diary_names.diary_name(desk_id, cfg)


def _front(text):
    """-> dict of the simple `key: value` lines in the front matter (---), plus any leading `confidence:` line in the first 15 lines."""
    lines = text.splitlines()
    out = {}
    if lines and lines[0].strip() == "---":
        for ln in lines[1:]:
            if ln.strip() == "---":
                break
            m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", ln)
            if m:
                out[m.group(1)] = m.group(2).strip()
    if "confidence" not in out:
        for ln in lines[:15]:
            m = re.match(r"^confidence:\s*(.*)$", ln)
            if m:
                out["confidence"] = m.group(1).strip()
                break
    return out


def _list(v):
    """A flow list `[a, b]` -> ['a','b']. Anything else (a bare word, prose, nothing) -> []: never guess."""
    v = (v or "").strip()
    if not (v.startswith("[") and v.endswith("]")):
        return []
    return [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip().strip("'\"")]


def _confidence(v):
    w = (v or "").strip().lower().split(" ")[0].rstrip(",.;:(")
    return w if w in ("low", "medium", "high") else None


def date_of(rel_in_diary):
    """'2026/11/06.md' -> '2026-11-06'; None for a file that is not a dated entry."""
    m = _DATED.match(rel_in_diary.replace(os.sep, "/"))
    return "%s-%s-%s" % m.group(1, 2, 3) if m else None


def index_entry(con, diary, entry_file, notes_root, now=None):
    """Index one entry file (read only). Returns 'added', 'updated', 'same' or None (not a dated entry). Idempotent: one row per
    (diary, path); re-running changes nothing."""
    notes_root = os.path.abspath(notes_root)
    rel = os.path.relpath(os.path.abspath(entry_file), notes_root).replace(os.sep, "/")
    m = re.search(r"diary/(\d{4}/\d{2}/\d{2}(?:-RESCUED[^/]*)?\.md)$", rel)
    day = date_of(m.group(1)) if m else None
    if not day:
        return None
    with open(entry_file, "rb") as f:
        text = f.read().decode("utf-8", "replace")
    fm = _front(text)
    keys = json.dumps(_list(fm.get("mentions")))
    staged = json.dumps(_list(fm.get("staged") or fm.get("staged_ids")))
    conf = _confidence(fm.get("confidence"))
    old = con.execute("SELECT date, keys_mentioned, staged_ids, confidence FROM diary_index WHERE diary=? AND entry_path=?", (diary, rel)).fetchone()
    new = (day, keys, staged, conf)
    if old is not None and tuple(old) == new:
        return "same"
    stamp = now or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if old is None:
        con.execute("INSERT INTO diary_index(diary,date,keys_mentioned,staged_ids,entry_path,confidence,indexed_at) VALUES(?,?,?,?,?,?,?)",
                    (diary, day, keys, staged, rel, conf, stamp))
        return "added"
    con.execute("UPDATE diary_index SET date=?,keys_mentioned=?,staged_ids=?,confidence=?,indexed_at=? WHERE diary=? AND entry_path=?",
                (day, keys, staged, conf, stamp, diary, rel))
    return "updated"


def refresh_index(con, diary, diary_root, notes_root, now=None):
    """Index every dated entry under diary_root; drop index rows whose file is gone. -> {'added','updated','same','removed','skipped'}."""
    res = {"added": 0, "updated": 0, "same": 0, "removed": 0, "skipped": 0}
    seen = set()
    for dp, _dn, fns in os.walk(diary_root):
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            if not fn.endswith(".md") or fn.startswith("."):
                continue
            r = index_entry(con, diary, p, notes_root, now)
            if r is None:
                res["skipped"] += 1
                continue
            res[r] += 1
            seen.add(os.path.relpath(os.path.abspath(p), os.path.abspath(notes_root)).replace(os.sep, "/"))
    for rid, rel in con.execute("SELECT id, entry_path FROM diary_index WHERE diary=?", (diary,)).fetchall():
        if rel not in seen:
            con.execute("DELETE FROM diary_index WHERE id=?", (rid,))
            res["removed"] += 1
    return res


def entries_mentioning(con, key, diary=None):
    """Entries whose mentions carry this key, or any key that is now the same thing (a merged key resolves to its survivor, both
    ways). Newest first: [{'diary','date','entry_path','confidence','keys_mentioned','staged_ids'}]."""
    want = sg.resolve_key(con, key)
    sql, args = "SELECT diary,date,entry_path,confidence,keys_mentioned,staged_ids FROM diary_index", []
    if diary:
        sql, args = sql + " WHERE diary=?", [diary]
    out = []
    for d, day, path, conf, km, st in con.execute(sql + " ORDER BY date DESC, diary, entry_path", args).fetchall():
        keys = json.loads(km)
        if any(sg.resolve_key(con, k) == want for k in keys):
            out.append({"diary": d, "date": day, "entry_path": path, "confidence": conf, "keys_mentioned": keys, "staged_ids": json.loads(st)})
    return out
