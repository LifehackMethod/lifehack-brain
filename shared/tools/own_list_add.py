#!/usr/bin/env python3
"""own_list_add.py -- your OWN list of your OWN tools (Round B piece 2, "your own list").

WHY: a tool, skill or runner you build lives in your personal code folder (shared/personal_code_root.py). The
plugin's master register (system/register/register.jsonl) is for SHARED tools only; yours are listed in YOUR list,
`<personal code folder>/register.jsonl`, same JSONL shape (one object per line: {"type","path","id",...}).
No GitHub, no git needed: it is a plain file in your own folder.

Usage:
  own_list_add.py PATH...            add each path (inside your personal code folder) to your own list; idempotent
  own_list_add.py --check PATH...    print one line per path that SHOULD be listed and is not (the end-of-turn
                                     check, system/hooks/end_of_turn_checks.sh, calls this); exit 0 always
  own_list_add.py --unhomed PATH...  (switch own_list_unhomed) print one message per NEW code file that sits outside
                                     every home (plugin, notes, personal code folder); exit 0 always
  own_list_add.py --keep PATH...     list a file that stays OUTSIDE the homes by the person's choice, in your own list,
                                     keyed by its ABSOLUTE path (row has "kept": true)
  own_list_add.py --root             print the resolved personal code folder and the list file
A "tool" here = a .py/.sh file (not a test, not under tests/fixtures/archive/_retired/hidden folders) or a SKILL.md,
inside the personal code folder. Rows are keyed by the path RELATIVE to that folder, with a leading slash.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import personal_code_root  # noqa: E402

LIST_NAME = "register.jsonl"
SKIP_DIR = re.compile(r"^(tests?|fixtures?|__pycache__|node_modules|\..*|_retired.*|_?archive.*)$", re.I)


def root_or_none():
    src, path = personal_code_root.resolve_personal_code_root()
    return os.path.realpath(path) if src in ("pointer", "default") else None


def rel_key(root, path):
    """-> '/rel/path' when path is a file inside root, else None."""
    rp = os.path.realpath(path)
    if not rp.startswith(root + os.sep):
        return None
    return rp[len(root):]


def _project_skills_on():
    """Switch placement_project_skills (system/hooks/roundB.conf, read through lib/roundb.py): a skill or agent under a PROJECT folder's .claude/ is the person's own code."""
    try:
        sys.path.insert(0, os.path.join(HERE, "..", "..", "system", "hooks", "lib"))
        from roundb import roundb_on
        return roundb_on("placement_project_skills")
    except Exception:
        return False
    finally:
        sys.path.pop(0)


def _shebang_file_on(path, base):
    """Switch code_shebang (system/hooks/roundB.conf): True for an extensionless file whose first line is #!."""
    if "." in base:
        return False
    try:
        sys.path.insert(0, os.path.join(HERE, "..", "..", "system", "hooks", "lib"))
        from roundb import roundb_on
        if not roundb_on("code_shebang"):
            return False
        with open(path, "rb") as fh:
            return fh.read(2) == b"#!"
    except Exception:
        return False
    finally:
        sys.path.pop(0)


def is_tool(rel, full=None):
    parts = rel.strip("/").split("/")
    base = parts[-1]
    proj_claude = _project_skills_on() and any(parts[i] == ".claude" and i + 1 < len(parts) and parts[i + 1] in ("skills", "agents") for i in range(len(parts))) and not rel.startswith(os.path.expanduser("~/.claude") + os.sep)   # placement_project_skills
    if any(SKIP_DIR.match(p) and not (proj_claude and p == ".claude") for p in parts[:-1]):
        return False
    if base == "SKILL.md":
        return True
    if not base.endswith((".py", ".sh")) and _shebang_file_on(full or rel, base):   # code_shebang: an extensionless file that opens with #!
        return not base.startswith(".") and not base.startswith("test_")
    if not base.endswith((".py", ".sh")) or base.startswith("test_") or re.search(r"_tests?\.(py|sh)$", base):
        return False
    return not base.startswith(".")


def kept_folders():
    """Folders the person KEPT on purpose: lines `kept<TAB><folder>[<TAB>reason]` in ~/.config/lifehack/placement.conf
    (the personal override file; load_placement ignores 2/3-field lines, so these are harmless there). One place to
    change if the remember_reason helper settles on another format."""
    out = []
    try:
        for ln in open(os.path.join(os.path.expanduser("~"), ".config", "lifehack", "placement.conf"), encoding="utf-8"):
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 2 and f[0].strip() == "kept" and f[1].strip():
                out.append(os.path.realpath(os.path.expanduser(f[1].strip())))
    except OSError:
        pass
    return out


