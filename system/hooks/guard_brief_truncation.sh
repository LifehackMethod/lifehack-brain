#!/usr/bin/env bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "guard_brief_truncation.sh" "PreToolUse" "Write|Edit|MultiEdit|Bash" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: 2026-08-22. A graduation sub-agent located a section of the cowork-migration
#      brief with an UNANCHORED substring search -- s.index("<h2> 7. SCRATCHPAD") -- and
#      rewrote the file from that offset. That same text also appears at column 2 of a
#      hard-wrapped inline code span 2,161 lines EARLIER, inside a Story Log entry that is
#      itself the write-up of an identical near-miss on 2026-08-13. The tool matched the
#      NARRATIVE, not the heading, and 2,640 lines -- all of section 5 and section 6 and the
#      tail of section 4 -- were deleted in one write. Recovery took an 11:38 backup, a
#      35-block pad archive, and nine line-boundary assertions. THE SAME TRAP IS STILL IN
#      THE FILE and cannot be removed: the Story Log is append-only, so every future
#      write-up of this bug re-arms it. Anchored matching is already correct in both
#      copies of pad_archive.py (^##\s*7\.\s*SCRATCHPAD, MULTILINE, exactly one hit). The
#      surviving vector is AD-HOC IN-SESSION CODE, which no tool fix can reach.
#      Measured on the live file, 2026-08-22: unanchored = 4 hits, first at line 2272;
#      line-anchored = 1 hit, line 4433. Every one of the 8 section headings is unique
#      when anchored and 2 of them are not when unanchored.
# GUARDS: a write that would SHRINK a project brief substantially, arriving through any of
#      the three doors -- Write (content vs on-disk size), Edit/MultiEdit (summed
#      old_string/new_string delta), or Bash (an overwrite-shaped write detected by
#      lib/bash_write_door.sh). Scope is brief.md under a projects/ folder and the legacy
#      state/briefs/*.md. Threshold is BOTH >15% of the file AND >5,000 bytes, so an
#      ordinary scratchpad compaction (measured: 50,791 of 486,520 bytes = 10.4%) passes
#      untouched. Shell APPENDS (>> and tee -a) are never this guard's business -- they
#      cannot truncate. Sanctioned tools pass untouched too: `python3 .../pad_archive.py
#      archive --brief X` shows no write call in the command string, so the library
#      reports no target.
# REDIRECT: the block is lifted by a fresh snapshot beside the brief, which is the whole
#      point -- it converts an unrecoverable delete into a `cp` away. Run:
#        cp "<brief>" "<brief>.pre-shrink.bak"
#      then retry the identical write. The receipt must be newer than 15 minutes and at
#      least as large as the file it is protecting. AND FIX THE ACTUAL BUG WHILE YOU ARE
#      HERE: locate sections by LINE NUMBER with an asserted boundary, or by a
#      line-anchored regex (^##\s*N\.), never by substring search -- a heading quoted
#      inside prose is indistinguishable from the heading itself to str.index/.find.
# SIGNPOST: rule lives in system/sops/hook-sop.md + system/hook-contract.md; the incident
#      is STORY LOG 2026-08-22yy in the cowork-migration brief, and the 2026-08-13x entry
#      records the first instance of the same shape. Change the thresholds there with the
#      operator's sign-off, never by loosening this file to fit one write.
# FAIL_POSTURE: mixed, deliberately. Not-our-business exits 0 (this runs on every Bash,
#      Write and Edit call; a blanket deny on a transient glitch is worse than the gap).
#      But once a brief IS identified as the target, any failure to size the write DENIES
#      -- an unreadable payload and a safe payload must never look the same.
# UPDATED: 2026-08-22
# ─────────────────────────────────────────────────────────────────────────────
INPUT=$(cat)

SHRINK_PCT=15
SHRINK_MIN_BYTES=5000
RECEIPT_MAX_AGE=900

_HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

deny() {
  python3 -c '
import json,sys
print(json.dumps({"decision":"block","reason":sys.argv[1]}))
' "$1" >&2
  exit 2
}

