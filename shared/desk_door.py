#!/usr/bin/env python3
# not-wired-yet: this is the desk door's check of desk-building-sop.md section 7 step 4 ("The door
# checks it"); desk_scaffold (CR-9 step 2a, being rewritten by another window) is the intended
# caller and will run it at desk birth. Nothing calls it yet.
"""desk_door.py -- the desk door's checks (canon/desk-building-sop.md section 5) as one code check.

Takes a desk folder (or a desk_id, resolved through shared/desk_list.py) and prints PASS, or one
named reason per failure, exit 0 / 1. The six checks, section 5's list:

  1. the card parses and holds only its three facts -- name, canon, diary; anything else is rejected
  2. every pointer on the card resolves to a real file
  3. nothing duplicates a fact owned elsewhere (jobs belong to the job list; access grants to the
     capability registry; status notes to their producers)
  4. canon sits where the card says it does
  5. any jobs the desk ships go through the job door (`install-schedulers.sh --check-row` PASS)
  6. no copied shared tools -- a desk uses the platform's tools or its own

The card (desk.yaml) is read with PyYAML when it is installed, and otherwise with a minimal
`key: value` reader that refuses anything outside the card's simple shape. Job rows are looked for
in ```jobs fences inside the desk folder's .md files and run through the job door's own
--check-row entry point with the LIFEHACK_JOBS_FILE test seam, so the real manifest is never read.
Copied shared tools are found by content: any file under the desk folder whose bytes match a file
under shared/ is named, with the path it duplicates.

CLI:
    python3 shared/desk_door.py <desk-folder | desk_id>   # PASS or reasons; exit 0 / 1
"""
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import desk_list  # noqa: E402  (the ONE reader of the person's desk list)

CARD_NAME = "desk.yaml"
CARD_FACTS = ("name", "canon", "diary")
OWNED_ELSEWHERE = {
    "jobs": "jobs belong to the job list",
    "job": "jobs belong to the job list",
    "cron": "jobs belong to the job list",
    "access": "access grants live in the capability registry",
    "grants": "access grants live in the capability registry",
    "capabilities": "access grants live in the capability registry",
    "status": "status notes belong to their producers",
    "tiles": "status notes belong to their producers",
}
_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")


def read_card(desk):
    """-> (card dict, None) or (None, named reason)."""
    path = os.path.join(desk, CARD_NAME)
    if not os.path.isfile(path):
        return None, "check 1 (card parses, three facts): no card: %s" % path
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        import yaml
    except ImportError:
        yaml = None
    if yaml is not None:
        try:
            data = yaml.safe_load(text)
        except Exception as e:
            return None, "check 1 (card parses, three facts): card does not parse: %s: %s" % (
                CARD_NAME, " ".join(str(e).split()))
    else:
        data, err = _parse_simple_card(text)
        if err:
            return None, "check 1 (card parses, three facts): card does not parse: %s" % err
    if not isinstance(data, dict):
        return None, "check 1 (card parses, three facts): card does not parse: %s is %s, not a mapping" % (
            CARD_NAME, type(data).__name__)
    return data, None


def _parse_simple_card(text):
    """Minimal `key: value` reader for the card's three-line shape. -> (dict, None) or (None, reason)."""
    data = {}
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _KEY_RE.match(line)
        if not m:
            return None, "line %d is not `key: value`: %r" % (n, line.strip()[:60])
        if m.group(1) in data:
            return None, "line %d repeats the fact %r" % (n, m.group(1))
        data[m.group(1)] = m.group(2).strip()
    return data, None


def check_card_facts(card):
    """Check 1: exactly the three facts, each a non-empty scalar."""
    reasons = []
    extra = [k for k in card if k not in CARD_FACTS]
    if extra:
        reasons.append("check 1 (card parses, three facts): card holds a fourth fact: %s "
                       "(the card is name, canon, diary -- nothing else)" % ", ".join(sorted(extra)))
    missing = [k for k in CARD_FACTS if k not in card or not str(card[k] or "").strip()]
    if missing:
        reasons.append("check 1 (card parses, three facts): card is missing the fact: %s" % ", ".join(missing))
    return reasons


def check_owned_elsewhere(card):
    """Check 3: no fact owned elsewhere rides on the card."""
    reasons = []
    for k in card:
        hit = OWNED_ELSEWHERE.get(k.lower())
        if hit:
            reasons.append("check 3 (no facts owned elsewhere): card fact %r is owned elsewhere: %s" % (k, hit))
    return reasons


def check_pointers(desk, card):
    """Check 2: every pointer on the card resolves to a real file (the diary may be a folder)."""
    reasons = []
    for fact in ("canon", "diary"):
        raw = str(card.get(fact) or "").strip()
        if not raw:
            continue  # already named by check 1
        p = os.path.join(desk, raw)
        if not os.path.exists(p):
            reasons.append("check 2 (every pointer resolves): pointer to a missing file: %s -> %s" % (fact, raw))
    return reasons


