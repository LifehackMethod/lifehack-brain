#!/usr/bin/env python3
"""
agent_output.py — pull a background sub-agent's FINAL output straight from its transcript.

WHY: the tool-less readers (Read-only, by security design — see SOP §5) can't write their own output, so
the controller used to HAND-COPY each reader's returned JSON into a file with the Write tool — slow, and
it once garbled the display. But Claude Code already persists every sub-agent's full transcript at
`~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl`. So the controller passes the agent
labels and THIS tool extracts each reader's final JSON array from its transcript — no hand-copying, no
untrusted text re-typed through the main session.

The extracted text is still UNTRUSTED (a reader read adversarial content) — it is handed to `scan_collect.py`,
which re-gates every gist before anything is stored. This tool only LOCATES + EXTRACTS; it never trusts.

ID/label handling (Bug C fix, 2026-07-12): the Task tool returns a label like `cw-r000` (sometimes
`cw-r000@session-<id>`), but the transcript file is named `agent-a<label>-<hash>.jsonl` — a leading `a`
plus a hash suffix. So we strip any `@…`, then try BOTH `agent-<label>*` and `agent-a<label>*` (newest wins).

SendMessage fallback (Bug B fix, 2026-07-12): a reader spawned as an addressable teammate is handed a
SendMessage tool and may ship its JSON via SendMessage instead of returning it as final text. If the final
assistant text isn't parseable JSON, we recover the last SendMessage payload from the transcript. (The real
fix is to spawn readers WITHOUT teammate names so they stay tool-less — see phases/3-deep-read.md — but this
keeps the collector robust either way.)

Split-answer fix (Bug F5.1, 2026-08-04): a long reader answer can spill across TWO assistant turns (the
model hits an output cap mid-array and continues in a fresh assistant message, with no tool call in
between). The old `final_text()` kept only the LAST text block, so it returned the tail fragment alone —
unparseable, and the whole bundle got silently dropped as UNPARSEABLE. It now concatenates every assistant
text block from the LAST tool-result boundary forward, so a split array reassembles whole; a normal
single-final-block answer is untouched (concatenating one block is that block).

Partial-batch fix (Bug F5.2, 2026-08-04): by default a partial batch (some readers MISS/UNPARSEABLE) still
exits 0 as long as at least one reader recovered — the pipeline can silently continue on an incomplete
batch. `--require-all N` (N = readers dispatched) makes that a hard failure: exits nonzero and names the
missing/unparseable labels when fewer than N recovered. Omit the flag and nothing changes.

Usage:
  python3 agent_output.py --agents <label1> <label2> ... --out <raw-dir>
    → writes <raw-dir>/agent-<label>.json for each (the reader's final JSON array, fence-stripped)
  python3 agent_output.py --agents <label1> <label2> ... --out <raw-dir> --raw
    → same JSON-array behavior first; for any agent where that yields nothing, falls back to writing
      the agent's content VERBATIM to <raw-dir>/agent-<label>.txt (all SendMessage payloads in transcript
      order, else the final assistant text, else UNPARSEABLE as before). Does not change the default
      (no --raw) behavior in any way; only adds a fallback path for agents that would otherwise be dropped.
"""
import argparse, glob, json, os, sys

# ⛔ FOLLOW THE CONFIG DIR. Claude Code writes every transcript under its ACTIVE config directory, and
# that is `~/.claude` only when nobody has moved it. `CLAUDE_CONFIG_DIR` moves it — which is exactly what
# the sanctioned isolated-run recipe does in order to test a repo without this machine's own hooks
# answering for it (records/context/2026-08-11-isolated-config-dir-recipe.md).
# MEASURED 2026-08-13: under that recipe the tagger ran perfectly and wrote a 42 KB and a 49 KB
# transcript into the isolated dir -- and this line looked in `~/.claude/projects`, found nothing, and
# reported `MISS: no transcript found`. The reader had done its job; the collector was looking in the
# wrong house. That single hardcode is why `/ingest` had never once been driven end to end under
# isolation -- the run dies in PHASE 1 before the first human turn.
# ⭐ A student never sets CLAUDE_CONFIG_DIR, so this changes nothing for them. It changes whether this
# tool can be TESTED at all, which is the thing that was actually broken.
PROJECTS = os.path.join(
    os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "projects")


