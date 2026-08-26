#!/usr/bin/env python3
"""encoding_lint — refuse NEW unencoded `open()` calls in staged Python.

WHY THIS IS A SEPARATE TOOL, NOT A CLAUSE BOLTED ONTO SOMETHING ELSE.
`citation_lint.py` checks whether a document's citations resolve — it is entirely text-based
(`import re`, no `import ast`) and knows nothing about Python semantics. `order_lint.py` checks
skill ordering. `topic-vocab-lint` checks vocabulary. None of the three parses Python, and none
has any notion of "this call opens a file without saying what encoding it is." A defect that
lives in the AST of a `.py` file needs a checker that reads the AST of a `.py` file.

WHAT IT CATCHES. An unencoded `open()` call — either a text-mode call with no `encoding=`
keyword, or one that spells `encoding=None` explicitly, which is the same defect written more
verbosely. On a platform whose default codec is not UTF-8 (the measured case: Windows cp1252),
such a call silently reads or writes the wrong bytes instead of raising — see
`system/tools/utf8_stdio.py`'s docstring for the sibling defect this shares a root cause with.

DETECTION IS AST (`import ast`), NEVER GREP — a regex cannot tell `open(p, encoding="utf-8")`
from `open(p, encoding="utf-8", errors=weird_but_encoding_is_fine)` without re-deriving a Python
parser badly. `ast.parse` already is one.

SCOPE, DELIBERATELY NARROW FOR v1: only a call to the **builtin bare name** `open(...)`.
`p.open()`, `Path.open()`, `gzip.open()`, `codecs.open()`, **and `io.open()`** — any
attribute-access call, `io.open` included, even though it is the identical builtin under
another name — are OUT OF SCOPE. So is a renamed/aliased binding (`o = open; o(p)`) and an
`encoding=` argument that is a variable whose runtime value happens to be `None` or `""` — all
of that is dataflow analysis this tool explicitly does not attempt. Widening this is real
future work, not a shortcut taken here; a bare-name check is the one that cannot be fooled into
thinking `shutil.rmtree` is `open`, and it is the shape every defect actually measured in this
tree (see the deny message below) uses. A reader relying on this gate should know: a one-word
rename to `io.open`, or an indirection through a variable, walks straight past it.

A CALL IS A DEFECT WHEN BOTH:
  1. its mode argument (positional #2, or keyword `mode=`) does not contain `b` — omitted mode
     defaults to `"r"`, which does not contain `b` either, so an omitted mode still counts, and
  2. it carries no `encoding=` keyword, OR `encoding=` is the literal `None`.
Anything else — `"rb"`, `"wb"`, `encoding="utf-8"`, `encoding=some_var` (any non-`None`
expression) — is not a defect. This lint does not try to prove the expression is a *valid*
codec name; that is what runtime would already catch.

GRANDFATHERING IS A RATCHET ON A DEFECT *COUNT*, NOT A LINE-NUMBER MEMBERSHIP TEST. The first
version of this tool intersected each `open()` call's line span against the diff's ADDED lines
-- and that model is structurally blind to one real attack: deleting the `encoding="utf-8"`
line out of an existing multi-line call, with a trailing comma already in place so the diff is a
PURE DELETION (`-        encoding="utf-8"`, no `+` line at all). There is no added line to
intersect with, so a line-membership model reports CLEAN on a commit that just introduced a real
defect by removing a line. Measured 2026-08-23 against the independent adversarial test suite.

THE FIX: per file, COUNT defects instead of locating them by line.
  post = number of defective open() calls in the STAGED post-image (`git show :<path>`)
  pre  = number of defective open() calls in the PRE-image at HEAD (`git show HEAD:<path>`;
         a brand-new file, or a repo with no HEAD yet, means pre = 0)
  post > pre  ->  FLAGGED.  Otherwise clean.
This is not merely a different way to reach the same answer -- it is what makes grandfathering
hold BY CONSTRUCTION rather than by a line-reasoning trick that has to be kept honest by hand: a
tree with hundreds of pre-existing unencoded calls across dozens of files (run `encoding_audit.py`
for this repo's own live count), touched on an unrelated line, is `pre == post` for every one of
them, with no notion of "which line" ever entering the picture. Deleting an `encoding=` keyword
makes the call itself go from clean to defective, so `pre=0 defects-from-that-call, post=1`: the
count rises, and it is refused. A whole-file gate would refuse every pre-existing-defect file on
its next unrelated touch -- the exact shape of defect that made `system/shipping-lane/scrub.py`
permanently uncommittable until `check_no_internal_leakage.py` grew a `--scan-file` whole-file
mode; the ratchet's `pre == post` case is what keeps this tool from repeating that.

THE ONE HOLE THIS MODEL HAS, NAMED RATHER THAN HIDDEN: a commit that adds one new unencoded
`open()` call to a file AND removes a pre-existing one, in the SAME commit, nets `post == pre`
and passes. A count ratchet cannot distinguish "nothing changed" from "one defect replaced
another" -- catching that would require identifying WHICH calls are the same call across the
diff (a much harder problem, adjacent to rename detection at the call-site level, not the
file level), which this tool does not attempt. Do not read this silence as an oversight: it is
a real, accepted limitation of counting instead of tracking identity, and a second mechanism
bolted on to chase it would be exactly the kind of complexity this tool exists to avoid.

RENAMES. `git diff --cached --name-status --diff-filter=ACMR -M` is asked to detect renames so
a renamed file's PRE-image is read from its OLD path at HEAD, not its new one (which has no
history under the new name yet). A rename that changes nothing inside the file nets `pre ==
post` and stays clean, same as any other untouched file.

MODES
  --staged        the ONLY mode the pre-commit hook may invoke. Enumerates the staged set via
                   `git diff --cached --name-status --diff-filter=ACMR -M`, reads each file's
                   post-image via `git show :<path>` (the staged blob, not the working tree --
                   what will actually be committed is what gets checked) and its pre-image via
                   `git show HEAD:<old-path>`.
  --scan-file PATH  WHOLE-FILE mode: PATH is evaluated with an implicit pre-image of zero
                   defects (i.e. every defect in the file is reported, same as "brand-new
                   file"). FOR MUTATION TESTING / MANUAL AUDIT ONLY — this is precisely the
                   scrub.py scar described above. It exists only to give
                   `system/factory/mutate.py` its `{ARTIFACT}` CLI shape (one path in, one
                   verdict out, no git required). It must NEVER be wired into a hook — a hook
                   that ran it would re-create the exact incident this tool is grandfathered to
                   avoid.
  --quiet         suppress CLEAN chatter (deny output always prints regardless of this flag).

WHICH FILES COUNT AS PYTHON. A staged file's path ending `.py`, OR — because an extension check
alone is blind to an extensionless script — its staged post-image's first line being a `#!` line
naming python (`#!/usr/bin/env python3`, `#!/usr/bin/python`, ...). This repo currently ships
zero tracked non-`.py` files with a python shebang (checked 2026-08-23), so this is a
forward-looking closure, not a live hole: `bin/runme` with a python shebang and a real unencoded
`open()` must not be invisible to this gate just because its name lacks `.py`. A file that is
neither is skipped entirely — never evaluated, never counted, never a reason for CANNOT
EVALUATE.

EXIT CODES — copied from `.github/scripts/check_no_internal_leakage.py`'s contract, not invented:
  0  CLEAN            — evaluated, nothing new flagged
  1  FLAGGED           — at least one file's defect count rose (post > pre)
  2  CANNOT EVALUATE   — the check never ran to a real verdict. Three causes, each its own
                         reason token, printed as the FIRST LINE of stdout:
                           CANNOT-EVALUATE: no-python-staged
                           CANNOT-EVALUATE: unparseable <path>
                           CANNOT-EVALUATE: no-git

ABSENT-SUBJECT RULE: "nothing to check" is its own outcome, never folded into 0. A commit that
stages no Python file at all (by the WHICH FILES COUNT rule above, not by extension alone) gets
exit 2 with reason `no-python-staged` — not a silent pass that looks identical to "checked, and
it was clean," and not a false claim of absence when a shebang-only script WAS staged.

DECODING IS DELIBERATE, NEVER LEFT TO CRASH THE PROCESS. Every git invocation is read as raw
bytes (`capture_output=True`, never `text=True`, which lets subprocess pick a codec and raise
mid-decode before any of this tool's own per-file handling runs). The name-status listing itself
is decoded leniently (`errors="replace"`) since it is only ever used to recover PATHS. A staged
file's OWN post-image is decoded strictly: one this tool cannot decode as UTF-8 is unparseable BY
DEFINITION (not valid Python source under this repo's own encoding policy), isolated to that one
file and reported as `CANNOT-EVALUATE: unparseable <path>` — the same path a `SyntaxError` takes
— never an uncaught `UnicodeDecodeError` killing the whole run with a raw traceback. A PRE-image
that fails to decode or fails to parse is treated as contributing 0 to `pre` — conservative in
the direction of catching more defects, never fewer, since an unreadable "before" cannot be
credited as proof nothing was wrong there. An encoding tool that dies on an encoding problem is
the exact irony this feature exists to end.

THE REMEDY THIS TOOL POINTS AT. `read_text(path, what)` in `shared/emit/verdicts.py:20`
already opens with `encoding="utf-8"` and returns a clean (text, error) pair. Several tools
in this repo already use it — importing a fix once does not adopt it everywhere, so this
lint still exists to catch the calls that were not converted.
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys

CLEAN, FLAGGED, CANNOT_EVALUATE = 0, 1, 2

REMEDY = (
    'add encoding="utf-8" — see read_text(path, what) in shared/emit/verdicts.py:20, '
    "which several tools in this repo already use -- importing the fix once does not adopt "
    "it everywhere."
)

# A recognized python shebang's first line must name the interpreter somewhere in it --
# "#!/usr/bin/env python3", "#!/usr/bin/python", "#! /usr/bin/env python" (a space after #!
# is legal shell). Deliberately loose (substring "python") rather than a rigid path match: the
# set of ways people write a shebang line is not something this tool should re-litigate.
def _is_python_shebang(first_line: str) -> bool:
    line = first_line.lstrip()
    return line.startswith("#!") and "python" in line


class Defect:
    def __init__(self, path, lineno, source_line):
        self.path = path
        self.lineno = lineno
        self.source_line = source_line

    def render(self):
        return (
            "  %s:%d\n"
            "      %s\n"
            "      -> %s" % (self.path, self.lineno, self.source_line.strip(), REMEDY)
        )


def _mode_has_b(call: ast.Call) -> bool:
    """True if this open() call's mode argument (positional #2 or keyword mode=) contains "b".
    An omitted mode defaults to "r", which does not contain "b" -- so omitted counts as text
    mode, same as an explicit "r"."""
    mode_node = None
    if len(call.args) >= 2:
        mode_node = call.args[1]
    for kw in call.keywords:
        if kw.arg == "mode":
            mode_node = kw.value
    if mode_node is None:
        return False  # default mode "r" -- text
    if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
        return "b" in mode_node.value
    # A non-literal mode (a variable, a concatenation) can't be proven binary or text by
    # inspection. Treated as NOT binary -- i.e. still eligible to be flagged if it also lacks
    # encoding=. Erring toward "still check it" matches this tool's job.
    return False


def _is_bare_open_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
    )


def _is_defect(call: ast.Call) -> bool:
    if _mode_has_b(call):
        return False
    for kw in call.keywords:
        if kw.arg == "encoding":
            if isinstance(kw.value, ast.Constant) and kw.value.value is None:
                return True  # encoding=None -- the same defect spelled out
            return False  # any other encoding= expression -- not a defect
    return True  # no encoding= keyword at all


def find_open_defects(tree: ast.AST):
    """Every defective bare open() call in this module, keyed by the call node's OWN lineno."""
    out = {}
    for node in ast.walk(tree):
        if _is_bare_open_call(node) and _is_defect(node):
            out[node.lineno] = node
    return out


