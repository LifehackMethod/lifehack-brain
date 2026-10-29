#!/usr/bin/env python3
"""refresh_staged.py — v2 step 1.3b: keep the register's DERIVED fields fresh for the files in THIS commit.

Called by system/githooks/pre-commit. CI (register-drift.yml) goes red whenever a registered file is
edited without the register being re-harvested, because the row's `sha` goes stale. This closes that gap at
commit time, for exactly the registered files that are staged -- no full re-harvest.

WHAT IT REFRESHES: for each STAGED file (added/copied/modified/renamed) that has a public tool / skill /
githook row, every field harvest.py DERIVES from the file: `sha` (harvest's own short_sha), `exists`,
`language` (tool), `name`/`description` (skill), `hook_name`/`commands` (githook). The fresh values come from
harvest.py's OWN harvest_tools / harvest_skills / harvest_githooks run over a scratch tree holding only the
STAGED blobs, so they match what CI computes. NEVER touched: identity (id/type/repo/path), the hand-written
needs/returns/group, `cost_bytes`/`cost_ms` (measured later by the fire-journal, not derivable from the file),
and every hook / scheduled row (no per-file source; CI excludes hooks and verifies wiring separately).

HOW: reads the STAGED register blob (never the working copy), rewrites only the matching lines, stores the
result with `git hash-object -w` + `git update-index --cacheinfo` (so unstaged edits are never swept in), then
applies the same row changes to the working copy -- only rows whose working line still equals the old staged
line; any other case leaves that row and prints a note to stderr.

STDOUT: exactly one line when something changed, nothing otherwise.
EXIT: 0 ok / nothing to do; 1 = could not refresh -> the hook REFUSES the commit (fail closed).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REG = "system/register/register.jsonl"
REFRESH_TYPES = ("tool", "skill", "githook")
KEEP = {"id", "type", "repo", "path", "needs", "returns", "group", "cost_bytes", "cost_ms"}


class Refuse(Exception):
    pass


def git(*args, input=None, check=True):
    r = subprocess.run(["git", *args], input=input, capture_output=True)
    if check and r.returncode != 0:
        raise Refuse("git %s failed: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace").strip()))
    return r


def main():
    top = git("rev-parse", "--show-toplevel").stdout.decode().strip()
    os.chdir(top)
    r = git("show", ":" + REG, check=False)
    if r.returncode != 0:
        return 0  # no register in the index: nothing to keep fresh
    staged_reg = r.stdout.decode("utf-8")
    lines = staged_reg.split("\n")
    by_path = {}  # "/rel/path" -> (line index, row)
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as e:
            raise Refuse("the STAGED %s line %d is not valid JSON (%s)" % (REG, i + 1, e))
        if not isinstance(row, dict) or "id" not in row:
            raise Refuse("the STAGED %s line %d is not a register row" % (REG, i + 1))
        if row.get("type") in REFRESH_TYPES and row.get("repo") == "public":
            by_path[row.get("path")] = (i, row)

    names = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").stdout.decode("utf-8").split("\0")
    hits = [n for n in names if n and "/" + n in by_path]
    if not hits:
        return 0

    try:
        sys.path.insert(0, HERE)
        import harvest
    except Exception as e:  # noqa: BLE001 -- any import failure must refuse
        raise Refuse("could not import harvest.py (%s: %s)" % (type(e).__name__, e))

    scratch = tempfile.mkdtemp(prefix="refresh-staged-")
    try:
        for n in hits:
            blob = git("show", ":" + n).stdout  # STAGED bytes, not the working tree
            dest = os.path.join(scratch, n)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(blob)
        none = os.path.join(scratch, "__no_private_root__")
        fresh = {}
        for fn in (harvest.harvest_tools, harvest.harvest_skills, harvest.harvest_githooks):
            for row in fn(scratch, none):
                fresh[row["id"]] = row
    except Refuse:
        raise
    except Exception as e:  # noqa: BLE001
        raise Refuse("harvest failed on the staged files (%s: %s)" % (type(e).__name__, e))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    changes = {}  # line index -> (old line, new line)
    changed_names = []
    for n in hits:
        i, old = by_path["/" + n]
        new_src = fresh.get(old["id"])
        if new_src is None:
            continue  # exempt class etc.: harvest would not register it, so nothing to derive
        new = dict(old)
        for k, v in new_src.items():
            if k not in KEEP:
                new[k] = v
        if new != old:
            new_line = json.dumps(new, sort_keys=True, ensure_ascii=False)
            changes[i] = (lines[i], new_line)
            changed_names.append(n)
    if not changes:
        return 0

    new_lines = list(lines)
    for i, (_, nl) in changes.items():
        new_lines[i] = nl
    new_blob = "\n".join(new_lines).encode("utf-8")

    ls = git("ls-files", "-s", "--", REG).stdout.decode().split()
    mode = ls[0] if ls else "100644"
    oid = git("hash-object", "-w", "--stdin", input=new_blob).stdout.decode().strip()
    git("update-index", "--cacheinfo", "%s,%s,%s" % (mode, oid, REG))

    # Same row changes into the working copy, only where it cannot clobber someone's unstaged edit.
    try:
        if os.path.isfile(REG):
            with open(REG, "rb") as f:
                work_text = f.read().decode("utf-8")
            if work_text == staged_reg:
                work_out = new_blob.decode("utf-8")
            else:
                wl = work_text.split("\n")
                skipped = []
                for i, (old_line, nl) in changes.items():
                    row_id = json.loads(old_line)["id"]
                    for j, w in enumerate(wl):
                        if w == old_line:
                            wl[j] = nl
                            break
                    else:
                        skipped.append(row_id)
                work_out = "\n".join(wl)
                if skipped:
                    print("pre-commit: note: working-copy %s has unstaged edits to %d refreshed row(s); "
                          "left as-is: %s" % (REG, len(skipped), ", ".join(skipped)), file=sys.stderr)
            if work_out != work_text:
                tmp = REG + ".refresh-tmp"
                with open(tmp, "wb") as f:
                    f.write(work_out.encode("utf-8"))
                os.replace(tmp, REG)
    except Exception as e:  # noqa: BLE001 -- the index is already right; the working copy is a courtesy
        print("pre-commit: note: could not update the working-copy %s (%s); the commit itself is correct"
              % (REG, e), file=sys.stderr)

    print("pre-commit: refreshed register sha for %d staged file(s): %s"
          % (len(changed_names), ", ".join(changed_names)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refuse as e:
        print("  REFUSED: %s" % e, file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print("  REFUSED: unexpected %s: %s" % (type(e).__name__, e), file=sys.stderr)
        sys.exit(1)