def _norm(agent_id):
    """The Task tool may hand back `cw-r000@session-abc`; the transcript key is just `cw-r000`."""
    return (agent_id or "").split("@", 1)[0].strip()


def find_agent_file(agent_id):
    """Locate the transcript under any project's <session>/subagents/ dir (newest wins). Handles the real
    filename shape `agent-a<label>-<hash>.jsonl` AND a bare `agent-<label>-<hash>.jsonl`."""
    aid = _norm(agent_id)
    pats = [f"agent-{aid}.jsonl", f"agent-{aid}-*.jsonl", f"agent-{aid}*.jsonl",
            f"agent-a{aid}-*.jsonl", f"agent-a{aid}*.jsonl"]
    hits = []
    for pat in pats:
        hits += glob.glob(os.path.join(PROJECTS, "*", "*", "subagents", pat))
    hits = sorted(set(hits), key=lambda p: os.path.getmtime(p), reverse=True)
    return hits[0] if hits else None


def _assistant_content(path):
    """Yield each assistant message's content list, in transcript order."""
    with open(path, errors="replace") as fh:
        for ln in fh:
            try:
                d = json.loads(ln)
            except Exception:
                continue
            m = d.get("message") or {}
            if isinstance(m, dict) and m.get("role") == "assistant":
                yield (m.get("content") or [])


def final_text(path):
    """The reader's final answer: every assistant TEXT block from the LAST tool-result boundary forward,
    concatenated in transcript order (F5.1). A tool-less reader that reads its bundle via `Read` (or any
    reader that calls a tool) leaves a `tool_result` block behind each round-trip; everything the model
    says AFTER the last one is its final answer, even if that answer itself spans two+ assistant turns
    because it hit an output cap mid-array. Only text blocks before that last boundary (earlier chatter,
    e.g. commentary before a tool call) are excluded. A transcript with no tool call at all has no
    boundary, so every assistant text block counts — there is no "earlier chatter" to exclude when nothing
    but the model's own continuing answer produced it.
    For the common case — one trailing text block — this returns exactly that block, unchanged from before."""
    texts = []       # [(line_idx, text), ...] every non-empty assistant text block, in transcript order
    boundary = -1     # line_idx of the last tool_result block seen
    idx = -1
    with open(path, errors="replace") as fh:
        for ln in fh:
            idx += 1
            try:
                d = json.loads(ln)
            except Exception:
                continue
            m = d.get("message") or {}
            if not isinstance(m, dict):
                continue
            content = m.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_result":
                    boundary = idx
                elif m.get("role") == "assistant" and c.get("type") == "text" and (c.get("text") or "").strip():
                    texts.append((idx, c["text"]))
    trailing = [t for i, t in texts if i > boundary]
    return "".join(trailing) if trailing else None


def sendmessage_payload(path):
    """Bug B fallback: dig out the last SendMessage tool_use payload (a reader that was handed a messaging
    tool may have shipped its JSON there instead of returning it as final text)."""
    last = None
    for content in _assistant_content(path):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                name = (c.get("name") or "").lower().replace("_", "")
                if "sendmessage" in name:
                    inp = c.get("input") or {}
                    msg = inp.get("message") or inp.get("content") or inp.get("body") or ""
                    if isinstance(msg, str) and msg.strip():
                        last = msg
    return last


def all_sendmessage_payloads(path):
    """--raw fallback: collect EVERY SendMessage tool_use payload in transcript order (generalizes
    sendmessage_payload(), which only keeps the last). Used when an agent's report is prose that never
    parses as a JSON array but is still sitting in the transcript across one or more SendMessage calls."""
    out = []
    for content in _assistant_content(path):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                name = (c.get("name") or "").lower().replace("_", "")
                if "sendmessage" in name:
                    inp = c.get("input") or {}
                    msg = inp.get("message") or inp.get("content") or inp.get("body") or ""
                    if isinstance(msg, str) and msg.strip():
                        out.append(msg)
    return out


