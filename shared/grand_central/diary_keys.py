"""Phase 4 step 4.3: keys in every diary entry (Vision 2.7 and 3.10).

An entry's front matter carries ONE line, `mentions: [...]`: the keys (thing_keys, as Phase 3 mints them) of the people,
organizations, events and projects the entry names, plus the conversation ids it rests on (written `conversation:<id>`).

THE RULE: keys come only from the staged records' own keys (the form file's `thing_keys`, an item's `keys`, and its
`thread_ids`). Nothing here ever reads a name out of prose and looks a key up for it. Each staged key is checked against the
database: a merged-away key is written as its survivor's key (store_graph.survivor); a retired key, an unknown key or a key
of the wrong kind is not written (and is reported).

For the other steps: mentions_for_forms(con, forms) -> (mentions, dropped); front_matter(mentions) -> text;
read_front_matter(text) -> {"mentions": [...], "keys": [...], "conversations": [...]};
check_entry(text, staged_keys_raw, con) -> problems (a mentions line naming a key no staged record carries is refused)."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store_graph as sg  # noqa: E402

KEY_KINDS = ("person", "organization", "event", "project")
CONV = "conversation:"
ID_RE = re.compile(r"^[0-9a-f]{6,32}$")
FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def staged_from_form(form):
    """(raw keys, conversation ids) a staged form file carries itself. Anything not a string is ignored."""
    if not isinstance(form, dict):
        return [], []
    keys = [k for k in form.get("thing_keys") or [] if isinstance(k, str)]
    for field in ("deadlines", "money", "needs_him", "project_updates"):
        for it in form.get(field) or []:
            if isinstance(it, dict):
                keys += [k for k in it.get("keys") or [] if isinstance(k, str)]
    convs = [c for c in form.get("thread_ids") or [] if isinstance(c, str) and ID_RE.match(c)]
    return keys, convs


def resolve_key(con, key):
    """-> (key to write or None, reason if dropped). Merged-away -> the survivor's key; retired, unknown, wrong kind -> None."""
    key = key.strip()
    if key.split(":", 1)[0] not in KEY_KINDS:
        return None, "kind_not_allowed"
    r = con.execute("SELECT id FROM kg_things WHERE key=?", (key,)).fetchone()
    if r is None:
        return None, "unknown_key"
    sid = sg.survivor(con, r[0])
    t = con.execute("SELECT key, kind, retired_at FROM kg_things WHERE id=?", (sid,)).fetchone()
    if t is None or t[2] is not None or t[1] not in KEY_KINDS:
        return None, "retired"
    return t[0], None


def mentions_for_forms(con, forms):
    """forms: the staged forms (dicts) of one diary-day. -> (sorted mentions list, [(key, reason)] dropped)."""
    seen, convs, dropped = set(), set(), []
    for form in forms:
        keys, cs = staged_from_form(form)
        convs.update(cs)
        for k in keys:
            if con is None:
                dropped.append((k, "no_database"))
                continue
            live, why = resolve_key(con, k)
            if live:
                seen.add(live)
            else:
                dropped.append((k, why))
    return sorted(seen) + [CONV + c for c in sorted(convs)], dropped


def front_matter(mentions, staged=None):
    """The entry's header: one mentions line, plus (when given) one staged line with the ids of the staged records it rests on."""
    st = "staged: %s\n" % json.dumps(list(staged), ensure_ascii=True) if staged else ""
    return "---\nmentions: %s\n%s---\n" % (json.dumps(list(mentions), ensure_ascii=True), st)


def read_front_matter(text):
    """Parse the front matter back. -> {"mentions": [...], "keys": [...], "conversations": [...]}; raises ValueError if absent or bad."""
    m = FM_RE.match(text)
    if not m:
        raise ValueError("no front matter")
    lines = [ln for ln in m.group(1).split("\n") if ln.strip()]
    if not lines or not lines[0].startswith("mentions: ") or len(lines) > 2 or (len(lines) == 2 and not lines[1].startswith("staged: ")):
        raise ValueError("front matter is not one mentions line (and at most one staged line)")
    ms = json.loads(lines[0][len("mentions: "):])
    st = json.loads(lines[1][len("staged: "):]) if len(lines) == 2 else []
    if not isinstance(ms, list) or not all(isinstance(x, str) for x in ms) or not isinstance(st, list) or not all(isinstance(x, str) for x in st):
        raise ValueError("mentions or staged is not a list of strings")
    return {"mentions": ms, "staged": st,
            "keys": [x for x in ms if not x.startswith(CONV)],
            "conversations": [x[len(CONV):] for x in ms if x.startswith(CONV)]}


def check_entry(text, staged_keys_raw, con, staged_conversations=(), staged_ids_allowed=None):
    """Problems for one entry: no/bad front matter; a mentions key no staged record carries (a staged key counts through its
    survivor); a retired key written; a conversation id no staged record carries. [] means clean."""
    try:
        fm = read_front_matter(text)
    except ValueError as e:
        return ["front_matter:%s" % e]
    allowed = set()
    for k in staged_keys_raw:
        allowed.add(k)
        live, _ = resolve_key(con, k)
        if live:
            allowed.add(live)
    problems = []
    for k in fm["keys"]:
        if k not in allowed:
            problems.append("not_staged:%s" % k)
        elif resolve_key(con, k)[0] != k:
            problems.append("retired_or_merged_key_written:%s" % k)
    for c in fm["conversations"]:
        if c not in set(staged_conversations):
            problems.append("conversation_not_staged:%s" % c)
    if staged_ids_allowed is not None:
        for sid in fm["staged"]:
            if sid not in set(staged_ids_allowed):
                problems.append("staged_not_staged:%s" % sid)
    return problems
