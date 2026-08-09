#!/usr/bin/env python3
"""
folder_scaffold.py — one-punch KNOWLEDGE FOLDER scaffold (ingest SPEC §5c C2, ruled 2026-08-08).

A knowledge folder is a strict SUBSET of a desk — NOT a new format. `/ingest` PHASE 4 (`4.2`) generates one
per confirmed branch of the human's world-model tree: "we're doing folders versus desks" (verbatim, ruled
2026-08-08). It writes ONLY `canon/current.md`, `canon/purpose.md`, and an empty `records/` — the sibling of
`desk_scaffold.py` (which builds the full, heavier DESK shape: `state/`, `views/`, `sources/inbox/`,
`_registry.md`, `CLAUDE.md`, plus a hand-paste block for `system/desk-registry.yaml`). None of that belongs
here: "PHASE 4 generates canon/current.md + canon/purpose.md + records/ and NOTHING ELSE — no
desk-registry.yaml entry, no CLAUDE.md, no health_producer, no pulse_slot, no status_tile_path. Promotion to
a real DESK is a separate, deliberate human act, later, if a folder earns it." (`skills/ingest/SPEC.md` §5c
C2). `desk_scaffold.py` stays the tool for that later promotion — it is not touched or superseded by this one.

It writes the folder skeleton + two stub files ONLY. It does NOT touch `system/desk-registry.yaml`, does NOT
touch `$DRIVE/system/project-registry.md` (findability for a new knowledge folder is a separate, human/archivist
decision — see the tool's own stdout note), and does NOT create any per-machine symlink. Refuses to clobber an
existing folder, and refuses any `--topic` slug not already in the closed vocabulary
(`system/topic-vocab.md`) — this tool must never invent one.

Usage:
  folder_scaffold.py --drive-root <Lifehack dir> --path <relative/path/under/drive-root> \
      --purpose "<one-line PURPOSE, never a done-when>" --topic <slug[,slug...]> \
      [--desk <owning-desk-slug>] [--title "<display title>"] [--not "<one near-miss line>"]
"""
import argparse, os, re, sys, datetime

DIRS = ["canon", "records"]

STUB = {
    "canon/current.md": ("---\ntopic: {topic}\ntitle: {Title} — canon (standing)\nrecord_type: canon\n"
                         "desk: {desk}\ncreated_at: {d}\nupdated_at: {d}\nstatus: active\nauthority: user\n---\n\n"
                         "# {Title} — standing canon\n\n_(Human-blessed, always-true facts for {Title}. Keep it TINY.)_\n"),
    "canon/purpose.md": ("---\ntopic: {topic}\ntitle: {Title} — purpose\nrecord_type: canon\ndesk: {desk}\n"
                         "created_at: {d}\nupdated_at: {d}\nstatus: active\nauthority: user\n---\n\n"
                         "# {Title} — purpose\n\n{purpose_body}\n"),
}

# ⚖⭐ THE VOCABULARY IS THE PERSON'S OWN DATA — IT LIVES IN THEIR TIER, NOT OURS (2026-08-09).
# It used to be read from `system/topic-vocab.md`, two directories up from this script. That was wrong in
# two ways at once, and the second one is the reason this changed:
#   1. It was ABSENT from the shipped package, so this tool refused on every machine but the author's.
#   2. ⭐ The obvious fix — scrub the author's vocabulary and ship it — is WORSE than the bug. A topic
#      vocabulary is a taxonomy OF A PERSON'S LIFE. Shipping one hands every student someone else's
#      categories and quietly tells them that is how their own material should be divided.
# ⇒ The vocabulary belongs under `memory/`, beside the material it describes, OUTSIDE the git-tracked
# tier — the same ruling that applies to everything else the person writes.
#
# Resolution order, first hit wins:
#   1. --vocab <path>                       explicit, always wins
#   2. <brain root>/memory/topic-vocab.md   the person's own, the normal case
#   3. system/topic-vocab.md                legacy in-repo copy; supported so an existing install does not
#                                           break, but never shipped and never created here.
def _brain_root():
    """The folder the person opened — this file sits at <root>/system/tools/cowork-ingest/."""
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


VOCAB_PATH = os.path.join(_brain_root(), "memory", "topic-vocab.md")
LEGACY_VOCAB_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "..", "..", "topic-vocab.md"))
SLUG_RE = re.compile(r"^- `([a-z0-9-]+)`")


def resolve_vocab(explicit=None):
    """First existing path in the order above, or None. Returns (path_or_None, tried_list)."""
    tried = [p for p in (explicit, VOCAB_PATH, LEGACY_VOCAB_PATH) if p]
    for p in tried:
        if os.path.isfile(p):
            return p, tried
    return None, tried


