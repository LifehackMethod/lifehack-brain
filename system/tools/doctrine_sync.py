#!/usr/bin/env python3
"""doctrine_sync.py — keep the per-machine doctrine files in step between two machines.

WHY THIS EXISTS (2026-08-22, on the operator's ruling). Three files are deliberately
gitignored and live in the repo folder, outside the notes folder: `CLAUDE.local.md` (the hard
rules), `.claude/settings.local.json` (the loader ceiling) and `.brain-root`. So neither `git pull`
nor Drive carries them between the desktop and the laptop. Until today the only bridge was a
hand-refreshed copy in `state/doctrine-mirror/` plus a hand-written handoff per change — and it
drifted within a day (one pointer sentence edited on the desktop 2026-08-21, nobody re-mirrored,
the laptop ran an edit behind until a session noticed).

WHAT IT DOES. Two mirrored files, one shared mirror in the notes folder (which Drive syncs), a
3-way compare per machine, and findings through the ONE Hospital writer so the session-start line
speaks drift unasked.

    push    local → mirror            (the edit-time act; also run by the PostToolUse hook)
    check   3-way compare, emit ONE finding per file; AHEAD auto-pushes   (rides the 5-min sweep)
    pull    mirror → local, diff shown, old local ARCHIVED first          (the visible repair act)
    status  print the table, no writes

THE 3-WAY COMPARE — local sha · mirror sha · this machine's last-synced sha:
    OK        local == mirror
    AHEAD     mirror == last-synced, local moved   → this machine's own edit; safe to push (the
              mirror has not moved since we last agreed) — check does it, and says so.
    BEHIND    local == last-synced, mirror moved   → the other machine pushed; a human runs `pull`.
    CONFLICT  both moved (or never synced here and they differ) → a human decides; nothing copied.
    NO-MIRROR local exists, mirror absent         → first adoption; pushed.
    NO-LOCAL  mirror exists, local absent         → a human runs `pull`.

WHAT IT NEVER DOES. It never overwrites a local doctrine file on its own: `pull` is the only
mirror→local copy, it prints the diff, and it archives the old local copy to
`records/logs/_ARCHIVE_doctrine-sync/` before writing (the never-delete rule: archive, under the
notes folder's `records/logs/_ARCHIVE_*/` convention).

`.brain-root` IS NOT MIRRORED. The notes path is per-machine by design (a different home folder
spells a different path). Its sha is recorded in this machine's state file for visibility only —
never flagged, never copied.

WHY THE MACHINE NAME IS IN THE PRODUCER. `emit_finding.py` pins `machine="local"` (single-machine
product by design), so a shared shard `<producer>.local.jsonl` written from two machines is exactly
the file Drive forked on 2026-08-21. Producer `doctrine-sync-<machine>` gives one writer per path.
Same reason the per-machine sync state is `state/doctrine-mirror/machine.<machine>.json` — each
machine writes only its own; the shared `manifest.json` is written only on a push (rare, a human's
edit behind it).

EXIT CODES (pulse contract): 0 ran (a DRIFT finding is an OUTPUT, not a failure) · 75 stood down
(no brain root configured — nothing honest to write to) · 1 usage error.

Compatible with /usr/bin/python3 (3.9) — stdlib only.
"""
import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
CODE_ROOT_DEFAULT = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(CODE_ROOT_DEFAULT, "shared"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from brain_root import resolve_brain_root            # noqa: E402
from emit_finding import emit_finding                # noqa: E402

# (repo-relative local path, mirror filename)
MIRRORED = (("CLAUDE.local.md", "CLAUDE.local.md"),
            (".claude/settings.local.json", "settings.local.json"))
INFO_ONLY = ".brain-root"
MIRROR_SUBDIR = os.path.join("state", "doctrine-mirror")
ARCHIVE_SUBDIR = os.path.join("records", "logs", "_ARCHIVE_doctrine-sync")
FINDINGS_SUBDIR = os.path.join("state", "findings")
PRODUCER_PREFIX = "doctrine-sync-"
STATUS_FOR = {"OK": "OK", "AHEAD": "OK", "NO-MIRROR": "OK",
              "BEHIND": "DRIFT", "NO-LOCAL": "DRIFT", "CONFLICT": "NEEDS_REVIEW"}
HINT_FOR = {"OK": "in step",
            "AHEAD": "this machine's own edit — pushed to the mirror",
            "NO-MIRROR": "first adoption — pushed to the mirror",
            "BEHIND": "the other machine pushed a newer copy — run: python3 system/tools/doctrine_sync.py pull",
            "NO-LOCAL": "mirror has a copy this machine lacks — run: python3 system/tools/doctrine_sync.py pull",
            "CONFLICT": "both copies moved — run: python3 system/tools/doctrine_sync.py pull --dry-run, read the diff, then decide (pull, or edit + push)"}

_SLUG = re.compile(r"[^a-z0-9]+")


def slug(s):
    s = _SLUG.sub("-", (s or "").lower()).strip("-")
    return s or "unknown"


def machine_token():
    env = os.environ.get("LIFEHACK_MACHINE", "").strip()
    if env:
        return slug(env)
    if sys.platform == "darwin":
        try:
            # Absolute path on purpose: scutil lives in /usr/sbin, which the pulse crontab's PATH omits.
            # A bare "scutil" there fell through to `hostname -s` and registered this same Mac as a
            # second machine (the About-name slug vs the hostname slug, found 2026-08-22).
            scutil = "/usr/sbin/scutil" if os.path.exists("/usr/sbin/scutil") else "scutil"
            out = subprocess.run([scutil, "--get", "ComputerName"], capture_output=True,
                                 text=True, timeout=5).stdout.strip()
            if out:
                return slug(out)
        except Exception:
            pass
    try:
        out = subprocess.run(["hostname", "-s"], capture_output=True, text=True, timeout=5).stdout.strip()
        if out:
            return slug(out)
    except Exception:
        pass
    return "unknown"


def sha256_file(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except (FileNotFoundError, NotADirectoryError):
        return None


def now_iso():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def copy_atomic(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".tmp"
    with open(src, "rb") as fi, open(tmp, "wb") as fo:
        fo.write(fi.read())
    os.replace(tmp, dst)


def classify(local_sha, mirror_sha, synced_sha):
    if local_sha is None and mirror_sha is None:
        return "OK"            # neither side has it — nothing to keep in step (settings may not exist yet)
    if mirror_sha is None:
        return "NO-MIRROR"
    if local_sha is None:
        return "NO-LOCAL"
    if local_sha == mirror_sha:
        return "OK"
    if synced_sha is None:
        return "CONFLICT"
    if local_sha == synced_sha:
        return "BEHIND"
    if mirror_sha == synced_sha:
        return "AHEAD"
    return "CONFLICT"


class Ctx:
    def __init__(self, code_root, brain_root, machine):
        self.code_root = code_root
        self.brain_root = brain_root
        self.machine = machine
        self.mirror_dir = os.path.join(brain_root, MIRROR_SUBDIR)
        self.manifest_path = os.path.join(self.mirror_dir, "manifest.json")
        self.state_path = os.path.join(self.mirror_dir, "machine.%s.json" % machine)
        self.archive_dir = os.path.join(brain_root, ARCHIVE_SUBDIR)
        self.findings_dir = os.path.join(brain_root, FINDINGS_SUBDIR)
        self.producer = PRODUCER_PREFIX + machine

    def local(self, rel):
        return os.path.join(self.code_root, rel)

    def mirror(self, name):
        return os.path.join(self.mirror_dir, name)

    def manifest(self):
        return load_json(self.manifest_path, {"schema_version": 1, "files": {}})

    def state(self):
        return load_json(self.state_path, {"schema_version": 1, "machine": self.machine, "files": {}})


def select(names):
    if not names:
        return list(MIRRORED)
    picked = []
    for rel, name in MIRRORED:
        if rel in names or name in names or os.path.basename(rel) in names:
            picked.append((rel, name))
    unknown = [n for n in names if not any(n in (rel, name, os.path.basename(rel)) for rel, name in MIRRORED)]
    if unknown:
        raise SystemExit("doctrine_sync: unknown file(s) %s — mirrored files are: %s"
                         % (unknown, [rel for rel, _ in MIRRORED]))
    return picked


def do_push(ctx, pairs, reason, out=sys.stdout):
    manifest = ctx.manifest()
    state = ctx.state()
    pushed = []
    for rel, name in pairs:
        src = ctx.local(rel)
        sha = sha256_file(src)
        if sha is None:
            print("push  %-28s SKIP — no local file at %s" % (name, src), file=out)
            continue
        copy_atomic(src, ctx.mirror(name))
        manifest["files"][name] = {"sha256": sha, "pushed_by": ctx.machine,
                                   "pushed_at": now_iso(), "reason": reason}
        state["files"].setdefault(name, {})["synced_sha256"] = sha
        pushed.append(name)
        print("push  %-28s local -> mirror  sha %s  (%s)" % (name, sha[:16], reason), file=out)
    if pushed:
        save_json(ctx.manifest_path, manifest)
        save_json(ctx.state_path, state)
    return pushed


def do_check(ctx, emit=True, auto_push=True, out=sys.stdout):
    """Returns list of (name, kind). Emits one finding per mirrored file. Never raises past its
    own ERROR finding — a check that cannot run is a RED, never a silent pass."""
    results = []
    try:
        manifest = ctx.manifest()
        state = ctx.state()
        for rel, name in MIRRORED:
            local_sha = sha256_file(ctx.local(rel))
            mirror_sha = sha256_file(ctx.mirror(name))
            synced = state["files"].get(name, {}).get("synced_sha256")
            kind = classify(local_sha, mirror_sha, synced)
            if kind in ("AHEAD", "NO-MIRROR") and auto_push:
                do_push(ctx, [(rel, name)], reason="auto: %s on check" % kind.lower(), out=out)
                manifest = ctx.manifest()
                state = ctx.state()
                mirror_sha = sha256_file(ctx.mirror(name))
            if kind == "OK" and local_sha is not None:
                # both sides agree: that IS a sync point — record it, or a later divergence on
                # this machine cannot tell BEHIND from CONFLICT (caught by the unit test)
                state["files"].setdefault(name, {})["synced_sha256"] = local_sha
            status = STATUS_FOR[kind]
            summary = "%s: %s — %s" % (name, kind, HINT_FOR[kind])
            pushed_by = manifest["files"].get(name, {}).get("pushed_by")
            payload = {"kind": kind, "local_sha256": local_sha, "mirror_sha256": mirror_sha,
                       "last_synced_sha256": synced, "mirror_pushed_by": pushed_by,
                       "mirror_pushed_at": manifest["files"].get(name, {}).get("pushed_at")}
            if emit:
                emit_finding(producer=ctx.producer, status=status, scanned_n=len(MIRRORED),
                             labels={"check": "doctrine-sync", "file": name, "machine": ctx.machine},
                             summary=summary, payload=payload, findings_dir=ctx.findings_dir,
                             done_when=None if status == "OK" else
                             "a later check on this machine classifies %s as OK — after `pull`, "
                             "or after an edit here followed by `push`" % name)
            state["files"].setdefault(name, {}).update(
                {"local_sha256": local_sha, "last_check": now_iso(), "kind": kind})
            results.append((name, kind))
            print("check %-28s %-9s %s" % (name, kind, HINT_FOR[kind]), file=out)
        state["brain_root_sha256"] = sha256_file(ctx.local(INFO_ONLY))
        state["last_check"] = now_iso()
        save_json(ctx.state_path, state)
    except Exception as e:          # fail-safe: the failure itself becomes the finding
        if emit:
            try:
                emit_finding(producer=ctx.producer, status="ERROR", scanned_n=0,
                             labels={"check": "doctrine-sync", "file": "_self", "machine": ctx.machine},
                             summary="doctrine-sync check crashed: %s: %s" % (type(e).__name__, e),
                             findings_dir=ctx.findings_dir)
            except Exception as e2:
                print("doctrine_sync: check crashed AND could not emit: %s / %s" % (e, e2), file=sys.stderr)
        print("doctrine_sync: check crashed: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        results.append(("_self", "ERROR"))
    return results


def do_pull(ctx, pairs, dry_run, out=sys.stdout):
    state = ctx.state()
    pulled = []
    for rel, name in pairs:
        dst = ctx.local(rel)
        src = ctx.mirror(name)
        mirror_sha = sha256_file(src)
        if mirror_sha is None:
            print("pull  %-28s SKIP — mirror has no copy" % name, file=out)
            continue
        local_sha = sha256_file(dst)
        if local_sha == mirror_sha:
            print("pull  %-28s already in step" % name, file=out)
            state["files"].setdefault(name, {})["synced_sha256"] = mirror_sha
            continue
        local_lines = open(dst, encoding="utf-8", errors="replace").read().splitlines() if local_sha else []
        mirror_lines = open(src, encoding="utf-8", errors="replace").read().splitlines()
        diff = list(difflib.unified_diff(local_lines, mirror_lines, fromfile="local/" + rel,
                                         tofile="mirror/" + name, lineterm="", n=2))
        print("\n".join(diff) if diff else "(binary or identical-text difference)", file=out)
        if dry_run:
            print("pull  %-28s DRY-RUN — nothing written" % name, file=out)
            continue
        if local_sha is not None:
            stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
            arch = os.path.join(ctx.archive_dir, "%s.%s.%s" % (name, ctx.machine, stamp))
            copy_atomic(dst, arch)
            print("pull  %-28s archived old local -> %s" % (name, arch), file=out)
        copy_atomic(src, dst)
        state["files"].setdefault(name, {})["synced_sha256"] = mirror_sha
        pulled.append(name)
        print("pull  %-28s mirror -> local  sha %s" % (name, mirror_sha[:16]), file=out)
    save_json(ctx.state_path, state)
    return pulled


def do_status(ctx, out=sys.stdout):
    manifest = ctx.manifest()
    state = ctx.state()
    print("machine: %s   mirror: %s" % (ctx.machine, ctx.mirror_dir), file=out)
    for rel, name in MIRRORED:
        local_sha = sha256_file(ctx.local(rel))
        mirror_sha = sha256_file(ctx.mirror(name))
        synced = state["files"].get(name, {}).get("synced_sha256")
        kind = classify(local_sha, mirror_sha, synced)
        m = manifest["files"].get(name, {})
        print("  %-28s %-9s local %s  mirror %s  (mirror pushed by %s at %s)" % (
            name, kind, (local_sha or "-")[:12], (mirror_sha or "-")[:12],
            m.get("pushed_by", "-"), m.get("pushed_at", "-")), file=out)
    print("  %-28s %-9s sha %s  (info only — per-machine by design)" % (
        INFO_ONLY, "INFO", (sha256_file(ctx.local(INFO_ONLY)) or "-")[:12]), file=out)
    try:
        others = sorted(f for f in os.listdir(ctx.mirror_dir)
                        if f.startswith("machine.") and f.endswith(".json") and f != os.path.basename(ctx.state_path))
    except OSError:
        others = []
    for f in others:
        o = load_json(os.path.join(ctx.mirror_dir, f), {})
        kinds = ", ".join("%s=%s" % (k, v.get("kind", "?")) for k, v in sorted(o.get("files", {}).items()))
        print("  other machine %-16s last check %s  %s" % (o.get("machine", f), o.get("last_check", "-"), kinds), file=out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["push", "check", "pull", "status"])
    ap.add_argument("files", nargs="*", help="subset of mirrored files (default: all)")
    ap.add_argument("--reason", default="manual push")
    ap.add_argument("--dry-run", action="store_true", help="pull: show the diff, write nothing")
    ap.add_argument("--no-emit", action="store_true", help="check: compare only, no findings")
    ap.add_argument("--no-auto-push", action="store_true", help="check: never push AHEAD/NO-MIRROR")
    ap.add_argument("--code-root", default=None, help="(tests) repo root holding the local files")
    ap.add_argument("--brain-root", default=None, help="(tests) notes root; default via shared/brain_root.py")
    ap.add_argument("--machine", default=None, help="override the machine token")
    a = ap.parse_args(argv)

    code_root = a.code_root or CODE_ROOT_DEFAULT
    brain_root = a.brain_root
    if brain_root is None:
        _src, brain_root = resolve_brain_root()
        if not brain_root:
            print("doctrine_sync: stood down — no notes root configured (shared/brain_root.py NOT-SET); "
                  "nothing honest to write to. Fix: python3 shared/brain_root.py --set <folder>", file=sys.stderr)
            return 75
    ctx = Ctx(code_root, brain_root, a.machine or machine_token())

    if a.cmd == "push":
        do_push(ctx, select(a.files), a.reason)
        return 0
    if a.cmd == "check":
        do_check(ctx, emit=not a.no_emit, auto_push=not a.no_auto_push)
        return 0
    if a.cmd == "pull":
        do_pull(ctx, select(a.files), a.dry_run)
        return 0
    do_status(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