def defects_in_source(path: str, source: str) -> list:
    """Every defective bare open() call in `source`, as Defect objects -- UNFILTERED: the
    ratchet decides membership by comparing COUNTS across pre/post images, not by asking
    whether any one call's line was touched. Raises SyntaxError on unparseable source; the
    caller turns that into CANNOT EVALUATE, never a silent skip."""
    tree = ast.parse(source, filename=path)
    by_line = find_open_defects(tree)
    src_lines = source.splitlines()
    out = []
    for lineno in sorted(by_line):
        text = src_lines[lineno - 1] if 0 < lineno <= len(src_lines) else ""
        out.append(Defect(path, lineno, text))
    return out


def _pre_image_defect_count(raw: bytes) -> int:
    """Best-effort defect count for a PRE-image. `raw is None` covers both "file did not exist
    at HEAD" (a brand-new file) and "there is no HEAD at all yet" -- both mean 0 by the
    contract. An undecodable or unparseable pre-image ALSO counts as 0 -- deliberately: crediting
    an unreadable "before" with defects it cannot be shown to hold would let the ratchet forgive
    something it never actually verified, which is the wrong direction to be wrong in for a
    grandfathering rule. Never raises."""
    if raw is None:
        return 0
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError:
        return 0
    try:
        return len(find_open_defects(ast.parse(source)))
    except SyntaxError:
        return 0