# ── what tool, and what is it writing to? ────────────────────────────────────
TOOL=$(printf '%s' "$INPUT" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('tool_name',''))
except Exception: print('')
" 2>/dev/null)

case "$TOOL" in
  Write|Edit|MultiEdit|Bash) ;;
  *) exit 0 ;;
esac

if [ "$TOOL" = "Bash" ]; then
  COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except Exception: print('')
" 2>/dev/null)
  [ -z "$COMMAND" ] && exit 0

  # Cheap pre-filter: no brief-shaped path mentioned at all -> not our business.
  # WINDOWS BLIND SPOT, closed 2026-09-04. A native Windows path --
  # D:\...\state\projects\<slug>\brief.md -- contains no forward slash at all, so this
  # pattern could never fire on it and the Bash door stood wide open on this machine.
  # Measured that day: the pattern returned NO MATCH on a backslash path and the guard
  # exited 0. The typed-tool door below was never affected (fnmatch normalises on
  # Windows). Normalisation here is for DETECTION ONLY; $COMMAND is never rewritten.
  # Parameter expansion, not printf|tr: this runs on EVERY Bash call, ahead of the cheap
  # pre-filter below that decides whether this guard cares at all. Measured on Git Bash,
  # 40 iterations: the two-fork pipeline ~62 ms, this ~1.7 ms. Same result, no subprocess.
  COMMAND_NORM=${COMMAND//\\//}
  printf '%s' "$COMMAND_NORM" | grep -qE '(projects/[^ ]*/brief\.md|state/briefs/[^ ]*\.md)' || exit 0

  # shellcheck source=lib/bash_write_door.sh
  . "$_HOOKDIR/lib/bash_write_door.sh" 2>/dev/null || \
    deny "BLOCKED: guard_brief_truncation could not load lib/bash_write_door.sh, so it is failing closed. The Bash door into a project brief is unguarded without it, and that door is how 2,640 lines of the cowork-migration brief were deleted on 2026-08-22. REDIRECT: restore system/hooks/lib/bash_write_door.sh from git, then retry."

  # Append-only shapes cannot truncate. Neutralise them, then ask the library again:
  # if the brief stops being a write target once >> and tee -a are scrubbed, the command
  # was only ever appending.
  SCRUBBED=$(printf '%s' "$COMMAND" | sed -e 's/>>/ /g' -e 's/tee[[:space:]]\{1,\}-a/tee_append_noop/g')

  TARGETS=$(bwd_write_targets "$SCRUBBED")
  case "$TARGETS" in
    *__BWD_PARSE_ERROR__*)
      deny "BLOCKED: guard_brief_truncation could not analyse this command, and it names a project brief. WHY: on 2026-08-22 an unanchored substring search for a section heading matched the heading QUOTED INSIDE a Story Log entry 2,161 lines earlier, and the rewrite that followed deleted 2,640 lines. An unparseable command targeting a brief is refused rather than guessed at. REDIRECT: write the brief through the Write tool, or through system/tools/save/pad_archive.py, or snapshot first with: cp \"<brief>\" \"<brief>.pre-shrink.bak\" and retry. RULE: system/sops/hook-sop.md."
      ;;
  esac

  # The library emits one token per write target, but an inline interpreter write comes back as
  # the WHOLE expression -- open('.../brief.md','w').write(x) -- not as a bare path, so a suffix
  # test misses exactly the shape that caused the 2026-08-22 loss. Search INSIDE each target.
  HIT=$(printf '%s\n' "$TARGETS" | python3 -c '
import sys, re
PAT = re.compile(r"[^\s\x27\"()]*(?:/projects/[^\s\x27\"()]*/brief\.md|/state/briefs/[^\s\x27\"()]*\.md)")
for line in sys.stdin:
    # WINDOWS, 2026-09-04: match on a separator-normalised copy and emit the normalised
    # path. A forward-slash Windows path works in Git Bash stat/cp and in python alike.
    m = PAT.search(line.replace("\\", "/"))
    if m:
        print(m.group(0)); break
' 2>/dev/null)

  # FAIL-CLOSED BACKSTOP, added 2026-09-04 after a fire test showed the door still open.
  # MEASURED that day: lib/bash_write_door.sh returns an EMPTY target list for
  #   python3 -c "open(r'D:\...state\projects\<slug>\brief.md','w').write(x)"
  # -- an interpreter write whose path carries backslashes and spaces. HIT was then
  # empty and the guard exited 0, even though the pre-filter had ALREADY identified a
  # brief as the target. That contradicted this file's own FAIL_POSTURE: once a brief
  # IS the target, failing to size the write must DENY, because an unreadable payload
  # and a safe payload must never look the same.
  #
  # Reads and appends are unaffected: they carry no mutation verb, and >> has already
  # been scrubbed out of $SCRUBBED above, so no bare > survives an append.
  if [ -z "$HIT" ]; then
    SCRUBBED_NORM=${SCRUBBED//\\//}   # parameter expansion; see COMMAND_NORM above
    # Patterns built with ANSI-C quoting so the quote characters never appear
    # literally in shell source -- 2026-09-04: a literal " inside a double-quoted
    # pattern closed the string early and silently disabled this whole check.
    _BT_VERBS=$'\\.write[a-zA-Z]*\\(|\\.truncate\\(|open\\([^)]*,[[:space:]]*[\x27\x22][^\x27\x22]*[wax+]|os\\.(replace|rename|remove|unlink)|shutil\\.(move|copy)|write_text|writeFileSync'
    # [^>]* not [^ ]* -- this brain lives under 'Google Drive' and 'Shared drives',
    # and a space stopped the old class dead. Still requires the redirect to TARGET
    # a brief, so `cat <brief> > /dev/null` and `2>/dev/null` are not caught.
    # ⛔ ONE TOKEN, NOT THE REST OF THE LINE. Narrowed 2026-09-04. The previous class was
    # [^>]*, which spans spaces AND every other character, so ANY earlier redirect in the
    # command -- `2>/dev/null` above all -- followed by a brief path ANYWHERE later matched
    # as "a redirect targeting a brief". MEASURED: it blocked `pm_flag.sh arm <brief>`, a
    # command that only NAMES the path and writes nothing, twice in one session. The three
    # alternatives below are the three real shapes of a redirect target: double-quoted (may
    # contain spaces, which is why the old class was widened in the first place),
    # single-quoted, or bare (cannot contain a space). A bare `2>/dev/null ... brief.md` no
    # longer matches, because the bare alternative stops at the first space.
    _BT_REDIR=$'>[[:space:]]*(\x22[^\x22]*brief\\.md|\x27[^\x27]*brief\\.md|[^[:space:]\x22\x27>]*brief\\.md)'
    if printf '%s' "$SCRUBBED" | grep -qE "$_BT_VERBS" || \
       printf '%s' "$SCRUBBED_NORM" | grep -qE "$_BT_REDIR"; then
      # ── HONOUR THE REDIRECT THIS MESSAGE ADVERTISES. Added 2026-09-04. ──────────
      # The deny below says "snapshot first and retry within 15 minutes". Until this
      # block existed, nothing here looked for that receipt, so the redirect was a dead
      # end and every legitimate Bash write to a brief was refused. Same test the HIT
      # path uses: fresh, and not smaller than the file it protects.
      # The extractor takes QUOTED segments first, because a real brief path here lives
      # under folder names that contain spaces -- and a space is exactly what
      # defeated lib/bash_write_door.sh and put us in this branch to begin with.
      _BT_TARGET=$(printf '%s' "$COMMAND" | python3 -c "
import sys
cmd = sys.stdin.read().replace(chr(92), '/')
parts = []
for ch in (chr(34), chr(39)):
    seg = cmd.split(ch)
    parts += seg[1::2]
parts += cmd.split()
hits = [p for p in parts
        if p.endswith('/brief.md') or ('/state/briefs/' in p and p.endswith('.md'))]
print(hits[0] if hits else '')
" 2>/dev/null)
      if [ -n "$_BT_TARGET" ] && [ -f "$_BT_TARGET.pre-shrink.bak" ]; then
        _bt_now=$(date +%s)
        _bt_mt=$(stat -c %Y "$_BT_TARGET.pre-shrink.bak" 2>/dev/null || stat -f %m "$_BT_TARGET.pre-shrink.bak" 2>/dev/null || echo 0)
        _bt_bs=$(stat -c %s "$_BT_TARGET.pre-shrink.bak" 2>/dev/null || stat -f %z "$_BT_TARGET.pre-shrink.bak" 2>/dev/null || echo 0)
        _bt_cs=$(stat -c %s "$_BT_TARGET" 2>/dev/null || stat -f %z "$_BT_TARGET" 2>/dev/null || echo 0)
        if [ $(( _bt_now - _bt_mt )) -le "$RECEIPT_MAX_AGE" ] && [ "$_bt_bs" -ge "$_bt_cs" ]; then
          exit 0
        fi
      fi
      deny "BLOCKED: a MUTATING Bash command names a project brief, but the write-door library could not identify a target, so this guard is failing closed. WHY: measured 2026-09-04, lib/bash_write_door.sh returns no targets for an interpreter write whose path carries Windows backslashes and spaces -- and a sub-agent using exactly that shape truncated a live brief to ZERO BYTES the same morning, the third such loss since 2026-08-30. An unsizeable write to a brief is refused rather than guessed at. REDIRECT: (1) append instead -- >> and tee -a are never blocked and cannot truncate; (2) or use the Write/Edit tools, which this guard CAN size; (3) or, if the overwrite is intended, snapshot first -- cp <brief> <brief>.pre-shrink.bak -- and retry within 15 minutes. RULE: system/sops/hook-sop.md."
    fi
    exit 0    # append-only, or the brief is only being READ
  fi

  # NARROWING -- a false positive caught in fire-test, 2026-08-22. lib/bash_write_door.sh treats a
  # bare `open(` as evidence of a write, so an ORDINARY READ --
  #   python3 -c "print(len(open('<brief>').read()))"
  # -- came back as a write target and was denied. Reading a brief with python is routine and must
  # never be blocked. The tell is in the library's own output: a shell redirect or a write VERB
  # emits the bare path, while an interpreter emits the WHOLE expression and the path had to be dug
  # out of it. So: exact match = a real shell write, keep blocking. Extracted from inside a larger
  # token = an interpreter, and it only counts if the code actually MUTATES.
  # (hook-sop.md: "Narrow by evidence of a WRITE, never by adding words.")
  # ⛔ COMPARE LIKE WITH LIKE. Added 2026-09-04, found by fire test. $HIT is emitted from a
  # SEPARATOR-NORMALISED copy (the .replace above), $TARGETS is the raw text the command used.
  # On any Windows spelling the two therefore never matched, this test fell through to the
  # interpreter branch, that branch demands a write VERB, and a shell redirect has none --
  # so `echo x > "D:\...\brief.md"` EXITED 0 and the overwrite ran. MEASURED that day on a
  # fixture brief: forward-slash spelling BLOCK, mixed separators ALLOWED, native backslash
  # ALLOWED. That is the guard's whole purpose failing open on the platform it was written for.
  TARGETS_NORM=${TARGETS//\\//}
  if ! printf '%s\n' "$TARGETS_NORM" | grep -Fxq "$HIT"; then
    printf '%s' "$COMMAND" | grep -qE "\\.write[a-zA-Z]*\\(|\\.truncate\\(|open\\([^)]*,[[:space:]]*['\"][^'\"]*[wax+]|os\\.(replace|rename|remove|unlink)|shutil\\.(move|copy)|write_text|writeFileSync" \
      || exit 0
  fi

  # ── SPACE-AWARE TARGET. Added 2026-09-04, found by the fire test. ─────────────
  # $HIT comes from a [^\s] class, so it truncates at the last space in the path.
  # MEASURED that day on ".../My Test Brain/projects/testproj/brief.md", the guard
  # reported  TARGET: Brain/projects/testproj/brief.md  -- and then looked for the
  # receipt beside THAT, which does not exist. So a valid, fresh snapshot could never
  # lift the block, and the deny named the wrong file. The real brief lives under
  # folders whose names contain spaces, so this was live, not theoretical.
  # Re-derive from quoted segments; prefer it ONLY when it names a file that exists.
  # ⛔ Detection is untouched -- this changes which file we look BESIDE, never whether
  # the guard fires.
  _BT_FULL=$(printf '%s' "$COMMAND" | python3 -c "
import sys
cmd = sys.stdin.read().replace(chr(92), '/')
parts = []
for ch in (chr(34), chr(39)):
    seg = cmd.split(ch)
    parts += seg[1::2]
parts += cmd.split()
hits = [p for p in parts
        if p.endswith('/brief.md') or ('/state/briefs/' in p and p.endswith('.md'))]
print(hits[0] if hits else '')
" 2>/dev/null)
  if [ -n "$_BT_FULL" ] && [ -f "$_BT_FULL" ]; then HIT="$_BT_FULL"; fi

  # A Bash overwrite cannot be sized before it runs, so the snapshot is unconditional here.
  if [ -f "$HIT.pre-shrink.bak" ]; then
    now=$(date +%s)
    mt=$(stat -c %Y "$HIT.pre-shrink.bak" 2>/dev/null || stat -f %m "$HIT.pre-shrink.bak" 2>/dev/null || echo 0)
    age=$(( now - mt ))
    bs=$(stat -c %s "$HIT.pre-shrink.bak" 2>/dev/null || stat -f %z "$HIT.pre-shrink.bak" 2>/dev/null || echo 0)
    cs=$(stat -c %s "$HIT" 2>/dev/null || stat -f %z "$HIT" 2>/dev/null || echo 0)
    if [ "$age" -le "$RECEIPT_MAX_AGE" ] && [ "$bs" -ge "$cs" ]; then exit 0; fi
  fi

  deny "BLOCKED: an OVERWRITE-shaped Bash write to a project brief with no fresh snapshot beside it. TARGET: $HIT. WHY: on 2026-08-22 a sub-agent located a section of this exact kind of file with an unanchored substring search, matched the same heading QUOTED INSIDE a Story Log entry 2,161 lines above the real one, rewrote from that offset, and deleted 2,640 lines -- all of section 5, all of section 6, and the tail of section 4. A shell overwrite cannot be sized before it runs, so it is gated on recoverability instead of on size. Appends (>> and tee -a) are NOT blocked and never reach here. REDIRECT: (1) snapshot -- cp \"$HIT\" \"$HIT.pre-shrink.bak\" -- then retry the identical command; the receipt is honoured for 15 minutes. (2) AND FIX THE LOCATOR: find sections by LINE NUMBER with an asserted boundary, or by a line-anchored regex (^##\\s*N\\.), NEVER by str.index/.find on a heading string -- measured on the live brief, unanchored matching returns 4 hits and anchored returns 1. RULE: system/sops/hook-sop.md; incident: STORY LOG 2026-08-22yy."
fi

# ── typed tools: Write / Edit / MultiEdit -- these we CAN size ───────────────
if [ "$TOOL" != "Bash" ]; then
  RESULT=$(printf '%s' "$INPUT" | TOOL="$TOOL" SHRINK_PCT="$SHRINK_PCT" SHRINK_MIN_BYTES="$SHRINK_MIN_BYTES" python3 -c '
import sys, json, os, fnmatch

def blen(s): return len((s or "").encode("utf-8"))

try:
    d = json.load(sys.stdin)
except Exception:
    print("ERROR|unparseable tool payload|"); sys.exit(0)

tool = os.environ["TOOL"]
ti   = d.get("tool_input", {}) or {}
path = ti.get("file_path", "") or ""

if not (fnmatch.fnmatch(path, "*/projects/*/brief.md") or fnmatch.fnmatch(path, "*/state/briefs/*.md")):
    print("SKIP||"); sys.exit(0)

if not os.path.isfile(path):
    print("SKIP||"); sys.exit(0)          # creating a new brief cannot shrink one

try:
    cur = os.path.getsize(path)
except Exception:
    print("ERROR|cannot stat the brief|" + path); sys.exit(0)

removed = 0
try:
    if tool == "Write":
        removed = cur - blen(ti.get("content"))
    elif tool == "Edit":
        removed = blen(ti.get("old_string")) - blen(ti.get("new_string"))
    elif tool == "MultiEdit":
        for e in (ti.get("edits") or []):
            removed += blen(e.get("old_string")) - blen(e.get("new_string"))
except Exception:
    print("ERROR|cannot size the write|" + path); sys.exit(0)

if removed <= 0 or cur <= 0:
    print("SKIP||"); sys.exit(0)

pct = (removed * 100.0) / cur
if removed > int(os.environ["SHRINK_MIN_BYTES"]) and pct > float(os.environ["SHRINK_PCT"]):
    print("SHRINK|%d|%s|%.1f|%d" % (removed, path, pct, cur))
else:
    print("SKIP||")
' 2>/dev/null)

  case "$RESULT" in
    SKIP*|"") exit 0 ;;
    ERROR*)
      msg=$(printf '%s' "$RESULT" | cut -d'|' -f2)
      deny "BLOCKED: guard_brief_truncation identified a project brief as the write target but could not size the write ($msg), so it is failing closed. WHY: on 2026-08-22 an unsized rewrite of a brief deleted 2,640 lines; an unreadable payload and a safe one must never look the same. REDIRECT: snapshot first -- cp \"<brief>\" \"<brief>.pre-shrink.bak\" -- then retry. RULE: system/sops/hook-sop.md."
      ;;
    SHRINK*)
      removed=$(printf '%s' "$RESULT" | cut -d'|' -f2)
      path=$(printf   '%s' "$RESULT" | cut -d'|' -f3)
      pct=$(printf    '%s' "$RESULT" | cut -d'|' -f4)
      cur=$(printf    '%s' "$RESULT" | cut -d'|' -f5)

      if [ -f "$path.pre-shrink.bak" ]; then
        now=$(date +%s)
        mt=$(stat -c %Y "$path.pre-shrink.bak" 2>/dev/null || stat -f %m "$path.pre-shrink.bak" 2>/dev/null || echo 0)
        age=$(( now - mt ))
        bs=$(stat -c %s "$path.pre-shrink.bak" 2>/dev/null || stat -f %z "$path.pre-shrink.bak" 2>/dev/null || echo 0)
        if [ "$age" -le "$RECEIPT_MAX_AGE" ] && [ "$bs" -ge "$cur" ]; then exit 0; fi
      fi

      deny "BLOCKED: this $TOOL would remove $removed bytes (${pct}% of $cur) from a project brief, and there is no fresh snapshot beside it. TARGET: $path. WHY: on 2026-08-22 a sub-agent located a section of this exact file with an unanchored substring search, matched the same heading QUOTED INSIDE a Story Log entry 2,161 lines above the real heading, rewrote from that offset, and deleted 2,640 lines -- all of section 5, all of section 6, and the tail of section 4. Threshold is >15% AND >5,000 bytes, so a normal scratchpad compaction (measured 10.4%) never lands here; a shrink this size is either a real graduation or the same bug again. REDIRECT: (1) if this shrink is INTENDED, make it recoverable -- cp \"$path\" \"$path.pre-shrink.bak\" -- then retry the identical write; the receipt is honoured for 15 minutes. (2) if you computed the boundary by searching for a heading STRING, that is the bug: find sections by LINE NUMBER with an asserted boundary, or by a line-anchored regex (^##\\s*N\\.). Measured on the live brief: unanchored matching for the scratchpad heading returns 4 hits, the first 2,161 lines too early; anchored returns exactly 1. RULE: system/sops/hook-sop.md; incident: STORY LOG 2026-08-22yy."
      ;;
  esac
fi

exit 0