def load_vocab(vocab_path):
    """Parse the CLOSED topic vocabulary. Stops at '## Not topics' — those entries are explicitly
    record_type/doctrine markers, not subjects, and must never validate as a topic slug."""
    if not os.path.isfile(vocab_path):
        sys.exit(f"REFUSED: cannot find the closed topic vocabulary at {vocab_path} — refusing to guess slugs.")
    slugs = set()
    with open(vocab_path) as f:
        for line in f:
            if line.strip().startswith("## Not topics"):
                break
            m = SLUG_RE.match(line.strip())
            if m:
                slugs.add(m.group(1))
    return slugs


def main():
    ap = argparse.ArgumentParser(description="scaffold a new conformant KNOWLEDGE FOLDER (canon/current.md + canon/purpose.md + records/)")
    ap.add_argument("--drive-root", required=True, help="the Lifehack root (the target path is resolved under it)")
    ap.add_argument("--path", required=True, help="the knowledge folder's path, relative to --drive-root (e.g. knowledge/example-subject)")
    ap.add_argument("--purpose", required=True, help="one-line PURPOSE — never a done-when (intent-doctrine.md)")
    ap.add_argument("--topic", required=True, help="comma-separated topic slug(s), drawn ONLY from your topic vocabulary")
    ap.add_argument("--vocab", default=None, help="explicit path to the topic vocabulary; defaults to "
                    "<brain root>/memory/topic-vocab.md (yours), then the legacy in-repo copy")
    ap.add_argument("--desk", default="root", help="owning desk slug for the frontmatter desk: field (default: root)")
    ap.add_argument("--title", default=None, help="display title (default: derived from the last path segment)")
    ap.add_argument("--not", dest="near_miss", default=None, help="OPTIONAL — the ONE near-miss line (never an exclusion list)")
    a = ap.parse_args()

    rel = a.path.strip().strip("/")
    if not rel:
        sys.exit("REFUSED: --path is empty.")
    base = os.path.join(a.drive_root, rel)
    if os.path.exists(base):
        sys.exit(f"REFUSED: '{rel}' already exists at {base} — will not clobber.")

    vocab_path, tried = resolve_vocab(getattr(a, "vocab", None))
    if vocab_path is None:
        # ⛔ REFUSE, and NAME EVERY PATH TRIED. A bare "cannot find it" sent a real person hunting through
        # a repo for a file that was never supposed to be there. The vocabulary is THEIR data; the fix is
        # to write one, not to find ours.
        sys.exit("REFUSED: no topic vocabulary found. Looked for, in order:\n"
                 + "\n".join(f"    {p}" for p in tried)
                 + "\n\n  The topic vocabulary is a list of the subject areas YOUR OWN material divides into,"
                   "\n  so it is yours to write and it lives with your notes, not in the tool.\n"
                   "  Create memory/topic-vocab.md with one line per subject:\n\n"
                   "      - `financial`\n      - `health`\n      - `writing`\n\n"
                   "  ⛔ This tool will not invent one for you — an invented taxonomy of your life is worse\n"
                   "     than no taxonomy at all.")
    vocab = load_vocab(vocab_path)
    topics = [t.strip() for t in a.topic.split(",") if t.strip()]
    if not topics:
        sys.exit("REFUSED: --topic is empty.")
    bad = [t for t in topics if t not in vocab]
    if bad:
        sys.exit(f"REFUSED: topic slug(s) not in the closed vocabulary ({vocab_path}): {bad}. "
                  f"Use an existing slug, or add it there FIRST — this tool never invents one.")

    title = a.title.strip() if a.title else rel.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ").strip().capitalize()
    d = datetime.datetime.now().strftime("%Y-%m-%d")
    topic_field = "[" + ", ".join(topics) + "]"

    purpose_body = "**intent:** " + a.purpose.strip()
    if a.near_miss:
        purpose_body += "\n**not:** " + a.near_miss.strip()

    fields = {"desk": a.desk.strip().lower(), "Title": title, "purpose_body": purpose_body,
              "d": d, "topic": topic_field}

    for sub in DIRS:
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    for relf, tmpl in STUB.items():
        p = os.path.join(base, relf)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(tmpl.format(**fields))

    print(f"OK: scaffolded knowledge folder '{rel}' at {base}")
    print("   folders:", ", ".join(DIRS))
    print("   files  :", ", ".join(STUB.keys()))
    print("\nThis is a KNOWLEDGE FOLDER — a strict subset of a desk. No state/, no views/, no sources/inbox/,")
    print("no per-folder file describing its own contents, and nothing pasted anywhere by hand. Promotion to a")
    print("full desk (health producer, pulse slot, status tile) is a separate, later, deliberate human act via")
    print("desk_scaffold.py — this tool does not do that and does not print anything for you to paste.")
    print("\nShape source: skills/ingest/SPEC.md §5c C2 · sibling tool: system/tools/cowork-ingest/desk_scaffold.py")


if __name__ == "__main__":
    main()