def check_canon_sits(desk, card):
    """Check 4: canon sits where the card says -- inside the desk's canon/, with canon.md and purpose.md."""
    reasons = []
    raw = str(card.get("canon") or "").strip()
    if not raw:
        return reasons
    p = os.path.normpath(os.path.join(desk, raw))
    canon_dir = os.path.normpath(os.path.join(desk, "canon"))
    if os.path.exists(p) and not (p == canon_dir or p.startswith(canon_dir + os.sep)):
        reasons.append("check 4 (canon sits where the card says): canon does not sit in the desk's canon/: %s" % raw)
    if os.path.exists(canon_dir):
        for need in ("canon.md", "purpose.md"):
            if not os.path.isfile(os.path.join(canon_dir, need)):
                reasons.append("check 4 (canon sits where the card says): canon/ is missing %s" % need)
    return reasons


_FENCE_RE = re.compile(r"^```jobs\s*$")
_ROW_RE = re.compile(r"^\s*([^|#\s][^|]*?)\s*\|")


def check_jobs_through_door(desk):
    """Check 5: any ```jobs rows the desk ships go through the job door (--check-row PASS)."""
    rows = []  # (row name, file)
    for base, _dirs, files in os.walk(desk):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            path = os.path.join(base, fn)
            try:
                with open(path, encoding="utf-8") as f:
                    lines = f.read().splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            inside = False
            for line in lines:
                if _FENCE_RE.match(line):
                    inside = True
                    continue
                if inside and line.strip() == "```":
                    inside = False
                    continue
                if inside:
                    m = _ROW_RE.match(line)
                    if m:
                        rows.append((m.group(1).strip(), path))
    reasons = []
    for name, path in rows:
        env = dict(os.environ)
        env["LIFEHACK_JOBS_FILE"] = path
        env["LIFEHACK_CODE_ROOT"] = env.get("LIFEHACK_CODE_ROOT") or ROOT
        r = subprocess.run(["bash", os.path.join(ROOT, "system", "tools", "install-schedulers.sh"),
                            "--check-row", name], capture_output=True, text=True, env=env)
        if r.returncode != 0:
            out = (r.stdout or r.stderr or "").strip().splitlines()
            first = out[0].strip() if out else "exit %d" % r.returncode
            reasons.append("check 5 (jobs go through the job door): job door refused job row %r in %s: %s"
                           % (name, os.path.relpath(path, desk), first))
    return reasons


def check_no_copied_tools(desk):
    """Check 6: no file in the desk folder is a byte-for-byte copy of a shared tool."""
    shared_files = {}
    for base, _dirs, files in os.walk(os.path.join(ROOT, "shared")):
        for fn in files:
            p = os.path.join(base, fn)
            try:
                with open(p, "rb") as f:
                    shared_files.setdefault(hashlib.sha256(f.read()).hexdigest(), p)
            except OSError:
                continue
    reasons = []
    for base, _dirs, files in os.walk(desk):
        for fn in files:
            p = os.path.join(base, fn)
            try:
                with open(p, "rb") as f:
                    h = hashlib.sha256(f.read()).hexdigest()
            except OSError:
                continue
            if h in shared_files:
                reasons.append("check 6 (no copied shared tools): copied shared tool: %s duplicates %s "
                               "(a desk uses the platform's tools, it never carries a copy)"
                               % (os.path.relpath(p, desk), os.path.relpath(shared_files[h], ROOT)))
    return reasons


def resolve_desk(arg):
    """A desk folder given directly, or a desk_id resolved through the person's desk list."""
    if os.path.isdir(arg):
        return os.path.abspath(arg), None
    folder, err = desk_list.desk_folder(arg)
    if err:
        return None, "the desk list cannot be read: %s" % err
    if not folder:
        return None, "no desk folder for %r (not a folder, and the desk list names no such desk_id)" % arg
    reg = desk_list.resolve_desk_list()
    if reg:
        base = os.path.dirname(reg)
        if os.path.basename(base) == "desks":   # the real layout: <notes>/desks/desk-registry.yaml
            base = os.path.dirname(base)
        p = os.path.join(base, "desks", folder)
    else:
        return None, "no desk folder for %r (not a folder, and there is no desk list)" % arg
    if not os.path.isdir(p):
        return None, "no desk folder: %s (the desk list names it, the folder is not there)" % p
    return p, None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print("usage: desk_door.py <desk-folder | desk_id>", file=sys.stderr)
        return 2
    desk, err = resolve_desk(argv[0])
    if err:
        print(err)
        return 1
    card, err = read_card(desk)
    reasons = [err] if err else []
    if card is not None:
        reasons += check_card_facts(card)
        reasons += check_owned_elsewhere(card)
        reasons += check_pointers(desk, card)
        reasons += check_canon_sits(desk, card)
    reasons += check_jobs_through_door(desk)
    reasons += check_no_copied_tools(desk)
    if reasons:
        for r in reasons:
            print(r)
        return 1
    print("PASS %s" % desk)
    return 0


if __name__ == "__main__":
    sys.exit(main())
