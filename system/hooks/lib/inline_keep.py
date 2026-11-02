#!/usr/bin/env python3
"""inline_keep.py -- decide whether the end-of-turn hook should nudge about an INLINE command (switch inline_keep_nudge).

WHY: exam cases D-B03/D-B04 (2026-11-01): the person said "keep it" about a command Claude had run inline (find ... -exec wc -l);
no file was written, so the file-based own-list check had nothing to inspect. Spec: notes record 2026-11-01-final-miss-analysis.md.

Usage: inline_keep.py <transcript.jsonl> <already_saved 0|1> <state_file>
Prints nothing (stay silent) or ONE line "keep<TAB>cmd" / "offer<TAB>cmd". Never raises: any error = silent.
  keep : the person's words (this turn, or the turn just before) show keep-intent, this turn ran an inline Bash command
         (>= MIN_CHARS), and no file was saved -> block once.
  offer: no keep-intent, but the inline command is LONG and REUSABLE (is_reusable) -> at most one per session
         (state_file holds a line "offer" once spent; a line "cmd:<sha>" per command already nudged).
Only REAL text counts: user entries that are not isMeta, with every <system-reminder>...</system-reminder> span stripped
(injected context is not what the person said), tool_result blocks ignored. Also skipped (plan item 15, 2026-11-02):
compaction summaries (isCompactSummary / isVisibleInTranscriptOnly -- they quote OLD words back), and any row whose origin.kind
is not "human" (task notifications arrive as type "user" with origin.kind "task-notification" and NO isMeta; cross-session
peer messages are origin.kind "peer" and already isMeta). A row with NO origin field still counts: older Claude Code builds,
slash-command rows and interrupt rows carry none, and those are the person's own doing.
"""
import hashlib
import json
import re
import sys

MIN_CHARS = 20      # below this a command is a glance (ls, pwd, git status), not something to keep
LONG_CHARS = 120    # a single line this long is something you would not retype
# "keep it/this/that" is keep-intent ONLY when the phrase ENDS there (plan item 15, 2026-11-02: Enver's "keep this on track so
# just keep it on track" was read as "keep this command"). Rule: after the pronoun come zero or more KEEP_TAIL words (please,
# thanks, too, then, around, handy, saved, "as a script/tool/...", "for later/next time/..."), then a BOUNDARY: end of text, a
# newline, punctuation, or a new clause starting with "and"/"but". Anything else continues the phrase -- "keep it on track",
# "keep it working/going/up/short/simple", "keep that in mind" -- and is an idiom, not keep-intent. An explicit object noun
# ("keep the command", "keep that one", "keep this script") always counts. The rule is an allowlist on purpose: a missed
# keep costs one un-nudged turn; a false keep blocks the person's turn with a request they never made.
KEEP_TAIL = (r"(?:\s+(?:please|pls|thanks|thank you|ok|okay|too|then|around|handy|somewhere|saved"
             r"|as (?:a |an |my )?(?:script|tool|command|file|snippet|one)"
             r"|for (?:later|next time|the future|reuse|re-use|me|now)))*")
KEEP_END = r"(?:[ \t]*(?:$|\n|[.,!?;:)\]\"'\u2014\u2013\u2026-])|\s+(?:and|but)\b)"
KEEP = re.compile(
    r"\b(keep (?:the|that|this) (?:command|one|script|snippet|pipeline|line)\b|keep (?:it|that|this)(?=" + KEEP_TAIL + KEEP_END + r")|"
    r"(?:save (that|this|it)( command| one)?|"
    r"i'?ll (reuse|re-use|use) (it|that|this)|reuse (it|that|this)|re-use (it|that|this)|"
    r"make (that|this|it) a (script|tool)|turn (that|this|it) into a (script|tool))\b)", re.I)
NEG = re.compile(r"\b(don'?t|do not|no need to|not|never|without)\s+(\w+\s+){0,2}$", re.I)
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
LOOPS = re.compile(r"(^|[\s;&|(])(for|while|until)\s|\bxargs\b|-exec\b|\bparallel\b")


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
WRITES = re.compile(
    r"(?<![0-9&<>])>>?\|?(?!&)\s*(?!/dev/)[^\s|;&)<>]"   # > file, >> file (not 2>/dev/null, 2>&1, &>)
    r"|(^|[\s;&|(])(tee|cp|mv|install|rsync|touch)\s|\bsed\s+(-[A-Za-z]*\s+)*-i|\bof=")


