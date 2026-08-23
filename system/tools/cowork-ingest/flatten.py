#!/usr/bin/env python3
"""
flatten.py — Deterministic, zero-LLM ChatGPT-export → clean-text converter.

The mechanical PULL of the bulk world-model ingestion (project `cowork-bulk-ingestion`).
Turns the raw OpenAI account-export
(a list of conversations, each a message TREE) into one clean, linear, role-labeled text
file per conversation. Deterministic, no LLM, no network, no third-party deps.

WHY OUR OWN (not convoviz / a library): research found no canonical maintained library and
DIY is dominant practice — the format is simple + stable, and a ~150-line auditable parser
we own beats a dependency we'd have to trust on a personal data export. convoviz's parser was
referenced READ-ONLY for the gotchas below; nothing was installed.

WHAT IT DOES NOT DO (by design): no sanitization, no injection scan. This is the pure
STRUCTURAL pull. The controller sanitizes each file's text through `shared/gate/ingest_gate.py
gate()` AFTER this runs, before the reader ever sees it (see the project's SENTINEL WIRING).
Keeping this tool dependency-free keeps it trivially auditable.

The 9 gotchas handled (from the /research pass):
  1. active-branch walk — follow `current_node` → `parent` to the root, reverse; a chat is a
     TREE (edits/regens fork it), and only the active branch is the "real" conversation.
  2. skip the root sentinel node (its `message` is null).
  3. filter roles — keep only user + assistant; drop system / tool / browser / python.
  4. guard null messages (a node can exist with `message: null`).
  5. non-text parts are dicts (image/audio/file pointers) → type-check; never str() a dict.
  6. join multiple parts into one message body.
  7. ms-vs-seconds timestamps → normalize (values > 1e12 are ms).
  8. missing/invalid `current_node` → DFS fallback (deepest leaf by create_time).
  9. list-vs-split export format → accept either a bare list or {"conversations": [...]}.

Output (one file per conversation, to --out):
  {short_id}-{slug}.txt  — provenance header + role-labeled linear turns.
  _manifest.json         — {conversation_id: {file, title, msg_count, chars, created, updated}}

Usage:
  python3 flatten.py --raw <export-dir-with-conversations-*.json> --out <dir> [--limit N]
"""
import argparse, glob, json, os, re, sys, time
from datetime import datetime, timezone

TEXT_ROLES = {"user", "assistant"}   # gotcha #3


def iso(ts):
    """Epoch (seconds or ms) → ISO date. gotcha #7: normalize ms → s."""
    try:
        ts = float(ts)
    except (TypeError, ValueError):
        return None
    if ts > 1e12:            # milliseconds, not seconds
        ts /= 1000.0
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        return None