# --------------------------------------------------------------------------- git plumbing
#
# Every git call is read as raw bytes -- never `text=True`, which lets subprocess pick a codec
# and raise mid-decode before any of this tool's own per-file error handling ever runs.
# Decoding is this tool's decision, made deliberately at each call site.

def _run_git_bytes(args):
    return subprocess.run(["git"] + args, capture_output=True)


def _git_show_bytes(ref_path: str):
    """`ref_path` like ':foo.py' (staged/index) or 'HEAD:foo.py' (pre-image). Returns raw bytes,
    or None if git could not produce them -- the path doesn't exist at that ref, OR the ref
    itself doesn't exist (no HEAD yet, in a brand-new repo)."""
    proc = _run_git_bytes(["show", ref_path])
    if proc.returncode != 0:
        return None
    return proc.stdout


def staged_image_bytes(path: str):
    """The staged (index) content of `path`, i.e. what would actually be committed -- never the
    working tree, which can differ from what's staged."""
    return _git_show_bytes(":" + path)


def head_image_bytes(path: str):
    """`path`'s content at HEAD -- the pre-image the ratchet compares against. None for a
    brand-new file, or a repo with no commits yet."""
    return _git_show_bytes("HEAD:" + path)


def _first_line_bytes(raw: bytes) -> str:
    """The first line of `raw`, decoded leniently (errors='replace') purely to sniff a shebang.
    A shebang line is ASCII by convention; a replacement character elsewhere in a binary blob
    must not stop this from recognizing a real `#!.../python` prefix."""
    first = raw.split(b"\n", 1)[0]
    return first.decode("utf-8", errors="replace")


