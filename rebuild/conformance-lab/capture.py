#!/usr/bin/env python3
"""
capture.py — Sub-agent transcript CAPTURE for the door-tester rebuild.

WHY THIS EXISTS (the bug it fixes):
The old "freeze" stored only a session-id POINTER into ~/.claude/projects/*.jsonl —
a path outside the repo, un-hashed, garbage-collectable. The tester could grade a
run whose base transcript had already been deleted and silently PASS. This module
COPIES THE BYTES instead: it locates the sub-agent transcripts Claude Code auto-writes
and (T3) snapshots + hashes them into an owned store.

GROUND TRUTH (verified 2026-07-24 against 71 real on-disk subagents dirs / 2552 transcripts):
  Claude Code writes each spawned sub-agent to:
    ~/.claude/projects/<cwd-slug>/<parent_session_id>/subagents/agent-<agentId>.jsonl
  plus a sidecar  agent-<agentId>.meta.json = {agentType, description, toolUseId, spawnDepth}.
  The parent session transcript is  ~/.claude/projects/<cwd-slug>/<parent_session_id>.jsonl.
  Sub-agent transcript lines carry  isSidechain: true  and record their own  cwd.

  The <cwd-slug> transform (empirically pinned, NO dash-collapse):
    every non-alphanumeric char in the ABSOLUTE cwd -> '-'.
    e.g. /Users/x/My Drive/_ClaudeOps -> -Users-x-My-Drive--ClaudeOps   (note the '--')

PRE-MORTEM (grounded): the naive path-finding is wrong -> a wrong slug = empty
glob = silent zero-capture. So resolve_subagent_dir() is a NAMED function with its own
CANARY (verify_slug_roundtrip): it re-derives the slug from a transcript's OWN recorded
cwd and asserts it matches the directory the transcript sits in. If the transform ever
changes, the canary fails LOUD instead of the resolver silently returning nothing.
"""

import hashlib
import json
import os
import re
import shutil
import sys
import time

PROJECTS_ROOT = os.path.expanduser("~/.claude/projects")

# The cwd every conformance-lab `claude -p` session launches from (probes/session.py
# LAUNCH_CWD). A spawned sub-agent inherits this cwd, so its slug is deterministic.
LAUNCH_CWD = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


# ---------------------------------------------------------------------------
# The slug transform + the named resolver (T3.0)
# ---------------------------------------------------------------------------

def cwd_to_slug(cwd: str) -> str:
    """Claude Code's projects-dir slug for a working directory.

    Empirically: abspath, then every non-alphanumeric char -> '-', NO collapse.
    """
    abspath = os.path.abspath(os.path.expanduser(cwd))
    return re.sub(r"[^A-Za-z0-9]", "-", abspath)


def resolve_subagent_dir(sandbox_cwd: str, parent_sid: str, projects_root: str = None) -> str:
    """The directory Claude Code writes a session's sub-agent transcripts into.

    NAMED + canaried on purpose (pre-mortem catch): a wrong slug returns an empty
    glob, which reads as 'the skill spawned nothing'. Callers MUST distinguish
    'dir missing' from 'dir present but empty' (see snapshot / the drift sentinel).

    projects_root defaults to ~/.claude/projects; overridable so the canary can
    point at a synthetic fixture tree (deterministic, no live-session dependency).
    """
    root = projects_root or PROJECTS_ROOT
    slug = cwd_to_slug(sandbox_cwd)
    return os.path.join(root, slug, parent_sid, "subagents")


def parent_transcript_path(sandbox_cwd: str, parent_sid: str, projects_root: str = None) -> str:
    """Path to the PARENT session's own transcript (<sid>.jsonl)."""
    root = projects_root or PROJECTS_ROOT
    slug = cwd_to_slug(sandbox_cwd)
    return os.path.join(root, slug, parent_sid + ".jsonl")


def base_alive(sandbox_cwd: str, parent_sid: str, projects_root: str = None) -> bool:
    """True iff the parent transcript still exists on disk (not GC'd).

    This is the exact check the old pointer-freeze skipped -> it could grade a
    dead base. A False here must poison the grade (INCONCLUSIVE), never pass.
    """
    return os.path.isfile(parent_transcript_path(sandbox_cwd, parent_sid, projects_root))


