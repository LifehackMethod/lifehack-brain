#!/usr/bin/env python3
"""hides_failure.py -- commit check 2 of 4 (plan v2 3b "Close the known gaps": "Does it hide failure?").

Refuses a commit whose ADDED lines (git diff --cached -U0) in a .sh/.py script:
  silenced-error   `|| true` / `|| :` / `2>/dev/null` on a fetch, write, push or model call
  empty-except     bare `except:` or `except Exception: pass` (python, via ast)
  model-id         a typed-in versioned model id, or a model flag naming one; name a tier (model_ids.py / model.lib.sh)
  tmp-path         a hard-coded /tmp/ path (use $TMPDIR / tempfile / the scratch helper)
  raw-google-curl  a curl/wget to a Google/Gmail API host (slip 41): use the shared email tool (rule in door_rules.py)
  vacuous-checker  a checker/lint/verify/validate script that loops over found files with no zero-target guard (F3)
  python-path      a hard-coded absolute interpreter path; the bare `python3` / `env python3` stay legal

Rules 1 and 3 are NOT copied: they are imported from system/tools/door_rules.py, the one rules file the job door
(install-schedulers.sh --check-row) also uses. Rules 2, 4, 5 are new here (no job-door equivalent).

ONLY ADDED LINES count (the old backlog never blocks, G14). Tests and fixtures are exempt, as are the model table
files. Escape hatch: `# allow-silence: <reason>` on the line (any physical line of a continued command) -> allowed
and REPORTED, never silent. Output: exit 1 on refuse; one human line plus one `FINDING {json}` per hit on stderr.

Usage: hides_failure.py                 staged changes (default; run from the repo, as pre-commit does)
       hides_failure.py --commits N     scan ALL added lines of the last N commits (false-alarm measurement)
       hides_failure.py --files P...    scan every line of these files, no git (the end-of-turn check)
"""
import ast
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "system", "tools")
sys.path.insert(0, _TOOLS)
sys.path.insert(0, os.path.join(os.path.dirname(_TOOLS), "hooks", "lib"))
from roundb import roundb_on  # noqa: E402
from door_rules import (weak_reason, REASON_HELP, MODEL_ID, MODEL_LIT, MODEL_TABLE_FILES, silenced_call, google_curl, google_curl_exempt,  # noqa: E402
                        GOOGLE_CURL_WHY, f3_unguarded)  # noqa: E402  (the one copy)

CHECK = "hides_failure"
ALLOW = re.compile(r"#\s*(?:allow-silence|empty-ok):\s*(\S.*)$")
TMP = re.compile(r"(?<![\w.$}-])/(?:private/)?tmp/")
PYPATH = re.compile(r"(?<![\w.$}-])/(?:[\w.+-]+/)*python3?(?:\.\d+)?(?![\w/-])")
EXEMPT_DIR = re.compile(r"(^|/)(tests?|fixtures?|__pycache__)/")
EXEMPT_NAME = re.compile(r"(^|/)(test_[^/]*|[^/]*_tests?\.(py|sh)|[^/]*\.pre-[^/]*)$")


def exempt(path):
    return bool(EXEMPT_DIR.search(path) or EXEMPT_NAME.search(path)) or os.path.basename(path) in MODEL_TABLE_FILES


def git(*a):
    r = subprocess.run(["git", *a], capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(f"{CHECK}: git {' '.join(a)} failed: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(2)  # a check that cannot read the diff must not pass as clean
    return r.stdout


def parse_diff(text):
    """unified -U0 diff -> {path: set(added new-file line numbers)}"""
    out, cur, ln = {}, None, 0
    for row in text.splitlines():
        if row.startswith("+++ "):
            cur = row[6:] if row.startswith("+++ b/") else None
            if cur is not None:
                out.setdefault(cur, set())
        elif row.startswith("@@") and cur is not None:
            m = re.search(r"\+(\d+)", row)
            ln = int(m.group(1)) if m else 0
        elif row.startswith("+") and not row.startswith("+++") and cur is not None:
            out[cur].add(ln)
            ln += 1
    return out


def bash_commands(lines):
    """yield (start_line, [physical line numbers], joined text); backslash continuations are ONE command (as the door does)."""
    acc, nums = "", []
    for i, ln in enumerate(lines, 1):
        if ln.endswith("\\") and not ln.lstrip().startswith("#"):
            acc += ln[:-1] + " "
            nums.append(i)
            continue
        nums.append(i)
        yield nums[0], list(nums), acc + ln
        acc, nums = "", []


def py_empty_excepts(text):
    """-> [(line, detail)] for bare `except:` (that does not re-raise) and `except Exception|BaseException: pass`"""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    hits = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.ExceptHandler):
            continue
        only_pass = all(isinstance(b, ast.Pass) or (isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant)) for b in n.body)
        reraises = any(isinstance(x, ast.Raise) for b in n.body for x in ast.walk(b))
        if n.type is None and not reraises:
            hits.append((n.lineno, "bare `except:` swallows every error"))
        elif only_pass and isinstance(n.type, ast.Name) and n.type.id in ("Exception", "BaseException"):
            hits.append((n.lineno, f"`except {n.type.id}: pass` swallows every error"))
    return hits


