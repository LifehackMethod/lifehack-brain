#!/usr/bin/env python3
"""encoding_audit.py — a repeatable CENSUS of bare `open()` calls that omit `encoding=`.

WHY THIS EXISTS. Every prior figure for this defect class came from a throwaway script run once
in a scratch directory and never checked in. The last one written down — "216 of 472" at
`system/tools/bootstrap.py:138`, commit `56fa5cd` — does not reproduce: re-running the same AST
walk AT THAT SAME COMMIT gives 482 total / 195 defects, not 216/472. Neither number derives from
the other, and nobody can say today which one (if either) was ever right. An unrepeatable
measurement is a rumour with a decimal point. This tool exists so the count is a `git ls-files`
away, forever, and so the next person to quote a number can be asked "did you run it."

THIS IS A CENSUS, NOT A LINT. It never fails a commit and never blocks anything — that is a
separate tool (`system/tools/encoding_lint.py`, built in parallel, not touched by this file). This
tool's only job is to say, honestly and reproducibly, how many `open()` calls in the tree right
now are missing `encoding=`, and where they are.

SCOPE — AST ONLY, BARE NAMES ONLY (v1). This walks every `.py` file with Python's own `ast`
module and matches `ast.Call` nodes whose `func` is a bare `Name` equal to `"open"`. It does NOT
match attribute calls — `p.open()`, `pathlib.Path(...).open()`, `gzip.open()`, `codecs.open()` —
because those are a different call signature (and `codecs.open` even defaults to a different
default encoding than builtin `open`). Catching those needs type-aware resolution this tool does
not attempt; counting them here would silently overstate confidence in a number this tool cannot
actually back up by inspection. A future v2 can add attribute-call resolution; until then, this
undercounts by construction and says so on every run.

WHAT COUNTS AS A DEFECT. A non-binary `open()` call (mode does not contain `"b"`) whose
`encoding=` argument is either absent, or present but literally `None`. `encoding=None` LOOKS
explicit in the source but is not — passing `None` for `encoding` still falls back to
`locale.getpreferredencoding()`, exactly like omitting the keyword; a human skimming a diff for
"has an encoding=" would be fooled, so this tool is not.

READ vs WRITE SPLIT. A defect's mode is classified WRITE if the mode string contains any of
`w`, `a`, `x`, `+` — those all open a stream capable of producing bytes onto disk in the process's
own encoding, which is where a silent mis-encode actually corrupts something. Everything else,
including the no-mode-argument default (`open(path)` == mode `'r'`), is READ — a read-time
mis-decode is also a real defect, just a different failure shape (wrong characters in memory, not
wrong bytes on disk), so it is still counted, just labelled separately.

MODE RESOLUTION. The positional or keyword `mode` argument is read only when it is a **literal**
string (`ast.Constant`). A computed mode (`open(f, mode_var)`, `open(f, "r" + suffix)`) cannot be
read statically; this tool falls back to the safe assumption — `'r'`, i.e. READ, non-binary — and
does NOT special-case it, because guessing "probably fine" for an unreadable mode is exactly the
kind of confident-but-unchecked claim this repo's own house rules forbid. It is not flagged
separately in the output; say so in the docstring is the only guarantee made here.

EXIT CONTRACT (census, not lint — read this before wiring it into anything):
  0  = reported. This is returned whether or not defects were found — a census's job is to COUNT,
       not to grade, so "0 problems" and "195 problems" both exit 0.
  2  = CANNOT EVALUATE. No Python interpreter's `ast` module worked (should never happen — ast is
       stdlib), the target tree does not exist, or `git ls-files` was requested but the tree is
       not a git repo and had no usable fallback. A file that fails to *parse* (bad syntax, mixed
       tabs, whatever) is NOT this case — it is counted as UNPARSEABLE and named in the output,
       never silently dropped and never treated as "0 open() calls found here". Reporting a clean
       0-defect count when the walk itself could not complete is exactly the failure this repo's
       ABSENT-SUBJECT-RULE exists to catch, and this tool is built specifically not to commit it.

FILE SET. In a git repository, the file set is `git ls-files '*.py'` — the tracked, checked-in
`.py` files, respecting `.gitignore` — because that is the one file set every run of this tool
against the same commit will agree on. Outside a git repo (or if git ls-files fails), this falls
back to an `os.walk` that still visited every `.py` file, and says so in the header so nobody
mistakes the fallback count for the reproducible one.

Usage:
  python3 encoding_audit.py [PATH] [--json]

PATH defaults to this repo's root (two directories up from this file). Passing a different PATH
is how the reproduction test in this tool's own build task points it at a `git worktree` checkout
of an old commit without ever copying this script out of the tree it is meant to audit.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

WRITE_MODE_CHARS = ("w", "a", "x", "+")


class FileResult:
    __slots__ = ("path", "opens", "defects_read", "defects_write", "binary", "explicit")

    def __init__(self, path):
        self.path = path
        self.opens = 0
        self.defects_read = 0
        self.defects_write = 0
        self.binary = 0
        self.explicit = 0


def _literal_mode(call: ast.Call):
    """Return the literal mode string for an open() call, or None if it cannot be read statically.

    Checked in order: the second positional arg, then a `mode=` keyword. Only an ast.Constant
    str is trusted — anything computed (a variable, a concatenation, an f-string) is left as
    None, and the caller treats that exactly like the true default 'r' rather than pretending
    to know something it does not.
    """
    if len(call.args) >= 2:
        arg = call.args[1]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        return None  # positional mode given but not a literal — cannot resolve, fall back to 'r'
    for kw in call.keywords:
        if kw.arg == "mode":
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
            return None
    return None  # no mode argument at all -> real default, 'r'


def _has_explicit_encoding(call: ast.Call) -> bool:
    """True only if encoding= is present AND not literally None.

    encoding=None is deliberately NOT explicit: it still falls through to
    locale.getpreferredencoding(), same as omitting the keyword outright, so it is the exact
    defect this audit exists to find, not an exemption from it. A non-None, non-constant value
    (encoding=some_var) is trusted as explicit — the author wrote something, and resolving
    whether that variable is itself sane is out of scope for a static AST census.
    """
    for kw in call.keywords:
        if kw.arg == "encoding":
            if isinstance(kw.value, ast.Constant) and kw.value.value is None:
                return False
            return True
        if kw.arg is None:
            # **kwargs spread into the call — cannot rule out an encoding= hiding inside it.
            # Treat as explicit rather than falsely flagging a defect we cannot see.
            return True
    return False


def _is_bare_open_call(node: ast.Call) -> bool:
    """True only for a bare-name call open(...) — never an attribute call like p.open() or
    gzip.open(). Attribute calls are explicitly out of scope for v1; see the module docstring."""
    return isinstance(node.func, ast.Name) and node.func.id == "open"


def audit_file(path: str, rel: str):
    """Parse one file and return (FileResult, error) — error is None on success, else a string
    describing why the file could not be parsed (never silently skipped)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
    except OSError as exc:
        return None, f"could not read: {exc}"

    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError as exc:
        return None, f"SyntaxError: {exc.msg} (line {exc.lineno})"
    except Exception as exc:  # pragma: no cover - ast.parse is otherwise very reliable
        return None, f"{type(exc).__name__}: {exc}"

    result = FileResult(rel)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _is_bare_open_call(node)):
            continue
        result.opens += 1
        mode = _literal_mode(node)
        if mode is None:
            mode = "r"  # unresolved mode -> the true default, per the module docstring
        is_binary = "b" in mode
        if is_binary:
            result.binary += 1
            continue  # binary is N/A, never a defect, per the task spec
        if _has_explicit_encoding(node):
            result.explicit += 1
            continue
        is_write = any(c in mode for c in WRITE_MODE_CHARS)
        if is_write:
            result.defects_write += 1
        else:
            result.defects_read += 1
    return result, None


