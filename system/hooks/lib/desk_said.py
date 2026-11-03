#!/usr/bin/env python3
"""desk_said.py -- switch desk_tool_sign (roundB.conf), exam miss D-B07 r2: which of the person's real desks they just named.

WHY: a write to <personal code>/tools/x.py looks the same for a loose script and a one-desk tool, so the write hook cannot tell them apart alone.
     The prompt hook gets the typed words and the write hook gets the same session_id, a sub-agent's write included (real stdin, tests/fixtures/).
HOW: inject_sop_before_build.sh pipes its payload here; this leaves ~/.claude/run/build-mode/desk-said.<session> holding the desk's notes folder name,
     when the prompt names EXACTLY ONE desk the person really has. guard_build_mode.sh reads it (placement rule desk-tool-loose). A later prompt that
     says "desk" and names none, or several, empties it; a prompt without the word leaves it, so a follow-up answer keeps the desk. It goes stale after STALE_SECONDS.
THE DESKS: folders in <notes>/desks/ plus <notes>/desks/desk-registry.yaml (shared/desk_list.py). No desks -> nothing is ever left, so a student sees nothing.
THE WORDS: a real name next to the word desk. No name is built in, and furniture falls out: "my desk lamps" and "lamps on my desk" are not a form below.
FAIL POSTURE: degrade-safe. Any error leaves no signal: no sign, never a stuck session.
"""
import json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STALE_SECONDS = 3600
_NOT_TYPED = re.compile(r"<(summary|task-notification|result|output|system-reminder)\b[^>]*>.*?(?:</\1>|$)|```.*?(?:```|$)", re.S | re.I)
_NEGATED = re.compile(r"(?:\b(?:not|never|without|no|isn't|aren't|don't|doesn't)\s+(?:\w+\s+){0,3}|\b(?:nothing to do with|unrelated to)\s+(?:\w+\s+){0,2})$", re.I)


def _marker(sid):
    return os.path.join(os.path.expanduser("~"), ".claude", "run", "build-mode", "desk-said." + re.sub(r"[^A-Za-z0-9_.-]", "_", sid)[:80])


def real_desks():
    """{name the person may say: folder under <notes>/desks/}"""
    sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "shared"))
    import desk_list, person_roots
    out = {}
    notes = person_roots.notes_root()
    if notes:
        try:
            for name in os.listdir(os.path.join(notes, "desks")):
                if name[0] not in "._" and os.path.isdir(os.path.join(notes, "desks", name)):
                    out[name] = name
        except OSError:
            pass
    for entry in desk_list.load_desks()[0] or []:
        did = str(entry.get("desk_id") or "").strip()
        if did:
            out[did] = desk_list.desk_folder(did)[0] or did
    return out


def _forms(name):
    n = r"[-_\s]+".join(re.escape(w) for w in re.split(r"[-_\s]+", name))
    end = r"(?![\w-])"
    return (r"\bdesks/" + n + end,                                                    # desks/lamps
            r"(?<![\w-])" + n + r"(?:'s)?[-_\s]+desk" + end,                          # lamps desk, lamps-desk, lamps's desk
            r"\bdesk\s*(?:called|named|i\s+call|we\s+call|:|=)\s*['\"`]?" + n + end,  # desk called lamps, desk: lamps
            r"(?<![\w-])" + n + r"(?:\s*,|\s+is)\s+(?:my|our|the|one\s+of\s+(?:my|our|the))\s+desks?" + end)   # lamps is my desk, lamps, one of my desks


def named(prompt, desks):
    """-> the one folder this prompt names, or None."""
    text = _NOT_TYPED.sub(" ", prompt).replace("’", "'")
    found = set()
    for name, folder in desks.items():
        for form in _forms(name):
            if any(not _NEGATED.search(text[:m.start()]) for m in re.finditer(form, text, re.I)):
                found.add(folder)
    return found.pop() if len(found) == 1 else None


def note(payload):
    sid = str(payload.get("session_id") or "")
    if not sid:
        return
    prompt = str(payload.get("prompt") or "")
    if "desk" not in prompt.lower():   # the hook's filter sees the whole payload, and a cwd like ~/Desktop must not empty the marker
        return
    desk = named(prompt, real_desks())
    mk = _marker(sid)
    if desk or os.path.exists(mk):
        os.makedirs(os.path.dirname(mk), exist_ok=True)
        with open(mk, "w", encoding="utf-8") as f:
            f.write(desk or "")


def read(sid):
    """-> the folder of the desk this session's person named, or None."""
    try:
        mk = _marker(sid)
        if not sid or time.time() - os.path.getmtime(mk) > STALE_SECONDS:
            return None
        with open(mk, encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


if __name__ == "__main__":
    try:
        note(json.loads(sys.stdin.read() or "{}"))
    except Exception as e:
        sys.stderr.write("desk_said: skipped (%s)\n" % e)
    sys.exit(0)