def is_python_file(path: str, raw: bytes) -> bool:
    if path.endswith(".py"):
        return True
    return _is_python_shebang(_first_line_bytes(raw))


def staged_entries():
    """(status, old_path_or_None, new_path) for every staged file this tool cares about --
    Added, Copied, Modified, Renamed (diff-filter=ACMR; a pure Deletion introduces nothing to
    scan and is correctly excluded). Rename detection (-M) is ON so a renamed file's PRE-image
    is read from its OLD path at HEAD -- the new path has no history of its own yet, and reading
    HEAD:<new-path> for a rename would silently behave like a brand-new file (pre=0), hiding a
    real defect count drop-then-rise across the rename. Returns (entries, error_rc) -- error_rc
    is None on success, else the CANNOT_EVALUATE code to return (git missing / failed)."""
    try:
        proc = _run_git_bytes(
            ["diff", "--cached", "--name-status", "--diff-filter=ACMR", "-M"]
        )
    except OSError as e:
        print("CANNOT-EVALUATE: no-git")
        sys.stderr.write("  %s\n" % e)
        return None, CANNOT_EVALUATE
    if proc.returncode not in (0, 1):
        print("CANNOT-EVALUATE: no-git")
        sys.stderr.write(proc.stderr.decode("utf-8", errors="replace"))
        return None, CANNOT_EVALUATE

    text = proc.stdout.decode("utf-8", errors="replace")
    entries = []
    for line in text.splitlines():
        if not line:
            continue
        fields = line.split("\t")
        status = fields[0]
        if status[0] in ("R", "C") and len(fields) >= 3:
            old_path, new_path = fields[1], fields[2]
        else:
            new_path = fields[1]
            # 'M' -- pre-image is the SAME path at HEAD. 'A' -- brand new, no pre-image at all.
            old_path = new_path if status[0] == "M" else None
        entries.append((status, old_path, new_path))
    return entries, None