def skeleton(cmd):
    """The command itself: heredoc BODIES dropped and quoted text replaced by Q, so a pasted document or a string payload is never
    measured as command length or pipes, and a '>' inside a quoted string is never read as a redirect."""
    out, delim = [], None
    for line in cmd.split("\n"):
        if delim is not None:
            if line.strip() == delim:
                delim = None
            continue
        out.append(line)
        m = HEREDOC.search(line)
        if m:
            delim = m.group(2)
    t = "\n".join(out)
    t = re.sub(r"'[^']*'", "Q", t)
    t = re.sub(r'"(?:[^"\\]|\\.)*"', "Q", t)
    return t


def writes_file(cmd):
    """True when the command itself saves a file: a redirect, tee, cp/mv/install/rsync/touch, sed -i, dd of=."""
    return bool(WRITES.search(skeleton(cmd)))


def has_keep_intent(text):
    for m in KEEP.finditer(text):
        if not NEG.search(text[max(0, m.start() - 24):m.start()]):
            return True
    return False


def is_reusable(cmd):
    """Long and reusable = a loop / xargs / find -exec, OR a pipeline of 2+ pipes, OR >= LONG_CHARS on one command."""
    cmd = skeleton(cmd)
    if len(cmd) >= LONG_CHARS:
        return True
    if LOOPS.search(cmd):
        return True
    return len(re.findall(r"(?<!\|)\|(?!\|)", cmd)) >= 2


def real_user_text(entry):
    if entry.get("type") != "user" or entry.get("isMeta"):
        return None
    if entry.get("isCompactSummary") or entry.get("isVisibleInTranscriptOnly"):   # a summary quotes old words back
        return None
    origin = entry.get("origin")
    if origin is not None and (not isinstance(origin, dict) or origin.get("kind") != "human"):   # not typed by the person
        return None
    c = (entry.get("message") or {}).get("content")
    parts = []
    if isinstance(c, str):
        parts = [c]
    elif isinstance(c, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
            return None
        parts = [b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text"]
    text = REMINDER.sub("", "\n".join(parts)).strip()
    return text or None


def tool_uses(entry):
    if entry.get("type") != "assistant":
        return []
    c = (entry.get("message") or {}).get("content")
    return [b for b in c if isinstance(b, dict) and b.get("type") == "tool_use"] if isinstance(c, list) else []


def analyse(path, saved):
    ents = []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            ents.append(json.loads(line))
        except Exception:
            continue
    users = [i for i, e in enumerate(ents) if real_user_text(e)]
    if not users:
        return None
    last = users[-1]; prev = users[-2] if len(users) > 1 else None
    said = real_user_text(ents[last]) or ""
    said_prev = (real_user_text(ents[prev]) or "") if prev is not None else ""
    keep = has_keep_intent(said) or has_keep_intent(said_prev)

    def window(a, b):
        cmds, wrote = [], False
        for e in ents[a + 1:b]:
            for u in tool_uses(e):
                if u.get("name") in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
                    wrote = True
                elif u.get("name") == "Bash":
                    cmds.append(str((u.get("input") or {}).get("command", "")))
        return cmds, wrote
    cmds, wrote = window(last, len(ents))
    if not cmds and has_keep_intent(said) and prev is not None:   # "keep it" said AFTER the command ran
        cmds, wrote = window(prev, last)
    if wrote or saved or any(writes_file(c) for c in cmds):   # a Bash redirect / heredoc / tee / cp / mv that writes a file IS a file saved
        return None
    cmds = [c for c in cmds if len(skeleton(c)) >= MIN_CHARS]
    if not cmds:
        return None
    if keep:
        return ("keep", cmds[-1])
    reus = [c for c in cmds if is_reusable(c)]
    return ("offer", reus[-1]) if reus else None


def main():
    try:
        path, saved, state = sys.argv[1], sys.argv[2] == "1", sys.argv[3]
        r = analyse(path, saved)
        if not r:
            return
        kind, cmd = r
        sha = "cmd:" + hashlib.sha256(cmd.encode("utf-8", "replace")).hexdigest()[:16]
        try:
            seen = open(state, encoding="utf-8").read().split("\n")
        except OSError:
            seen = []
        if sha in seen or (kind == "offer" and "offer" in seen):
            return
        with open(state, "a", encoding="utf-8") as f:
            f.write(sha + "\n" + ("offer\n" if kind == "offer" else ""))
        print(kind + "\t" + " ".join(cmd.split())[:400])
    except Exception:
        return


if __name__ == "__main__":
    main()