def slugify(title, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return (s[:60] or fallback)


def message_text(msg):
    """Extract readable body from one message. gotchas #5 (dict parts) + #6 (join parts).
    Returns "" for content we deliberately drop (thoughts, tool output, empty)."""
    content = msg.get("content") or {}
    ctype = content.get("content_type")
    if ctype == "text":
        parts = content.get("parts") or []
        return "\n".join(p for p in parts if isinstance(p, str)).strip()
    if ctype == "multimodal_text":
        out = []
        for p in content.get("parts") or []:
            if isinstance(p, str):
                out.append(p)
            elif isinstance(p, dict):                    # image/audio/file pointer, not text
                out.append(f"[{p.get('content_type', 'non-text')}]")
        return "\n".join(out).strip()
    if ctype == "code":                                  # user/assistant code blocks
        t = content.get("text")
        return t.strip() if isinstance(t, str) else ""
    # thoughts / reasoning_recap / tether_* / execution_output / user_editable_context → drop
    return ""


def is_hidden(msg):
    """Skip messages the UI hides (custom-instructions context, etc.)."""
    meta = msg.get("metadata") or {}
    return bool(meta.get("is_visually_hidden_from_conversation"))


def active_branch(mapping, current_node):
    """gotcha #1: walk current_node → parent to root, then reverse to chronological order.
    gotcha #8: if current_node is missing/invalid, fall back to the deepest leaf by create_time."""
    if not (current_node and current_node in mapping):
        current_node = _deepest_leaf(mapping)
    chain, seen, nid = [], set(), current_node
    while nid and nid not in seen:                        # `seen` guards a malformed cycle
        seen.add(nid)
        node = mapping.get(nid)
        if not isinstance(node, dict):
            break
        chain.append(node)
        nid = node.get("parent")
    chain.reverse()
    return chain


def _deepest_leaf(mapping):
    """DFS fallback: the leaf (no children) whose message has the latest create_time."""
    best_id, best_t = None, -1.0
    for nid, node in mapping.items():
        if not isinstance(node, dict) or node.get("children"):
            continue                                      # not a leaf
        msg = node.get("message") or {}
        t = msg.get("create_time") or 0.0
        try:
            t = float(t)
        except (TypeError, ValueError):
            t = 0.0
        if t >= best_t:
            best_t, best_id = t, nid
    return best_id


def flatten_conversation(c):
    """One conversation → (header_meta, list-of-(role, text)). Never raises on a bad chat."""
    mapping = c.get("mapping") or {}
    turns = []
    for node in active_branch(mapping, c.get("current_node")):
        msg = node.get("message")
        if not isinstance(msg, dict):                     # gotchas #2 + #4: root sentinel / null message
            continue
        role = (msg.get("author") or {}).get("role")
        if role not in TEXT_ROLES:                        # gotcha #3
            continue
        if is_hidden(msg):
            continue
        text = message_text(msg)
        if text:
            turns.append((role, text))
    title = (c.get("title") or "(untitled)").strip().replace("\n", " ")
    meta = {
        "conversation_id": c.get("conversation_id") or c.get("id"),
        "title": title[:120],
        "created": iso(c.get("create_time")),
        "updated": iso(c.get("update_time")) or iso(c.get("create_time")),
    }
    return meta, turns


def render(meta, turns):
    """Clean text: provenance header (research: always stamp source) + role-labeled turns."""
    lines = [
        f"# {meta['title']}",
        f"# conversation_id: {meta['conversation_id']}",
        f"# created: {meta['created']} · updated: {meta['updated']}",
        f"# turns: {len(turns)}",
        "",
    ]
    for role, text in turns:
        lines.append(f"## {role}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def load_shard(path):
    """gotcha #9: accept a bare list OR {"conversations": [...]}."""
    with open(path) as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("conversations") or [data]
    return data if isinstance(data, list) else [data]


def main():
    ap = argparse.ArgumentParser(description="ChatGPT export → clean linear text (deterministic)")
    ap.add_argument("--raw", required=True, help="dir containing conversations-*.json shards")
    ap.add_argument("--out", required=True, help="output dir for per-conversation .txt + _manifest.json")
    ap.add_argument("--limit", type=int, default=None, help="cap conversations (for a quick verify run)")
    args = ap.parse_args()

    # ⛔ DASH-OPTIONAL AND RECURSIVE (2026-08-09). This globbed `conversations-*.json` — with a literal
    # dash, top level only. A real ChatGPT export is `conversations.json`, SINGULAR, so this matched
    # nothing on a genuine export and only ever worked on a manually-sharded corpus. Detection upstream
    # was fixed first, which made this WORSE for a moment: the format was recognised and then produced
    # "no conversations-*.json under ...", which reads like a deeper failure instead of a naming one.
    # Fix both ends of a rename, or the second half becomes a more confusing version of the first.
    shards = sorted(set(glob.glob(os.path.join(args.raw, "**", "conversations*.json"), recursive=True))
                    - set(glob.glob(os.path.join(args.raw, "**", "_manifest.json"), recursive=True)))
    if not shards:
        print(f"ERROR: no conversations*.json anywhere under {args.raw}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()
    manifest, written, skipped_empty, used_fallback = {}, 0, 0, 0
    seen_names = set()

    for sp in shards:
        for c in load_shard(sp):
            if args.limit and written >= args.limit:
                break
            meta, turns = flatten_conversation(c)
            if not turns:
                skipped_empty += 1
                continue
            cid = meta["conversation_id"] or "unknown"
            short = re.sub(r"[^a-z0-9]", "", str(cid).lower())[:8] or "noid"
            name = f"{short}-{slugify(meta['title'], short)}.txt"
            while name in seen_names:                      # guarantee uniqueness
                name = f"{short}-{len(seen_names)}-{slugify(meta['title'], short)}.txt"
            seen_names.add(name)
            body = render(meta, turns)
            with open(os.path.join(args.out, name), "w") as fh:
                fh.write(body)
            manifest[cid] = {
                "file": name,
                "title": meta["title"],
                "msg_count": len(turns),
                "chars": sum(len(t) for _, t in turns),
                "created": meta["created"],
                "updated": meta["updated"],
            }
            written += 1

    with open(os.path.join(args.out, "_manifest.json"), "w") as fh:
        json.dump({
            "generated_at": iso(time.time()),
            "shards": len(shards),
            "conversations_written": written,
            "skipped_empty": skipped_empty,
            "rows": manifest,
        }, fh, indent=2)

    dt = time.time() - t0
    print(f"OK: flattened {written} conversations from {len(shards)} shards in {dt:.1f}s "
          f"({skipped_empty} empty skipped)")
    print(f"  wrote {written} .txt + _manifest.json → {args.out}")


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()