def unhomed_check(paths):
    """-> [(path, pc_root, suggested_abs, kept_bool)] for new code files outside every home and not yet listed.
    The 'outside every home + same scratch exemptions' decision is build_mode.outside_homes_target (imported, not copied);
    this feature has its own switch, so the placement switch is forced on for that one call."""
    sys.path.insert(0, os.path.join(HERE, "..", "..", "system", "hooks", "lib"))
    old = os.environ.get("ROUNDB_PLACEMENT_OUTSIDE_HOMES")
    os.environ["ROUNDB_PLACEMENT_OUTSIDE_HOMES"] = "on"
    try:
        import build_mode
        code = build_mode.code_root() or os.path.realpath(os.path.join(HERE, "..", ".."))
        notes = build_mode.notes_root(code)
        root = root_or_none()
        have, kept, out = (listed(root) if root else set()), kept_folders(), []
        for p in paths:
            t = os.path.realpath(p)
            if not os.path.isfile(t) or not is_tool(t):
                continue
            pc = build_mode.outside_homes_target(t, code, notes)
            if not pc or t in have:
                continue
            name = os.path.basename(t)
            sug = os.path.join(pc, "skills", os.path.basename(os.path.dirname(t)), name) if name == "SKILL.md" else os.path.join(pc, "tools", name)
            out.append((t, pc, sug, any(build_mode.under(t, k) for k in kept)))
        return out
    except Exception as e:  # degrade-safe: never wedge a turn
        sys.stderr.write("own_list_add --unhomed skipped: %s\n" % e)
        return []
    finally:
        sys.path.pop(0)
        if old is None:
            os.environ.pop("ROUNDB_PLACEMENT_OUTSIDE_HOMES", None)
        else:
            os.environ["ROUNDB_PLACEMENT_OUTSIDE_HOMES"] = old


def keep(paths):
    root = root_or_none()
    if not root:
        print("own_list_add: no personal code folder is set up (run: python3 system/tools/bootstrap.py)", file=sys.stderr)
        return 1
    have, rc = listed(root), 0
    for p in paths:
        t = os.path.realpath(p)
        if not os.path.isfile(t):
            print("own_list_add: %s is not a file -- not added" % p, file=sys.stderr)
            rc = 1
        elif t in have:
            print("already listed: " + t)
        else:
            row = {"id": "tool:own:" + t, "path": t, "type": "tool", "repo": "own", "kept": True}
            with open(os.path.join(root, LIST_NAME), "a", encoding="utf-8") as f:
                f.write(json.dumps(row, sort_keys=True) + "\n")
            have.add(t)
            print("listed (kept outside, by your choice): " + t)
    return rc


def listed(root):
    out = set()
    try:
        for ln in open(os.path.join(root, LIST_NAME), encoding="utf-8"):
            ln = ln.strip()
            if ln:
                try:
                    out.add("/" + str(json.loads(ln).get("path", "")).lstrip("/"))
                except (ValueError, AttributeError):
                    pass
    except OSError:
        pass
    return out


def cmd_for(path):
    return 'python3 "%s" "%s"' % (os.path.abspath(__file__), path)


def check(paths):
    root = root_or_none()
    if not root:
        return []
    have, out = listed(root), []
    for p in paths:
        k = rel_key(root, p)
        if k and os.path.isfile(p) and is_tool(k, p) and k not in have and k != "/" + LIST_NAME:
            out.append((p, k))
    return out


def add(paths):
    root = root_or_none()
    if not root:
        print("own_list_add: no personal code folder is set up (run: python3 system/tools/bootstrap.py)", file=sys.stderr)
        return 1
    have, rc = listed(root), 0
    for p in paths:
        k = rel_key(root, p)
        if not k or not os.path.isfile(p):
            print("own_list_add: %s is not a file inside %s -- not added" % (p, root), file=sys.stderr)
            rc = 1
            continue
        if k in have:
            print("already listed: " + k)
            continue
        row = {"id": "tool:own:" + k, "path": k, "type": "tool", "repo": "own"}
        with open(os.path.join(root, LIST_NAME), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
        have.add(k)
        print("listed: " + k)
    return rc


def main(argv):
    if len(argv) >= 2 and argv[1] == "--root":
        r = root_or_none()
        print("%s\n%s" % (r, os.path.join(r, LIST_NAME)) if r else "NOT-SET")
        return 0 if r else 1
    if len(argv) >= 2 and argv[1] == "--keep":
        return keep(argv[2:])
    if len(argv) >= 2 and argv[1] == "--unhomed":
        for t, pc, sug, kept in unhomed_check(argv[2:]):
            if kept:
                print("%s stays here by your choice; list it: python3 \"%s\" --keep \"%s\"" % (t, os.path.abspath(__file__), t))
            else:
                print("%s is outside all your homes: move it to %s, then run: %s" % (t, sug, cmd_for(sug)))
        return 0
    if len(argv) >= 2 and argv[1] == "--check":
        for p, k in check(argv[2:]):
            print("%s is not in your own list (%s). Add it: %s" % (p, os.path.join(root_or_none(), LIST_NAME), cmd_for(p)))
        return 0
    if len(argv) < 2:
        print(__doc__)
        return 1
    return add(argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