def strip_fence(t):
    """Drop a leading ```json fence + trailing ``` if present, so the file is a bare JSON array."""
    t = (t or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _json_ok(t):
    t = (t or "").strip()
    if not t:
        return False
    try:
        json.loads(t)
        return True
    except Exception:
        return False


def extract_json_array(t):
    """Robustly pull a JSON ARRAY out of reader text that may carry a prose preamble ('Here are the
    conclusions:') or a ```json fence. Mirrors tag.extract_json_array — a reader sometimes ignores the
    'start with [' instruction, and the collector must still deliver clean parseable JSON downstream.
    Returns the array text (verbatim substring) or '' if none is found."""
    t = strip_fence(t or "")
    cands = [t]
    if "[" in t and "]" in t:
        cands.append(t[t.find("["): t.rfind("]") + 1])   # first '[' .. last ']' — drops a prose preamble
    for cand in cands:
        try:
            if isinstance(json.loads(cand), list):
                return cand.strip()
        except Exception:
            continue
    return ""


def main():
    ap = argparse.ArgumentParser(description="pull background reader outputs from their transcripts")
    ap.add_argument("--agents", nargs="+", required=True, help="agent labels (e.g. cw-r000); @session suffix ok")
    ap.add_argument("--out", required=True, help="dir to write agent-<label>.json into")
    ap.add_argument("--raw", action="store_true", default=False,
                     help="when JSON extraction yields nothing for an agent, fall back to writing its "
                          "content VERBATIM to agent-<label>.txt (all SendMessage payloads in transcript "
                          "order, else the final assistant text) instead of dropping it as UNPARSEABLE")
    ap.add_argument("--require-all", type=int, default=None, metavar="N",
                     help="(F5.2) N = how many readers were dispatched. If fewer than N are recovered "
                          "(MISS or UNPARSEABLE), print which labels are missing and exit nonzero instead "
                          "of continuing on a partial batch. Omit this flag to keep today's behavior "
                          "(exit 0 as long as at least one reader recovered).")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ok = miss = empty = recovered = raw_recovered = 0
    missing_labels = []   # labels that ended up MISS or UNPARSEABLE — for --require-all's report
    for aid in a.agents:
        label = _norm(aid)
        f = find_agent_file(aid)
        if not f:
            print(f"  MISS: no transcript found for agent {label}")
            miss += 1
            missing_labels.append(f"{label} (missing)")
            continue
        txt = extract_json_array(final_text(f))    # robust: strips a prose preamble / ```json fence
        if not txt:                                # final text had no JSON array → try the SendMessage payload
            txt = extract_json_array(sendmessage_payload(f) or "")
            if txt:
                recovered += 1
        if not txt:
            if a.raw:
                payloads = all_sendmessage_payloads(f)
                raw_txt = "\n\n".join(payloads) if payloads else (final_text(f) or "")
                if raw_txt.strip():
                    with open(os.path.join(a.out, f"agent-{label}.txt"), "w") as fh:
                        fh.write(raw_txt)
                    raw_recovered += 1
                    ok += 1
                    continue
            print(f"  UNPARSEABLE: {label} had no JSON array in its final text or a SendMessage payload")
            empty += 1
            missing_labels.append(f"{label} (unparseable)")
            continue
        with open(os.path.join(a.out, f"agent-{label}.json"), "w") as fh:
            fh.write(txt)
        ok += 1
    extras = []
    if recovered:
        extras.append(f"{recovered} recovered from SendMessage")
    if raw_recovered:
        extras.append(f"{raw_recovered} recovered raw (--raw)")
    if miss:
        extras.append(f"{miss} missing")
    if empty:
        extras.append(f"{empty} empty")
    print(f"OK agent-output: pulled {ok} reader output(s) → {a.out}"
          + (f" ({', '.join(extras)})" if extras else ""))
    if a.require_all is not None and ok < a.require_all:
        print(f"FAIL agent-output: --require-all {a.require_all} but only {ok} recovered — "
              f"missing/unparseable: {', '.join(missing_labels) if missing_labels else '(none logged)'}")
        sys.exit(1)
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()