# ---------------------------------------------------------------------------
# Reading the transcripts + meta sidecars
# ---------------------------------------------------------------------------

def parse_agent_meta(meta_path: str) -> dict:
    """Load an agent-<id>.meta.json sidecar. Returns {} on any failure."""
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _agent_id_from_jsonl(jsonl_path: str) -> str:
    """agent-<agentId>.jsonl -> <agentId>."""
    base = os.path.basename(jsonl_path)
    m = re.match(r"agent-(.+)\.jsonl$", base)
    return m.group(1) if m else base


def _first_record(jsonl_path: str) -> dict:
    """First parseable JSON line of a transcript (carries cwd/sessionId/isSidechain)."""
    try:
        with open(jsonl_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    return json.loads(line)
                except Exception:
                    continue
    except Exception:
        pass
    return {}


def _first_cwd(jsonl_path: str) -> str:
    """The first cwd recorded anywhere in a transcript.

    The very first line can be a summary record with no cwd, so we scan (bounded)
    for the first record that actually carries one.
    """
    try:
        with open(jsonl_path, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i > 50:  # cwd appears in the opening records; don't scan whole file
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("cwd"):
                    return d["cwd"]
    except Exception:
        pass
    return ""


def list_subagents(subdir: str) -> list:
    """Every sub-agent under a subagents/ dir, with its meta merged.

    Returns a list of dicts: {agentId, jsonl, meta_path, agentType, description,
    toolUseId, spawnDepth, cwd, session_sid}. cwd/session_sid come from the
    transcript's first record (used by the slug canary + base linkage).
    """
    out = []
    if not os.path.isdir(subdir):
        return out
    for name in sorted(os.listdir(subdir)):
        if not (name.startswith("agent-") and name.endswith(".jsonl")):
            continue
        jsonl = os.path.join(subdir, name)
        agent_id = _agent_id_from_jsonl(jsonl)
        meta_path = os.path.join(subdir, "agent-%s.meta.json" % agent_id)
        meta = parse_agent_meta(meta_path)
        first = _first_record(jsonl)
        out.append({
            "agentId": agent_id,
            "jsonl": jsonl,
            "meta_path": meta_path,
            "meta_present": os.path.isfile(meta_path),
            "agentType": meta.get("agentType"),
            "description": meta.get("description"),
            "toolUseId": meta.get("toolUseId"),
            "spawnDepth": meta.get("spawnDepth"),
            "cwd": first.get("cwd"),
            "session_sid": first.get("sessionId"),
            "isSidechain": first.get("isSidechain"),
        })
    return out


# ---------------------------------------------------------------------------
# Quiescence (T3.1 primitive; used by snapshot). A torn/streaming write must
# never be copied as clean.
# ---------------------------------------------------------------------------

def is_quiescent(path: str, restat_wait_s: float = 0.4) -> tuple:
    """(quiescent: bool, reason: str).

    Quiescent iff: the final non-empty line parses as complete JSON AND
    (size, mtime) are stable across a short re-stat. Catches background/crash
    torn writes.
    """
    if not os.path.isfile(path):
        return False, "file missing"
    try:
        st1 = os.stat(path)
    except OSError as e:
        return False, "stat failed: %s" % e
    # last non-empty line must be complete JSON
    last = ""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last = line.strip()
    except Exception as e:
        return False, "read failed: %s" % e
    if not last:
        return False, "no content"
    try:
        json.loads(last)
    except Exception:
        return False, "final line not complete JSON (torn write)"
    # size+mtime stable across a re-stat
    time.sleep(restat_wait_s)
    try:
        st2 = os.stat(path)
    except OSError as e:
        return False, "re-stat failed: %s" % e
    if (st1.st_size, st1.st_mtime) != (st2.st_size, st2.st_mtime):
        return False, "size/mtime changed across re-stat (still being written)"
    return True, "quiescent"


def content_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# The resolver CANARY (T3.0 / T1.2 (c)) — self-proving against real bytes
# ---------------------------------------------------------------------------

def verify_slug_roundtrip(subdir: str) -> dict:
    """Re-derive the projects slug from the PARENT session transcript's own cwd
    field and assert it matches the on-disk slug directory.

    This is the resolver's canary: it does NOT trust cwd_to_slug()'s assumption,
    it proves it against ground truth. If Claude Code ever changes the transform,
    THIS fails loud rather than the resolver silently globbing empty.

    KEY (learned 2026-07-24): the slug is keyed to the PARENT session's launch cwd,
    NOT each sub-agent's cwd — a sub-agent can legitimately run in a subdirectory
    (its transcript records that subdir), yet its file is still filed under the
    parent's slug. So we verify against the parent transcript, not the sub-agents.

    Returns {ok, reason, parent_cwd}.
    """
    # subdir = .../projects/<slug>/<parent_sid>/subagents
    #   dirname^1 -> <parent_sid> dir ; dirname^2 -> <slug> dir.
    parent_sid_dir = os.path.dirname(os.path.abspath(subdir))
    slug_dir = os.path.dirname(parent_sid_dir)
    on_disk_slug = os.path.basename(slug_dir)
    parent_sid = os.path.basename(parent_sid_dir)
    parent_transcript = os.path.join(slug_dir, parent_sid + ".jsonl")

    if not os.path.isfile(parent_transcript):
        return {"ok": False, "reason": "parent transcript missing (base not alive): %s"
                % parent_transcript, "parent_cwd": None}
    parent_cwd = _first_cwd(parent_transcript)
    if not parent_cwd:
        return {"ok": False, "reason": "parent transcript records no cwd", "parent_cwd": None}
    derived = cwd_to_slug(parent_cwd)
    if derived != on_disk_slug:
        return {"ok": False, "parent_cwd": parent_cwd,
                "reason": "slug mismatch: parent cwd %r -> %r but dir slug is %r"
                          % (parent_cwd, derived, on_disk_slug)}
    return {"ok": True, "parent_cwd": parent_cwd,
            "reason": "slug roundtrip verified from parent cwd %r" % parent_cwd}


# ---------------------------------------------------------------------------
# The capture spike (T3.0 GATE) — prove the copy path on ONE real fan-out,
# runnable OFFLINE against an already-captured session (zero API cost).
# ---------------------------------------------------------------------------

def spike(sandbox_cwd: str, parent_sid: str, expected_count=None,
          expected_agentType=None, projects_root: str = None) -> dict:
    """Prove, against a REAL on-disk session, that we can:
      (1) resolve the subagents dir,
      (2) find the transcripts + parse every meta sidecar,
      (3) confirm toolUseId links back to a parent Agent call,
      (4) confirm base_alive detection,
      (5) pass the slug-roundtrip canary,
      (6) (optional) found-count == spawned-count / agentType matches.

    GATE semantics: returns {"gate": "PASS"|"FAIL", ...}. FAIL if any of the
    load-bearing checks fail. expected_count/agentType are the {count,agentType}
    contract (T3.2) when known; omitted for a pure discovery spike.
    """
    result = {"sandbox_cwd": sandbox_cwd, "parent_sid": parent_sid}
    subdir = resolve_subagent_dir(sandbox_cwd, parent_sid, projects_root)
    result["subdir"] = subdir
    result["subdir_exists"] = os.path.isdir(subdir)
    result["base_alive"] = base_alive(sandbox_cwd, parent_sid, projects_root)

    if not result["subdir_exists"]:
        result["gate"] = "FAIL"
        result["reason"] = "subagents dir does not resolve: %s" % subdir
        return result

    agents = list_subagents(subdir)
    result["found_count"] = len(agents)
    result["all_meta_present"] = all(a["meta_present"] for a in agents) and bool(agents)
    result["all_toolUseId"] = all(bool(a["toolUseId"]) for a in agents) and bool(agents)
    result["agentTypes"] = sorted({a["agentType"] for a in agents if a["agentType"]})
    result["all_sidechain"] = all(a["isSidechain"] is True for a in agents) and bool(agents)

    canary = verify_slug_roundtrip(subdir)
    result["slug_canary"] = canary

    checks = {
        "subdir_exists": result["subdir_exists"],
        "base_alive": result["base_alive"],
        "found_nonzero": result["found_count"] > 0,
        "all_meta_present": result["all_meta_present"],
        "all_toolUseId_link": result["all_toolUseId"],
        "all_sidechain": result["all_sidechain"],
        "slug_canary_ok": canary["ok"],
    }
    if expected_count is not None:
        checks["count_matches_expected"] = (result["found_count"] == expected_count)
    if expected_agentType is not None:
        checks["agentType_matches_expected"] = (result["agentTypes"] == [expected_agentType])

    result["checks"] = checks
    result["gate"] = "PASS" if all(checks.values()) else "FAIL"
    result["failed_checks"] = [k for k, v in checks.items() if not v]
    return result


# ---------------------------------------------------------------------------
# T3.1/T3.2/T3.3 — snapshot the sub-agent transcripts (copy the BYTES),
# the {count, agentType} contagious gate, and the drift sentinel.
# ---------------------------------------------------------------------------

class DriftError(RuntimeError):
    """The harness moved/hid the transcripts under us — a LOUD tester-self-failure,
    distinct from 'the skill spawned nothing'. Must ABORT the grade, never fold to
    a quiet INCONCLUSIVE (T3.3)."""


def _captured_at():
    # Date.now() is unavailable in the workflow sandbox but this is a normal process;
    # still, keep it injectable for deterministic tests.
    import datetime
    return datetime.datetime.utcnow().isoformat() + "Z"


def snapshot_subagents(sandbox_cwd, parent_sid, dest_root, seam_id="seam",
                       run_id="run", expected_count=None, expected_agentType=None,
                       projects_root=None, restat_wait_s=0.4, now_fn=None,
                       staging_root=None):
    """Copy every sub-agent transcript for a seam into an OWNED store, hashed.

    Order (T3.1): resolve dir -> drift sentinel (T3.3) -> per-file QUIESCENCE ->
    stage to LOCAL .staging -> move into dest_root/<run_id>/<seam_id>/ -> thinned
    records. Then the {count,agentType} gate (T3.2) sets the seam verdict.

    Returns a dict:
      {verdict: "captured"|"inconclusive", reason, base_alive, found, quiescent_n,
       expected_count, expected_agentType, agentTypes, dest, records:[{...}]}
    Raises DriftError for the T3.3 sentinel case.
    """
    now_fn = now_fn or _captured_at
    subdir = resolve_subagent_dir(sandbox_cwd, parent_sid, projects_root)
    alive = base_alive(sandbox_cwd, parent_sid, projects_root)
    exp = expected_count if expected_count is not None else 0

    subdir_present = os.path.isdir(subdir)
    agents = list_subagents(subdir) if subdir_present else []

    # ---- T3.3 DRIFT SENTINEL (loud) ----
    # Parent transcript is alive but the subagents subtree is absent/empty while we
    # EXPECTED fan-out -> the harness moved the files under us. ABORT, don't fold.
    if alive and exp > 0 and (not subdir_present or len(agents) == 0):
        raise DriftError(
            "DRIFT: parent transcript present (base alive) but subagents/ %s for "
            "seam %r with expected_count=%d — the harness moved/hid the transcripts. "
            "Refusing to grade (this is NOT 'the skill spawned nothing')."
            % ("absent" if not subdir_present else "empty", seam_id, exp))

    # ---- dead base -> inconclusive (never a silent pass); NOT drift ----
    if not alive:
        return {"verdict": "inconclusive", "reason": "base not alive (parent transcript "
                "GC'd) — cannot trust this capture", "base_alive": False,
                "found": len(agents), "quiescent_n": 0, "expected_count": expected_count,
                "expected_agentType": expected_agentType, "agentTypes": [],
                "dest": None, "records": []}

    # ---- expected==0 and empty -> clean (nothing to capture) ----
    if exp == 0 and len(agents) == 0:
        return {"verdict": "captured", "reason": "no fan-out expected, none present",
                "base_alive": True, "found": 0, "quiescent_n": 0,
                "expected_count": expected_count, "expected_agentType": expected_agentType,
                "agentTypes": [], "dest": None, "records": []}

    # ---- T3.1 per-file quiescence -> stage -> hash -> move ----
    staging_root = staging_root or os.path.join(_STAGING_DIR, run_id, seam_id)
    dest = os.path.join(dest_root, run_id, seam_id)
    os.makedirs(staging_root, exist_ok=True)
    os.makedirs(dest, exist_ok=True)

    records, non_quiescent = [], []
    captured_at = now_fn()
    for a in agents:
        q_ok, q_reason = is_quiescent(a["jsonl"], restat_wait_s=restat_wait_s)
        if not q_ok:
            # a torn/streaming write is NEVER copied as clean
            non_quiescent.append({"agentId": a["agentId"], "reason": q_reason})
            continue
        sha = content_sha256(a["jsonl"])
        staged = os.path.join(staging_root, os.path.basename(a["jsonl"]))
        shutil.copy2(a["jsonl"], staged)
        if a["meta_present"]:
            shutil.copy2(a["meta_path"], os.path.join(staging_root, os.path.basename(a["meta_path"])))
        final = os.path.join(dest, os.path.basename(a["jsonl"]))
        shutil.move(staged, final)
        if a["meta_present"]:
            shutil.move(os.path.join(staging_root, os.path.basename(a["meta_path"])),
                        os.path.join(dest, os.path.basename(a["meta_path"])))
        records.append({
            "toolUseId": a["toolUseId"], "agentType": a["agentType"],
            "content_sha256": sha, "quiescent": True, "base_alive": True,
            "captured_at": captured_at, "dest": final,
        })

    agent_types = sorted({r["agentType"] for r in records if r["agentType"]})
    quiescent_n = len(records)

    # ---- T3.2 {count, agentType} gate (contagious -> inconclusive) ----
    reasons = []
    if non_quiescent:
        reasons.append("%d non-quiescent (torn) transcript(s): %s"
                       % (len(non_quiescent), [x["agentId"] for x in non_quiescent]))
    if expected_count is not None and quiescent_n < expected_count:
        reasons.append("captured %d < expected %d" % (quiescent_n, expected_count))
    if expected_agentType is not None and agent_types != [expected_agentType]:
        reasons.append("agentType %s != expected [%s]" % (agent_types, expected_agentType))

    verdict = "inconclusive" if reasons else "captured"
    return {"verdict": verdict, "reason": "; ".join(reasons) or "captured==expected, quiescent",
            "base_alive": True, "found": len(agents), "quiescent_n": quiescent_n,
            "expected_count": expected_count, "expected_agentType": expected_agentType,
            "agentTypes": agent_types, "non_quiescent": non_quiescent,
            "dest": dest, "records": records}


_STAGING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".staging")


if __name__ == "__main__":
    # CLI: prove the resolver against a real session dir.
    #   python3 capture.py --spike <parent_sid> [--cwd <sandbox_cwd>]
    #                       [--expect-count N] [--expect-type <agentType>]
    #   python3 capture.py --scan     # list candidate real sessions with fan-outs
    def _arg(flag, default=None, cast=str):
        if flag in sys.argv:
            i = sys.argv.index(flag)
            if i + 1 < len(sys.argv):
                return cast(sys.argv[i + 1])
        return default

    if "--scan" in sys.argv:
        # find real sessions under LAUNCH_CWD's slug that have a subagents dir
        slug = cwd_to_slug(LAUNCH_CWD)
        root = os.path.join(PROJECTS_ROOT, slug)
        rows = []
        if os.path.isdir(root):
            for sid in os.listdir(root):
                sub = os.path.join(root, sid, "subagents")
                if os.path.isdir(sub):
                    agents = list_subagents(sub)
                    if agents:
                        types = sorted({a["agentType"] for a in agents if a["agentType"]})
                        rows.append((len(agents), sid, ",".join(types)))
        rows.sort(reverse=True)
        print("real captured fan-outs under %s:" % slug)
        for n, sid, types in rows[:30]:
            print("  %2d agents  sid=%s  types=[%s]" % (n, sid, types))
        sys.exit(0)

    if "--spike" in sys.argv:
        sid = _arg("--spike")
        cwd = _arg("--cwd", LAUNCH_CWD)
        exp_count = _arg("--expect-count", None, int)
        exp_type = _arg("--expect-type", None)
        res = spike(cwd, sid, expected_count=exp_count, expected_agentType=exp_type)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("gate") == "PASS" else 1)

    print(__doc__)
    print("usage: capture.py --scan | --spike <parent_sid> [--cwd C] "
          "[--expect-count N] [--expect-type T]")