def collect_files(root: str):
    """Return (relpaths, method) where method is 'git ls-files' or 'os.walk (no git)'.

    git ls-files '*.py' is preferred because it is the one file set that agrees run to run at a
    given commit — it respects .gitignore and only sees tracked files. If root is not inside a
    git repo, or git itself is unavailable, this falls back to a full os.walk so the tool still
    produces a number rather than exiting — but the header names which method ran, because the
    two file sets are not the same set and a silent fallback would make a fallback count look
    reproducible when it is not.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", root, "ls-files", "*.py"],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0:
            files = [ln for ln in proc.stdout.splitlines() if ln.strip()]
            if files or proc.stdout == "":
                return sorted(files), "git ls-files"
    except (OSError, subprocess.SubprocessError):
        pass

    # Fallback: no git, or git ls-files failed. Walk the tree by hand.
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".venv", "venv")]
        for name in filenames:
            if name.endswith(".py"):
                full = os.path.join(dirpath, name)
                found.append(os.path.relpath(full, root))
    return sorted(found), "os.walk (no git)"


def run_audit(root: str):
    """Walk `root` and return the full census dict, or None if the tree could not be evaluated
    at all (exit 2 territory) — as opposed to being evaluated and finding zero defects."""
    if not os.path.isdir(root):
        return None

    relpaths, method = collect_files(root)

    per_file = {}
    unparseable = []
    for rel in relpaths:
        full = os.path.join(root, rel)
        result, err = audit_file(full, rel)
        if err is not None:
            unparseable.append({"file": rel, "error": err})
            continue
        per_file[rel] = result

    total_opens = sum(r.opens for r in per_file.values())
    total_binary = sum(r.binary for r in per_file.values())
    total_explicit = sum(r.explicit for r in per_file.values())
    total_defects_read = sum(r.defects_read for r in per_file.values())
    total_defects_write = sum(r.defects_write for r in per_file.values())
    total_defects = total_defects_read + total_defects_write

    by_dir = {}
    for rel, r in per_file.items():
        d = os.path.dirname(rel) or "."
        bucket = by_dir.setdefault(d, {"opens": 0, "defects": 0, "read": 0, "write": 0})
        bucket["opens"] += r.opens
        bucket["defects"] += r.defects_read + r.defects_write
        bucket["read"] += r.defects_read
        bucket["write"] += r.defects_write

    return {
        "root": root,
        "file_set_method": method,
        "files_scanned": len(relpaths),
        "files_unparseable": unparseable,
        "total_opens": total_opens,
        "binary": total_binary,
        "explicit_encoding": total_explicit,
        "defects": total_defects,
        "defects_read": total_defects_read,
        "defects_write": total_defects_write,
        "by_dir": by_dir,
        "per_file": {
            rel: {
                "opens": r.opens, "binary": r.binary, "explicit": r.explicit,
                "defects_read": r.defects_read, "defects_write": r.defects_write,
            }
            for rel, r in per_file.items() if r.opens
        },
    }


def render_text(census: dict) -> str:
    lines = []
    lines.append("encoding_audit — census of bare open() calls (AST, not grep; attribute calls "
                  "like p.open()/gzip.open() are out of scope for v1)")
    lines.append(f"  root:            {census['root']}")
    lines.append(f"  file set:        {census['file_set_method']} -> {census['files_scanned']} .py file(s)")
    if census["files_unparseable"]:
        lines.append(f"  ⛔ UNPARSEABLE:  {len(census['files_unparseable'])} file(s) — counted, not skipped:")
        for row in census["files_unparseable"]:
            lines.append(f"      {row['file']}: {row['error']}")
    lines.append("")
    lines.append("  THE ARITHMETIC (every number below is the sum of the per-file AST walk, printed "
                  "so it can be checked by hand):")
    lines.append(f"    total open() calls        = {census['total_opens']}")
    lines.append(f"    binary (mode has 'b')      = {census['binary']}   (N/A — not a defect)")
    lines.append(f"    explicit encoding=         = {census['explicit_encoding']}   "
                 "(encoding=None does NOT count as explicit)")
    lines.append(f"    defects (read)             = {census['defects_read']}   "
                 "(non-binary, no real encoding=, mode not w/a/x/+)")
    lines.append(f"    defects (write)            = {census['defects_write']}   "
                 "(non-binary, no real encoding=, mode has w/a/x/+)")
    lines.append(f"    defects (total)            = {census['defects']}"
                 f"   = {census['defects_read']} read + {census['defects_write']} write")
    check = census["binary"] + census["explicit_encoding"] + census["defects"]
    lines.append(f"    check: binary + explicit + defects = {census['binary']} + "
                 f"{census['explicit_encoding']} + {census['defects']} = {check}"
                 f"   (should equal total_opens = {census['total_opens']}: "
                 f"{'OK' if check == census['total_opens'] else 'MISMATCH'})")
    lines.append("")
    lines.append("  PER-DIRECTORY BREAKDOWN (opens / defects / read+write split):")
    for d in sorted(census["by_dir"]):
        b = census["by_dir"][d]
        lines.append(f"    {d:50s} opens={b['opens']:4d}  defects={b['defects']:4d}  "
                     f"(read={b['read']}, write={b['write']})")
    return "\n".join(lines) + "\n"


def cannot_evaluate_reason(census: dict):
    """Return a human reason string if `census` represents a tree this tool could not actually
    evaluate, or None if it is a genuine census (including a genuine 0-defect one).

    Two distinct CANNOT-EVALUATE shapes, both exit 2, both caught here rather than left for a
    reader to infer from a table of zeroes:

      - EMPTY FILE SET: zero .py files resolved under root at all. "0 defects" over "0 files
        looked at" is not a clean result, it is the absence of a subject — this repo's own
        ABSENT-SUBJECT-RULE names this exact confusion as the failure to avoid.
      - ALL-UNPARSEABLE: at least one file was found, but every single one of them failed to
        parse, so the walk produced zero real observations despite having a non-empty file set.
        A *partial* parse failure (some files parse, some don't) is NOT this case — that stays a
        real census, exit 0, with the unparseable files named in the output as usual.
    """
    if census["files_scanned"] == 0:
        return f"no .py files found under {census['root']} (via {census['file_set_method']})"
    if len(census["files_unparseable"]) == census["files_scanned"]:
        return (f"all {census['files_scanned']} .py file(s) under {census['root']} failed to "
                f"parse — the tree could not be walked")
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Census of unencoded open() calls (AST-based, bare-name open() only). "
                    "Reproducible: run it twice unchanged, get byte-identical output.",
    )
    ap.add_argument("path", nargs="?", default=REPO_ROOT,
                     help="tree to audit (default: this repo's root)")
    ap.add_argument("--json", action="store_true", help="machine-readable JSON output")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.path)
    census = run_audit(root)
    if census is None:
        # CANNOT EVALUATE: the target path is not even a directory. Never report a 0-defect
        # census in this case — that would be exactly the silently-clean-because-nothing-ran
        # failure this tool is built not to commit.
        print(f"encoding_audit: ⛔ CANNOT EVALUATE — no such directory: {root}", file=sys.stderr)
        return 2

    reason = cannot_evaluate_reason(census)
    if reason is not None:
        # Deliberately do NOT print the arithmetic block here — a table reading "0 defects"
        # is exactly the shape that gets misread as "clean", when what actually happened is that
        # this run had nothing to look at. Say so in words instead, and stop.
        if args.json:
            print(json.dumps({"cannot_evaluate": True, "reason": reason, **census},
                              indent=2, sort_keys=True))
        else:
            print(f"encoding_audit: ⛔ CANNOT EVALUATE — {reason}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(census, indent=2, sort_keys=True))
    else:
        print(render_text(census), end="")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main())