def analyze(path, text, added):
    """-> [finding dict] for the added lines of one file."""
    lines = text.splitlines()
    out = []

    def hit(rule, line, why, span=None):
        span = span or [line]
        allowed = None
        for n in span:
            m = ALLOW.search(lines[n - 1]) if 0 < n <= len(lines) else None
            if m:
                allowed = m.group(1).strip()
        weak = ""
        if allowed and roundb_on("allow_silence_reason"):   # Round C 3: a real reason, or fix it (OFF = exactly the old behaviour)
            weak = weak_reason(allowed, " ".join(re.sub(r"#.*$", "", lines[n - 1]) for n in span if 0 < n <= len(lines)))
            if weak:
                why = f"{why} -- the allow-silence reason is {weak}; {REASON_HELP}"
        out.append({"check": CHECK, "file": path, "line": line, "rule": rule, "detail": why,
                    "status": "allowed" if allowed and not weak else "refused", "reason": allowed or ""})

    if path.endswith((".sh", ".py")):
        for start, nums, full in bash_commands(lines):
            if not any(n in added for n in nums) or full.lstrip().startswith("#"):
                continue
            kind = silenced_call(full.split(" #", 1)[0])
            if kind:
                hit("silenced-error", start, f"silenced {kind} error: `|| true`, `|| :`, `2>/dev/null` hide a failure; log it to stderr and fail the step", nums)
    if path.endswith((".sh", ".py")) and not google_curl_exempt(path):
        for start, nums, full in bash_commands(lines):
            if any(n in added for n in nums) and not full.lstrip().startswith("#") and google_curl(full.split(" #", 1)[0]):
                hit("raw-google-curl", start, GOOGLE_CURL_WHY, nums)
    if path.endswith((".sh", ".py")):
        for ln, why in f3_unguarded(path, text, added, lines):
            hit("vacuous-checker", ln, why)
    if path.endswith(".py"):
        for ln, why in py_empty_excepts(text):
            if ln in added:
                hit("empty-except", ln, why)
    for i, ln in enumerate(lines, 1):
        if i not in added:
            continue
        if ln.lstrip().startswith("#") and not ln.startswith("#!"):
            continue
        code = ln if ln.startswith("#!") else ln.split(" #", 1)[0]
        if MODEL_ID.search(code) or any(r.search(code) for r in MODEL_LIT):
            hit("model-id", i, "typed-in model id: name a tier (small|medium|large); ids live only in model.lib.sh / model_ids.py")
        if TMP.search(code) and "TMPDIR" not in code:
            hit("tmp-path", i, "hard-coded /tmp/ path: use $TMPDIR / mktemp / tempfile, never a fixed path")
        if PYPATH.search(code):
            hit("python-path", i, "hard-coded interpreter path: use `python3` from PATH (or `#!/usr/bin/env python3`)")
    return out


def report(findings):
    for f in findings:
        tag = "ALLOWED (allow-silence: %s)" % f["reason"] if f["status"] == "allowed" else "REFUSED"
        print(f"{CHECK}: {tag} {f['file']}:{f['line']} [{f['rule']}] {f['detail']}", file=sys.stderr)
        print("FINDING " + json.dumps(f, sort_keys=True), file=sys.stderr)


def scan_staged():
    diff = parse_diff(git("diff", "--cached", "-U0", "--no-color", "--no-ext-diff", "--diff-filter=ACMR"))
    found = []
    for path, added in diff.items():
        if not added or not path.endswith((".sh", ".py")) or exempt(path):
            continue
        found += analyze(path, git("show", ":" + path), added)
    return found


def scan_files(paths):
    """--files: every line of each existing .sh/.py file counts as added (a file the session just created has no old backlog)."""
    found = []
    for p in paths:
        if not p.endswith((".sh", ".py")) or exempt(p) or not os.path.isfile(p):
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        found += analyze(p, text, set(range(1, len(text.splitlines()) + 1)))
    return found


def scan_commits(n):
    found = []
    for c in git("log", f"-{n}", "--format=%h").split():
        diff = parse_diff(git("show", "-U0", "--no-color", "--no-ext-diff", "--format=", "--diff-filter=ACMR", c))
        for path, added in diff.items():
            if not added or not path.endswith((".sh", ".py")) or exempt(path):
                continue
            for f in analyze(path, git("show", f"{c}:{path}"), added):
                f["commit"] = c
                found.append(f)
    return found


def main(argv):
    if len(argv) >= 3 and argv[1] == "--files":
        found = scan_files(argv[2:])
    else:
        found = scan_commits(int(argv[2])) if len(argv) >= 3 and argv[1] == "--commits" else scan_staged()
    report(found)
    refused = [f for f in found if f["status"] == "refused"]
    if refused:
        print(f"{CHECK}: {len(refused)} refusal(s). Fix the line, or add `# allow-silence: <reason>` on it.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