def run_staged():
    entries, error_rc = staged_entries()
    if error_rc is not None:
        return error_rc

    all_defects = []
    any_python_seen = False
    for _status, old_path, new_path in entries:
        post_raw = staged_image_bytes(new_path)
        if post_raw is None:
            # Staged as changed but not readable via `git show :<path>` -- e.g. a path git
            # can't resolve. Nothing to scan.
            continue

        if not is_python_file(new_path, post_raw):
            continue  # not python by extension or shebang -- out of scope, not an error

        any_python_seen = True
        try:
            post_source = post_raw.decode("utf-8")
        except UnicodeDecodeError as e:
            # A python file (by extension or shebang) that cannot be decoded as UTF-8 is
            # unparseable BY DEFINITION under this repo's encoding policy -- isolated to this
            # one file, reported exactly like a SyntaxError, never an uncaught traceback.
            print("CANNOT-EVALUATE: unparseable %s" % new_path)
            sys.stderr.write("  %s\n" % e)
            return CANNOT_EVALUATE

        try:
            post_defects = defects_in_source(new_path, post_source)
        except SyntaxError as e:
            print("CANNOT-EVALUATE: unparseable %s" % new_path)
            sys.stderr.write("  %s\n" % e)
            return CANNOT_EVALUATE

        pre_raw = head_image_bytes(old_path) if old_path is not None else None
        pre_count = _pre_image_defect_count(pre_raw)

        if len(post_defects) > pre_count:
            all_defects.extend(post_defects)

    if not any_python_seen:
        print("CANNOT-EVALUATE: no-python-staged")
        return CANNOT_EVALUATE

    if all_defects:
        print(
            "\n  ENCODING-LINT — %d file(s) with a risen unencoded open() count.\n"
            % len({d.path for d in all_defects})
        )
        for d in all_defects:
            print(d.render())
        print("")
        return FLAGGED

    return CLEAN


def run_scan_file(path: str):
    """WHOLE-FILE mode: PATH is evaluated against an implicit pre-image of zero defects (every
    defect in the file is reported, same treatment as a brand-new file). See module docstring --
    manual/mutation-testing use only, NEVER wired into the hook."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as e:
        print("CANNOT-EVALUATE: unparseable %s" % path)
        sys.stderr.write("  %s\n" % e)
        return CANNOT_EVALUATE

    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        print("CANNOT-EVALUATE: unparseable %s" % path)
        sys.stderr.write("  %s\n" % e)
        return CANNOT_EVALUATE

    try:
        defects = defects_in_source(path, source)
    except SyntaxError as e:
        print("CANNOT-EVALUATE: unparseable %s" % path)
        sys.stderr.write("  %s\n" % e)
        return CANNOT_EVALUATE

    if defects:
        print(
            "\n  ENCODING-LINT — %d unencoded open() call(s) in %s.\n" % (len(defects), path)
        )
        for d in defects:
            print(d.render())
        print("")
        return FLAGGED
    return CLEAN


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Refuse a RISE in unencoded open() calls in staged Python (per-file "
                     "defect-count ratchet against the HEAD pre-image)."
    )
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true",
                       help="the ONLY mode the pre-commit hook may invoke")
    mode.add_argument("--scan-file", metavar="PATH",
                       help="whole-file mode -- manual/mutation-testing only, never a hook")
    ap.add_argument("--quiet", action="store_true",
                     help="suppress CLEAN chatter (deny output always prints)")
    args = ap.parse_args(argv)

    if args.staged:
        rc = run_staged()
    else:
        rc = run_scan_file(args.scan_file)

    if rc == CLEAN and not args.quiet:
        print("ENCODING-LINT-CLEAN")
    return rc


if __name__ == "__main__":
    import os

    sys.path.insert(
        0,
        os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)))),
    )
    from utf8_stdio import force_utf8_stdio  # noqa: E402

    force_utf8_stdio()
    sys.exit(main())
