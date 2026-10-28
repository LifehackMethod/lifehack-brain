#!/usr/bin/env python3
"""territory_walk — the live inventory the territory map is rebuilt from.

WHY THIS EXISTS. archivist-audit check 8 rebuilds `<notes>/system/canon-purpose-map.md` every week.
Until this tool, nothing in that check walked the tree: a model was asked, in one sentence, to
"rebuild" the map "with every home", and the only inputs it reliably had were the PREVIOUS map and
`docs/data-layout.md`. So it edited the old map forward. A folder neither of those named was never
seen, a folder that had been removed stayed listed, and every count in the map (projects per
subject, archive folders, packages in a staging folder) was copied from last week rather than
counted. The prose was confident and the map was wrong in exactly the places that had changed.

WHAT IT DOES. Walks the notes tree from the root, every run, and prints an inventory the
orchestrating session hands to the archivist as ground truth:

  declared     the folder matches a path `docs/data-layout.md` declares
  mapped       the previous map names it — as a path, or as a folder name written inside an
               ancestor's row. A folder named only that second way is an ITEM the row lists (a
               package, a dated folder): it is counted, and its insides are content, not homes.
  UNMAPPED     neither names it. Listed with its first-seen date, never skipped. Only the topmost
               unmapped folder is listed; what is under it is counted, not itemised.
  MISSING      the previous map has a row for it and it is no longer on disk. Never carried forward.
  not-created  the layout declares it and it does not exist yet — normal on a young install.
  tool-config  a dot-folder (an app's own settings, e.g. an editor vault folder). Listed on purpose,
               never descended, never reported as unmapped — it is not a home anyone files into.
  archive      a folder whose name starts with `_` and contains "archive". Counted per parent,
               never descended — an archive is a sealed bundle, not a home.

and COUNTS, every one from the filesystem on this run: files and sub-folders in each home, project
folders, projects per subject (from each brief's `desk:` line and from the registry), archive
folders per parent, and `.bak` files per folder.

Folders matched by a placeholder (`state/projects/<slug>/`, a dated folder) are grouped into one
line with a count, so a tree with forty projects does not produce forty lines.

GUARDS. Read-only. No network, no model. It never writes inside the notes root: `--out` refuses any
path there, so a dry run can never touch the map it is checking. Nothing here names any one
person's folders — every rule above is derived from the layout spec, the previous map, or the
shape of a name.

Exit: 0 = ran (clean or not) · 1 = tool broke · 2 = no notes root.

Usage:
  python3 system/tools/territory_walk.py                    # markdown inventory to stdout
  python3 system/tools/territory_walk.py --json             # the same, as one JSON object
  python3 system/tools/territory_walk.py --root <notes> --map <old-map.md> --out <file outside notes>
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

CODE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_LAYOUT = os.path.join(CODE_ROOT, "docs", "data-layout.md")
NOISE = {".DS_Store", "Icon\r", "desktop.ini", "Thumbs.db"}
ARCHIVE_RE = re.compile(r"^_.*archive", re.I)
PLACEHOLDER_RE = re.compile(r"\\?<[^>]+>|YYYY[-\w.]*|\{[^}]+\}")
WORD_RE = re.compile(r"[A-Za-z0-9_][\w.-]*[\w]")


# ── what is declared ──────────────────────────────────────────────────────────────────────────

def _norm(tok):
    tok = tok.strip().strip("`").strip()
    if tok.startswith("<notes>/"):
        tok = tok[len("<notes>/"):]
    tok = PLACEHOLDER_RE.sub("*", tok)          # `<slug>` -> `*`; `*.bak` stays a FILE glob, not "anything"
    return tok.strip("/")


def _looks_like_path(tok):
    return ("/" in tok or "." in tok) and " " not in tok and not tok.startswith(("http", "-"))


def parse_layout(text):
    """Paths docs/data-layout.md declares. Returns (patterns, literal_paths).

    Two sources, both read: the fenced tree drawings that start with a `<notes>/...` line (the
    spec's own picture of the shape), and backticked `<notes>/...` tokens in prose and tables. A
    single-segment `name/` token is a record type (the "Types of record" table) and is declared
    under every `records/` folder. Backticks pair within a line only — a fenced block in between
    must never shift every later token by one."""
    patterns, literals = set(), set()

    def add(tok):
        p = _norm(tok)
        if p:
            patterns.add(p)
            if "*" not in p:
                literals.add(p)

    in_fence, base, stack = False, None, []
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence, base, stack = not in_fence, None, []
            continue
        if in_fence:
            s = line.strip()
            if base is None:
                if s.startswith("<notes>/"):
                    base = _norm(s.split()[0])
                    add(s.split()[0])
                continue
            m = re.match(r"^([│ ]*)[├└]── (\S+)", line)
            if m:
                stack = stack[:len(m.group(1)) // 4] + [m.group(2).rstrip("/")]
                add("/".join([base] + stack if base else stack))
            continue
        for tok in re.findall(r"`([^`]+)`", line):
            if tok.startswith("<notes>/"):
                add(tok)
            elif re.fullmatch(r"[a-z][\w-]*/", tok):
                patterns.add("**/records/" + tok.rstrip("/"))
    return patterns, literals


def parse_map(text):
    """Paths the previous map names. Returns (patterns, row_kids, row_literals).

    Every backticked path anywhere counts as named. In a table row, the first cell is the home, and
    a folder name written anywhere else in that row — `hooks/`, "(context/, logs/)", or a plain list
    of package names — names a sub-folder of it, at any depth below. Only first-cell literals are
    candidates for MISSING: prose that says a folder is gone must never be read as a claim that the
    folder exists."""
    patterns, row_kids, row_literals = set(), {}, set()
    for line in text.splitlines():
        for tok in re.findall(r"`([^`]+)`", line):
            if _looks_like_path(tok):
                p = _norm(tok)
                if p:
                    patterns.add(p)
    for line in text.splitlines():
        if not line.startswith("|") or re.match(r"^\|[\s:|-]+\|?\s*$", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        homes = [_norm(t) for t in re.findall(r"`([^`]+)`", cells[0]) if _looks_like_path(t)]
        homes = [h for h in homes if h]
        if not homes:
            continue
        words = {w for w in WORD_RE.findall(" ".join(cells[1:]).replace("`", " ")) if len(w) > 1}
        for h in homes:
            if "*" not in h:
                row_literals.add(h)
            row_kids.setdefault(h, set()).update(words)
    return patterns, row_kids, row_literals


def _rx(pattern):
    out = []
    for seg in pattern.split("/"):
        out.append("(?:[^/]+/)*" if seg == "**" else re.escape(seg).replace(r"\*", "[^/]*") + "/")
    return re.compile("^" + "".join(out).rstrip("/") + "$")


def _anchored(p):
    """A pattern whose first segment is a wildcard matches every top-level folder and would hide any
    unmapped one — only the record-type rule (`**/records/<type>`) may float."""
    first = p.split("/")[0]
    return p.startswith("**/records/") or "*" not in first


class Declared:
    def __init__(self, patterns, row_kids=None):
        self.patterns = sorted(p for p in patterns if _anchored(p))
        self._rx = [(p, _rx(p)) for p in self.patterns]
        self._kids = [(_rx(h + "/**"), kids) for h, kids in sorted((row_kids or {}).items()) if _anchored(h)]

    def match(self, rel):
        """The pattern `rel` matches, or the pattern it is an ancestor of; None if neither."""
        for p, rx in self._rx:
            if rx.match(rel):
                return p
        if self.named_in_row(rel):
            return rel
        for p, _ in self._rx:
            if "**" in p:
                continue
            segs = p.split("/")
            rsegs = rel.split("/")
            if len(rsegs) < len(segs) and all(s == "*" or s == r for s, r in zip(segs, rsegs)):
                return "/".join(segs[:len(rsegs)])
        return None

    def named_in_row(self, rel):
        """True when `rel` is named only as a word inside an ancestor's row — an item that row lists
        (a package, a dated folder), not a home with structure of its own."""
        parent, _, name = rel.rpartition("/")
        return bool(parent) and any(name in kids and rx.match(parent + "/") for rx, kids in self._kids)


# ── the walk ──────────────────────────────────────────────────────────────────────────────────

def _first_seen(path):
    st = os.stat(path)
    t = getattr(st, "st_birthtime", None) or st.st_mtime
    return datetime.date.fromtimestamp(t).isoformat()


def _children(path):
    try:
        names = [n for n in os.listdir(path) if n not in NOISE]
    except OSError as e:
        return None, None, str(e)
    dirs = sorted(n for n in names if os.path.isdir(os.path.join(path, n)))
    files = sorted(n for n in names if not os.path.isdir(os.path.join(path, n)))
    return dirs, files, None


def _subtree_size(path):
    nd = nf = 0
    for _, ds, fs in os.walk(path):
        nd += len(ds)
        nf += len([f for f in fs if f not in NOISE])
    return nd, nf


def walk(root, layout, named, depth):
    entries = {}            # key -> entry; a key is a literal path or a grouped pattern
    archives, baks, unreadable = {}, {}, []

    def add(rel, status, matched, full, dirs, files):
        # Group folders a placeholder matched (`projects/<slug>`, `projects/<slug>/records`) into one
        # line. Never group on the floating record-type rule: `desks/a/records/context` and
        # `desks/b/records/context` are each a home worth seeing.
        grouped = matched is not None and "*" in matched.split("/") and \
            "**" not in matched and status in ("declared", "mapped")
        key = matched if grouped else rel
        e = entries.setdefault(key, {"path": key, "status": status, "grouped": grouped, "folders": 0,
                                     "files": 0, "subfolders": 0, "first_seen": None})
        e["folders"] += 1
        e["files"] += len(files or [])
        e["subfolders"] += len([d for d in (dirs or []) if not d.startswith(".") and not ARCHIVE_RE.match(d)])
        fs = _first_seen(full)
        if e["first_seen"] is None or fs < e["first_seen"]:
            e["first_seen"] = fs

    def visit(rel, level):
        full = os.path.join(root, rel) if rel else root
        dirs, files, err = _children(full)
        if err:
            unreadable.append({"path": rel or ".", "error": err})
            return
        b = [f for f in files if f.endswith(".bak")]
        if b:
            baks[rel or "."] = len(b)
        n_arch = [d for d in dirs if ARCHIVE_RE.match(d)]
        if n_arch:
            archives[rel or "."] = len(n_arch)
        if level >= depth:
            return
        for d in dirs:
            if ARCHIVE_RE.match(d):
                continue
            crel = f"{rel}/{d}" if rel else d
            cfull = os.path.join(root, crel)
            if d.startswith("."):
                nd, nf = _subtree_size(cfull)
                entries[crel] = {"path": crel, "status": "tool-config", "grouped": False, "folders": 1,
                                 "files": nf, "subfolders": nd, "first_seen": _first_seen(cfull),
                                 "named_in_map": bool(named.match(crel))}
                continue
            m_layout = layout.match(crel)
            m_named = named.match(crel)
            if m_layout or m_named:
                status = "declared" if m_layout else "mapped"
                cd, cf, _ = _children(cfull)
                add(crel, status, m_layout or m_named, cfull, cd, cf)
                if m_layout or not named.named_in_row(crel) or crel in named.patterns:
                    visit(crel, level + 1)      # an item a row merely lists is content: not descended
            else:
                nd, nf = _subtree_size(cfull)
                entries[crel] = {"path": crel, "status": "UNMAPPED", "grouped": False, "folders": 1,
                                 "files": nf, "subfolders": nd, "first_seen": _first_seen(cfull)}

    visit("", 0)
    _, root_files, _ = _children(root)
    loose = [f for f in (root_files or [])
             if not f.startswith(".") and not layout.match(f) and not named.match(f)]
    return entries, archives, baks, unreadable, loose


# ── counts that are about the system's own vocabulary ─────────────────────────────────────────

def project_counts(root):
    """Projects per subject, two ways: each brief's `desk:` line, and the registry's rows."""
    by_brief, folders = {}, 0
    pdir = os.path.join(root, "state", "projects")
    if os.path.isdir(pdir):
        for slug in sorted(os.listdir(pdir)):
            if not os.path.isdir(os.path.join(pdir, slug)) or slug.startswith((".", "_")):
                continue
            folders += 1
            desk = "(no desk: line)"
            brief = os.path.join(pdir, slug, "brief.md")
            if os.path.isfile(brief):
                with open(brief, encoding="utf-8", errors="replace") as f:
                    for line in f.read(4000).splitlines():
                        m = re.match(r"^\s*\**desk\**\s*:\s*\**\s*`?([\w-]+)", line, re.I)
                        if m:
                            desk = m.group(1)
                            break
            else:
                desk = "(no brief.md)"
            by_brief[desk] = by_brief.get(desk, 0) + 1
    by_registry = {}
    reg = os.path.join(root, "system", "project-registry.md")
    if os.path.isfile(reg):
        with open(reg, encoding="utf-8", errors="replace") as f:
            for line in f:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 5 and re.fullmatch(r"[a-z0-9][\w-]*", cells[0]) and \
                        re.fullmatch(r"[a-z0-9][\w-]*", cells[1]) and cells[0] != "desk":
                    by_registry[cells[0]] = by_registry.get(cells[0], 0) + 1
    desks = []
    ddir = os.path.join(root, "desks")
    if os.path.isdir(ddir):
        desks = sorted(d for d in os.listdir(ddir)
                       if os.path.isdir(os.path.join(ddir, d)) and not d.startswith((".", "_")))
    per_desk = {d: {"briefs": by_brief.get(d, 0), "registry": by_registry.get(d, 0)} for d in desks}
    for d in sorted(set(by_brief) | set(by_registry)):
        if d not in per_desk:
            per_desk[d] = {"briefs": by_brief.get(d, 0), "registry": by_registry.get(d, 0),
                           "no_desk_folder": True}
    return {"project_folders": folders, "registry_rows": sum(by_registry.values()), "per_desk": per_desk}


# ── assemble ──────────────────────────────────────────────────────────────────────────────────

def inventory(root, map_text, layout_text, depth=4):
    l_pat, l_lit = parse_layout(layout_text)
    m_pat, m_kids, m_rows = parse_map(map_text)
    layout, named = Declared(l_pat), Declared(m_pat | l_pat, m_kids)
    entries, archives, baks, unreadable, loose = walk(root, layout, named, depth)
    on_disk = lambda p: os.path.exists(os.path.join(root, p))
    missing = sorted(p for p in m_rows if not on_disk(p) and not ARCHIVE_RE.match(os.path.basename(p)))
    not_created = sorted(p for p in l_lit if not on_disk(p) and p not in missing)
    rows = sorted(entries.values(), key=lambda e: e["path"])
    return {
        "root": root,
        "generated": datetime.date.today().isoformat(),
        "depth": depth,
        "homes": rows,
        "unmapped": [e for e in rows if e["status"] == "UNMAPPED"],
        "tool_config": [e for e in rows if e["status"] == "tool-config"],
        "missing": missing,
        "not_created": not_created,
        "loose_root_files": loose,
        "archive_folders": archives,
        "bak_files": baks,
        "projects": project_counts(root),
        "unreadable": unreadable,
    }


def render(inv):
    o = [f"# Territory inventory — {inv['generated']}", "",
         f"Walked live from the notes root to depth {inv['depth']}. Every number below was counted on "
         "this run; none is carried from an earlier map.", ""]

    def section(title, items, fmt, empty="none"):
        o.append(f"## {title}")
        if items:
            o.extend(fmt(i) for i in items)
        else:
            o.append(f"- {empty}")
        o.append("")

    section("UNMAPPED — on disk, named by neither the layout spec nor the previous map", inv["unmapped"],
            lambda e: f"- `{e['path']}/` — first seen {e['first_seen']} · {e['subfolders']} sub-folders, "
                      f"{e['files']} files under it")
    section("MISSING — the previous map lists it, it is not on disk (drop it; never carry it forward)",
            inv["missing"], lambda p: f"- `{p}`")
    section("Tool config — app settings folders, listed on purpose, not homes", inv["tool_config"],
            lambda e: f"- `{e['path']}/` — first seen {e['first_seen']} · {e['files']} files")
    section("Loose files at the root, named by neither", inv["loose_root_files"], lambda f: f"- `{f}`")
    o += ["## Every home on disk", "", "| path | status | folders | sub-folders | files | first seen |",
          "|---|---|---|---|---|---|"]
    for e in inv["homes"]:
        if e["status"] in ("declared", "mapped"):
            p = e["path"] + "/" + (" (grouped)" if e["grouped"] else "")
            o.append(f"| `{p}` | {e['status']} | {e['folders']} | {e['subfolders']} | {e['files']} | "
                     f"{e['first_seen']} |")
    o.append("")
    pc = inv["projects"]
    o += ["## Projects", "", f"- project folders in `state/projects/`: {pc['project_folders']}",
          f"- registry rows: {pc['registry_rows']}", "", "| subject | projects (brief `desk:`) | registry rows |",
          "|---|---|---|"]
    for d, c in pc["per_desk"].items():
        flag = " (no folder under desks/)" if c.get("no_desk_folder") else ""
        o.append(f"| {d}{flag} | {c['briefs']} | {c['registry']} |")
    o.append("")
    section("Archive folders, per parent", sorted(inv["archive_folders"].items()),
            lambda kv: f"- `{kv[0]}/`: {kv[1]}")
    section("`.bak` files, per folder", sorted(inv["bak_files"].items()), lambda kv: f"- `{kv[0]}/`: {kv[1]}")
    section("Layout paths not created yet (normal on a young install)", inv["not_created"], lambda p: f"- `{p}`")
    section("Could not read (never the same as empty)", inv["unreadable"],
            lambda u: f"- `{u['path']}` — {u['error']}")
    return "\n".join(o)


def _resolve_root():
    r = subprocess.run([sys.executable, os.path.join(CODE_ROOT, "shared", "brain_root.py"), "--quiet"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _read(path):
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    return ""


def main(argv=None):
    ap = argparse.ArgumentParser(description="Walk the notes tree live and print the inventory the "
                                             "territory map (archivist-audit check 8) is rebuilt from.")
    ap.add_argument("--root", help="notes root (default: shared/brain_root.py)")
    ap.add_argument("--map", help="previous map (default: <root>/system/canon-purpose-map.md)")
    ap.add_argument("--layout", default=DEFAULT_LAYOUT, help="layout spec (default: docs/data-layout.md)")
    ap.add_argument("--depth", type=int, default=4, help="how many folder levels hold homes (default 4)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of markdown")
    ap.add_argument("--out", help="write here instead of stdout — refused if inside the notes root")
    a = ap.parse_args(argv)

    root = a.root or _resolve_root()
    if not root or not os.path.isdir(root):
        print("territory_walk: no notes root set — nothing to walk. "
              "Set one: python3 shared/brain_root.py --set <folder>", file=sys.stderr)
        return 2
    root = os.path.realpath(root)
    if a.out:
        out = os.path.realpath(a.out)
        if out == root or out.startswith(root + os.sep):
            print(f"territory_walk: refusing to write inside the notes root: {a.out}", file=sys.stderr)
            return 1
    try:
        inv = inventory(root, _read(a.map or os.path.join(root, "system", "canon-purpose-map.md")),
                        _read(a.layout), a.depth)
        text = json.dumps(inv, indent=1) if a.json else render(inv)
    except Exception as e:  # a broken walk is never reported as a clean one
        print(f"territory_walk: ERROR: {e}", file=sys.stderr)
        return 1
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
