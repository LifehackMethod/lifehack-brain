#!/usr/bin/env python3
# not-wired-yet: card 7.1 wires this into the SubagentStop hook; nothing calls it before then.
"""read_coverage.py [--documents-only] TRANSCRIPT.jsonl [FILE ...] — from a helper's record
(the JSONL transcript), which lines of each FILE did the helper actually open with the Read tool?

The file list is OPTIONAL. With no FILE arguments, the tool derives the file list from the
transcript itself: every file opened with the Read tool, plus every file touched through a shell
reader (cat, sed, head, tail, awk, a safe-reader script). Each derived file gets its total line
count read from disk; a derived file that no longer exists on disk is listed as "gone from disk,
not countable" (exit 1). With FILE arguments given, only those files are reported, exactly as before.

Prints, one line per file: lines opened of total, and FULL or PARTIAL with the gaps. Proves OPENED,
not understood. A Read that returned an error counts as nothing. A file the helper read through a
shell command (cat, sed, head, tail, awk, a safe-reader script) is listed as "read through the shell,
not counted" — never full, never dropped: the counter says what it could not see. Lines of the record
that are not valid JSON are counted and reported.

--documents-only limits the report to .md and .txt files; code files are ignored (a builder opening
part of a code file is normal; a partial read of a document is the signal).

Exit 0 nothing partial or uncountable · 1 something partial or not countable · 4 the record could
not be read. Always prints "EXAMINED n files"; if the record cannot be read, prints
COULD NOT READ TRANSCRIPT.

Tested by test_read_coverage.py. stdlib only."""
import argparse
import json
import os
import sys

READ_DEFAULT_LIMIT = 2000  # the Read tool's own default when no limit is given
SHELL_TOOLS = ("Bash", "Grep")
SHELL_READER_HINTS = ("cat ", "sed ", "head ", "tail ", "awk ", "less ", "safe_read.py ",
                      "safe-reader", "safe_fetch")
DOCS_EXT = (".md", ".txt")


def walk(obj, reads, shells, errored):
    """Walk one parsed JSON value: collect Read tool_use inputs by id, shell tool calls
    naming a path, and ids of tool_use calls whose result was an error."""
    if isinstance(obj, dict):
        if obj.get("type") == "tool_use":
            name = obj.get("name")
            inp = obj.get("input") or {}
            if name == "Read":
                reads[obj.get("id")] = inp
            elif name in SHELL_TOOLS:
                shells.append((name, json.dumps(inp)))
        elif obj.get("type") == "tool_result" and obj.get("is_error"):
            errored.add(obj.get("tool_use_id"))
        for v in obj.values():
            walk(v, reads, shells, errored)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, reads, shells, errored)


def line_gaps(seen, total):
    """[start, end] 1-based inclusive ranges of unopened lines."""
    gaps, i = [], 1
    while i <= total:
        if not seen[i]:
            j = i
            while j < total and not seen[j + 1]:
                j += 1
            gaps.append((i, j))
            i = j + 1
        else:
            i += 1
    return gaps


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--documents-only", action="store_true",
                    help="report .md/.txt files only; code files are ignored")
    ap.add_argument("transcript")
    ap.add_argument("files", nargs="*",
                    help="optional; with no FILE args, every file the transcript shows the helper opening is reported")
    args = ap.parse_args(argv)

    if not args.files:
        derived = []          # transcript-only mode: discover the files from the record
    else:
        derived = args.files  # explicit mode: report exactly what was asked

    # ---- read the record ----
    try:
        with open(args.transcript, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except Exception as e:
        print(f"COULD NOT READ TRANSCRIPT: {e}")
        print("EXAMINED 0 files")
        return 4

    reads, shells, errored, n_json, n_bad = {}, [], set(), 0, 0
    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            n_bad += 1
            continue
        walk(obj, reads, shells, errored)
        n_json += 1
    if not n_json:
        print(f"COULD NOT READ TRANSCRIPT: no valid JSON lines in {args.transcript}")
        print("EXAMINED 0 files")
        return 4
    if n_bad:
        print(f"WARNING: {n_bad} transcript line(s) were not valid JSON and were not counted; "
              "coverage below may be understated")

    # ---- transcript-only mode: derive the file list from the record ----
    if not derived:
        for tid, inp in reads.items():
            pth = inp.get("file_path")
            if pth:
                derived.append(pth)
        for name, inp in shells:
            try:
                cmd = json.loads(inp).get("command", "")
            except Exception:
                cmd = inp
            for seg in cmd.replace("&&", ";").replace("|", ";").split(";"):
                if not any(h in seg for h in SHELL_READER_HINTS):
                    continue
                for tok in seg.split():
                    tok = tok.strip("'\"")
                    if tok.startswith("-"):
                        continue
                    if "/" in tok:
                        derived.append(tok)
    files = []
    for f in derived:
        rf = os.path.realpath(f)
        if rf not in files and not os.path.isdir(rf):
            files.append(rf)

    def shell_touched(f):
        """A shell read means a READER command (cat/sed/head/tail/awk/less/safe-reader)
        ran with this file's name in the SAME command segment — a pipeline tail like
        `wc -l file | tail -3` counts the file, it does not read it."""
        base = os.path.basename(f)
        hits = []
        for name, inp in shells:
            try:
                cmd = json.loads(inp).get("command", "")
            except Exception:
                cmd = inp
            for seg in cmd.replace("&&", ";").replace("|", ";").split(";"):
                if base in seg and any(h in seg for h in SHELL_READER_HINTS):
                    hits.append((name, inp[:150]))
                    break
        return hits

    # ---- per-file coverage ----
    ok = True
    examined = 0
    for f in files:
        if args.documents_only and not f.lower().endswith(DOCS_EXT):
            continue
        examined += 1
        shell_hits = shell_touched(f)
        if not os.path.isfile(f):
            print(f"GONE FROM DISK, not countable: {os.path.basename(f)}")
            ok = False
            continue
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                total = sum(1 for _ in fh)
        except Exception as e:
            print(f"NOT COUNTABLE cannot read file on disk: {os.path.basename(f)}: {e}")
            ok = False
            continue
        seen = [False] * (total + 2)
        reads_n = errs_n = 0
        for tid, inp in reads.items():
            path = inp.get("file_path") or ""
            if os.path.realpath(path) != f:
                continue
            if tid in errored:
                errs_n += 1
                continue  # an errored Read counts as nothing
            reads_n += 1
            start = max(int(inp.get("offset") or 1), 1)
            limit = int(inp.get("limit") or READ_DEFAULT_LIMIT)
            for i in range(start, min(start + limit, total + 1)):
                seen[i] = True
        got = sum(seen[1:total + 1])
        gaps = line_gaps(seen, total)
        full = got == total and not shell_hits
        if not full:
            ok = False
        line = (f"{'FULL' if full else 'PARTIAL'} {got}/{total} reads={reads_n} "
                f"errors={errs_n} {os.path.basename(f)}")
        if gaps:
            shown = ", ".join(f"{a}-{b}" for a, b in gaps[:8])
            more = " ..." if len(gaps) > 8 else ""
            line += f" gaps: {shown}{more}"
        print(line)
        if shell_hits:
            print("  read through the shell, not counted: "
                  + "; ".join(f"{n}: {t}" for n, t in shell_hits[:3]))

    print(f"EXAMINED {examined} files")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
