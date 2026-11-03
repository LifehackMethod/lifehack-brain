#!/usr/bin/env python3
"""team_skills.py — share personal skills with a team through a Google Drive folder
(approved design 2026-11-01, SIMPLE build).

FILE-SYSTEM ONLY: the team folder is the local Drive-for-Desktop mount the person picks
(~/.config/lifehack/team-skills, resolved ONLY by shared/team_skills_root.py). No gws, no Drive
API, no network — everything here is os.symlink / copy / move on local paths.

The design in one breath (decisions, Enver 2026-11-01):
  - LIVE sharing by SYMLINK: ~/.claude/skills/<name> becomes a link to <team>/skills/<name>, so a
    teammate's edit arrives by itself; the session-start check re-hashes every linked tree and
    DROPS the link if a change fails the injection scan (the mid-session gap is accepted).
  - SCRIPTS inside shared skills are ALLOWED: scanned like any text file, and listed to the
    person in one plain line — never refused for being scripts.
  - Nothing is deleted anywhere: the sharer's local folder is MOVED to a backup; retire moves the
    team copy to _retired/; remove/unshare never touch the Drive copy.
  - Windows is best-effort: symlink, then (on OSError) a real copy with mode=copy in the ledger
    and a note that a copied skill is not live.

Safety: Drive content is OUTSIDE content. Every skill is VETTED before it is linked (injection
scan via system/tools/safe_input.py on every text file; no symlinks inside the tree; no `hooks:`
frontmatter), and the vetted tree's sha256 is PINNED in the ledger — `verify`/`update`/the
session check re-hash and re-vet on every change.

Subcommands: route (the sign the prompt hook prints, switch team_share_route) · question · discover · set · status · share (--no-link: the person declines the link) · unshare · use · update · verify · remove ·
--session-check (the SessionStart check, gated by the roundB switch team_skill_verify, default OFF).
`share` is dry-run by default; --yes after the person says yes.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.join(HERE, "..")
if SHARED not in sys.path:
    sys.path.insert(0, SHARED)
SAFE_INPUT_DIR = os.path.join(SHARED, "..", "system", "tools")
if os.path.isdir(SAFE_INPUT_DIR) and SAFE_INPUT_DIR not in sys.path:
    sys.path.insert(0, SAFE_INPUT_DIR)

import team_skills_root  # noqa: E402  shared/team_skills_root.py — the ONLY resolver for the team folder

QUESTION = ("Do you work with a team that shares skills on google drive or are you only using "
            "these on your own personal system on one computer?")
MARKER_NAME = ".lifehack-shared"
LEDGER_NAME = "team-skills-linked"
BACKUP_DIRNAME = os.path.join(".claude", "run", "team-skills-backup")
SCRIPT_EXTS = (".sh", ".py", ".js")
TEXT_EXTS = (".md", ".txt", ".py", ".sh", ".js", ".json", ".yaml", ".yml", ".csv", ".toml")


# ── paths (all under the person's HOME, computed at call time so tests can swap HOME) ──────────

def _cfg_dir():
    return os.path.join(os.path.expanduser("~"), ".config", "lifehack")


def ledger_path():
    return os.path.join(_cfg_dir(), LEDGER_NAME)


def skills_home():
    return os.path.join(os.path.expanduser("~"), ".claude", "skills")


def backup_root():
    return os.path.join(os.path.expanduser("~"), BACKUP_DIRNAME)


def _now():
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%S")


# ── hashing ────────────────────────────────────────────────────────────────────────────────────

def _file_sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tree_sha256(root):
    """sha256 of a skill tree: sorted relpaths + file hashes. MARKER_NAME is excluded (it is
    written by the tool after the copy, so it must not change what 'same tree' means)."""
    root = os.path.realpath(root)
    h = hashlib.sha256()
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for f in sorted(fns):
            if f == MARKER_NAME:
                continue
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, root)
            h.update(rel.encode("utf-8"))
            h.update(bytes.fromhex(_file_sha(full)))
    return h.hexdigest()


# ── vetting (design section 5) ────────────────────────────────────────────────────────────────

def vet_skill(root):
    """(ok, problems, script_names). Checks: SKILL.md exists; no symlinks inside the tree; no
    `hooks:` frontmatter; no injection patterns in any text file (safe_input.scan_for_injection).
    Scripts are ALLOWED — they are scanned like any file and returned in script_names for the
    one plain line, never refused for being scripts."""
    problems, scripts = [], []
    if not os.path.isfile(os.path.join(root, "SKILL.md")):
        problems.append("no SKILL.md")
        return False, problems, scripts
    try:
        import safe_input
    except ImportError:
        safe_input = None
    for dp, dns, fns in os.walk(root):
        for d in dns:
            if os.path.islink(os.path.join(dp, d)):
                problems.append("symlink inside the skill: " + os.path.relpath(os.path.join(dp, d), root))
        for f in sorted(fns):
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, root)
            if os.path.islink(full):
                problems.append("symlink inside the skill: " + rel)
                continue
            if f.endswith(SCRIPT_EXTS):
                scripts.append(rel)
            if not f.endswith(TEXT_EXTS):
                continue
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError as e:
                problems.append("unreadable file %s (%s)" % (rel, e))
                continue
            if f == "SKILL.md" and "\nhooks:" in "\n" + text:
                problems.append("SKILL.md declares hooks: (a shared skill must not install hooks)")
            if safe_input is not None:
                for _match, label in safe_input.scan_for_injection(text):
                    problems.append("%s looks like an injection (%s)" % (rel, label))
                    break
    return (not problems), problems, scripts


# ── the ledger (tool-made links; remove/unshare only ever touch rows that are in it) ───────────

def read_ledger():
    try:
        with open(ledger_path(), encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except (OSError, ValueError):
        return []


def write_ledger(rows):
    os.makedirs(_cfg_dir(), exist_ok=True)
    tmp = ledger_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    os.replace(tmp, ledger_path())


def upsert_row(row):
    rows = [r for r in read_ledger() if r.get("name") != row["name"]]
    rows.append(row)
    write_ledger(rows)


def drop_row(name):
    write_ledger([r for r in read_ledger() if r.get("name") != name])


# ── linking (with the Windows best-effort fallback) ───────────────────────────────────────────

def link_skill(target, link):
    """Make <link> point at <target>: symlink; on OSError (Windows without Developer Mode) a real
    COPY with mode=copy (a copied skill is not live — update re-copies when the hash differs).
    Writes the ledger row (the pinned vetted tree hash) either way.
    -> (mode, messages). NEVER overwrites: the caller checks the clash first."""
    try:
        os.symlink(os.path.realpath(target), link)
        mode, notes = "symlink", []
    except OSError:
        shutil.copytree(target, link, symlinks=False)
        mode, notes = "copy", ["note: this skill was COPIED, not linked — it does not update itself "
                               "from the team folder; `update` re-copies it when the team copy changes"]
    upsert_row({"name": os.path.basename(link), "target": os.path.realpath(target),
                "sha256": tree_sha256(target), "mode": mode, "linked_at": _now()})
    return mode, notes


# ── commands ───────────────────────────────────────────────────────────────────────────────────

def cmd_question(_a):
    print(QUESTION)
    print("Run: python3 %s set team <folder>   (or: set solo)" % os.path.abspath(__file__))
    return 0


def route_text():
    """The street sign for someone asked to share a skill: the ONE route, in commands that work as printed. A team folder the person
    already chose is never asked about or repointed; `solo` or nothing saved gets the first-time route (asking to share IS the new answer)."""
    t = 'python3 "%s"' % os.path.abspath(__file__)
    source, path = team_skills_root.resolve_team_skills_root()
    ready = source == "pointer" and team_skills_root.sharing_mode() == "team"
    lines = ["[team-share] A skill reaches other people through the team's Google Drive folder. Not a zip, a repo or a plugin. "
             "They asked, so do it now, one command at a time:"]
    if ready:
        lines.append("1. %s share <skill-name> --yes --no-link   (team folder already set: %s)" % (t, os.path.realpath(path)))
    else:
        lines.append("1. %s discover" % t)
        lines.append('2. %s set team "<the folder discover marks or suggests>" --create' % t)
        lines.append("3. %s share <skill-name> --yes --no-link" % t)
        lines.append("No Drive found: ask for the folder's path.")
    first = "" if ready else "do steps 1 and 2 anyway, "
    lines.append("Skill not in ~/.claude/skills/<skill-name>/ yet: %sbuild it there if you know what it does; if not, "
                 "end with the plan (folder, commands, link) and one question: what it should do." % first)
    lines.append("Final message: where the Drive copy is, and recommend once a link to it from ~/.claude/skills: best practice, "
                 "not required; one copy, so edits reach everyone; each computer once; they can decline. On yes:")
    lines.append("%s share <skill-name> --yes" % t)
    return "\n".join(lines)


def cmd_route(_a):
    print(route_text())
    return 0


def _notes_root():
    try:
        import brain_root
        source, path = brain_root.resolve_brain_root()
    except Exception:
        return None
    return os.path.realpath(path) if source not in (None, "permission-denied") and path else None


TEAM_MARKER = ".lifehack-team-skills"   # sits in a team folder `set team` accepted, so a teammate's `discover` finds it
DEFAULT_TEAM_DIRNAME = "Team skills"


def drive_mounts():
    """Every local Drive-for-Desktop 'My Drive' folder of THIS person (macOS: ~/Library/CloudStorage/GoogleDrive-*/My Drive;
    Windows best-effort: <letter>:/My Drive). Read-only, one glob, never a walk (walking a synced drive can hang)."""
    import glob
    hits = glob.glob(os.path.join(os.path.expanduser("~"), "Library", "CloudStorage", "GoogleDrive-*", "My Drive"))
    if os.name == "nt":
        hits += [p for p in ("%s:\\My Drive" % c for c in "DEFGHIJ") if os.path.isdir(p)]
    return sorted(h for h in hits if os.path.isdir(h))


def discover_candidates(mounts):
    """Folders at depth <= 2 under each mount that hold TEAM_MARKER or are named like a team/skills folder. No recursion."""
    out = []
    for m in mounts:
        level = [m]
        for _depth in (1, 2):
            nxt = []
            for parent in level:
                try:
                    names = sorted(os.listdir(parent))
                except OSError:
                    continue
                for n in names:
                    p = os.path.join(parent, n)
                    if n.startswith(".") or not os.path.isdir(p) or os.path.islink(p):
                        continue
                    nxt.append(p)
                    low = n.lower()
                    if os.path.isfile(os.path.join(p, TEAM_MARKER)) or "skill" in low or "team" in low:
                        out.append(p)
            level = nxt
    return out


def cmd_discover(_a):
    mounts = drive_mounts()
    if not mounts:
        print("no Google Drive folder found on this computer (Drive for Desktop puts it under "
              "~/Library/CloudStorage/GoogleDrive-<account>/My Drive). Install Drive for Desktop, or ask the "
              "person for the folder path, then: set team <folder>")
        return 1
    print("Google Drive on this computer:")
    for m in mounts:
        print("  " + m)
    cands = discover_candidates(mounts)
    if cands:
        print("folders that look like a team skills folder:")
        for i, c in enumerate(cands, 1):
            print("  %d. %s%s" % (i, c, "  (already a team folder)" if os.path.isfile(os.path.join(c, TEAM_MARKER)) else ""))
    suggestion = os.path.join(mounts[0], DEFAULT_TEAM_DIRNAME)
    if cands:   # a real choice: which folder is the team's is the person's call
        print("Pick one with the person, or make a new one:  set team \"%s\" --create" % suggestion)
    else:       # nothing to choose between
        print("No team folder yet. Make this one:  python3 \"%s\" set team \"%s\" --create" % (os.path.abspath(__file__), suggestion))
    return 0


def cmd_set(a):
    mode = a.mode.strip().lower()
    if mode not in ("team", "solo"):
        print("REFUSED: answer must be exactly 'team' or 'solo' (ask the person the question; "
              "never guess). Run: python3 %s question" % os.path.abspath(__file__))
        return 2
    os.makedirs(_cfg_dir(), exist_ok=True)
    with open(os.path.join(_cfg_dir(), "team-sharing"), "w", encoding="utf-8") as f:
        f.write(mode + "\n")
    if mode == "solo":
        print("saved: team-sharing=solo. Your skills stay on this machine only.")
        return 0
    folder = os.path.expanduser((a.folder or "").strip())
    if not folder:
        print("REFUSED: 'team' needs the folder. Ask the person which Drive folder the team shares "
              "skills through, then: set team <folder>")
        return 2
    folder = os.path.abspath(folder)
    notes = _notes_root()
    if notes:
        real = os.path.realpath(folder)
        if real == notes or real.startswith(notes + os.sep) or notes.startswith(real.rstrip(os.sep) + os.sep):
            print("REFUSED: %s is, holds, or sits inside your notes root (%s). The brain is never shared — pick a "
                  "team folder OUTSIDE the notes root (for example a new 'Team skills' folder)." % (folder, notes))
            return 2
    if not os.path.isdir(folder):
        if a.create and os.path.isdir(os.path.dirname(folder)):
            os.mkdir(folder)
            print("made the folder %s" % folder)
        else:
            print("REFUSED: %s is not a folder. Pick the team's Drive folder (run: discover), or add --create "
                  "to make it (its parent must already exist)." % folder)
            return 2
    with open(os.path.join(_cfg_dir(), "team-skills"), "w", encoding="utf-8") as f:
        f.write(folder + "\n")
    try:
        if not os.path.exists(os.path.join(folder, TEAM_MARKER)):
            with open(os.path.join(folder, TEAM_MARKER), "w", encoding="utf-8") as f:
                f.write("Lifehack team skills folder: shared skills live in skills/<name>/\n")
    except OSError:
        pass
    print("saved: team-sharing=team, team-skills=%s" % folder)
    print("To share Drive access itself, do it in the Drive website: give teammates 'Viewer' if "
          "they only use skills, 'Editor' if they also add skills. This tool never changes Drive sharing.")
    return 0


def _team_root_or_die():
    source, path = team_skills_root.resolve_team_skills_root()
    if source != "pointer":
        if source == "pointer-missing":
            print("REFUSED: the team folder pointer names a folder that is not there (%s). "
                  "Fix the line in %s." % (path, team_skills_root.pointer_path()))
        else:
            print("REFUSED: no team folder is set yet. Find the Drive folder: python3 %s discover   then: "
                  "set team <folder> [--create]   (if the person has not said whether they share with a team, ask: %s)"
                  % (os.path.abspath(__file__), QUESTION))
        return None
    if team_skills_root.sharing_mode() != "team":
        print("REFUSED: team-sharing is not 'team' (solo or unset). Nothing shares.")
        return None
    return os.path.realpath(path)


def cmd_status(_a):
    mode = team_skills_root.sharing_mode()
    print("team-sharing: %s" % (mode or "unset"))
    source, path = team_skills_root.resolve_team_skills_root()
    print("team folder: %s" % (path if source == "pointer" else "(%s)" % (source or "unset")))
    rows = read_ledger()
    if not rows:
        print("shared skills: none")
        return 0
    print("shared skills:")
    for r in rows:
        link = os.path.join(skills_home(), r["name"])
        state = ("link" if os.path.islink(link) else "copy" if os.path.isdir(link)
                 else "MISSING (run verify)")
        print("  %s: %s, mode=%s" % (r["name"], state, r.get("mode", "?")))
    return 0


def _share_conflict(name, team):
    """None when the Drive copy is absent or identical (safe to copy); a message when it differs."""
    dst = os.path.join(team, "skills", name)
    if not os.path.isdir(dst):
        return None
    return dst


def cmd_share(a):
    team = _team_root_or_die()
    if team is None:
        return 2
    src = os.path.join(skills_home(), a.name)
    if not os.path.isdir(src) or os.path.islink(src):
        print("REFUSED: %s is not a real skill folder of yours (a symlink or missing). Nothing to share." % src)
        return 2
    ok, problems, scripts = vet_skill(src)
    if not ok:
        print("REFUSED: %s did not pass the vet:" % a.name)
        for p in problems:
            print("  - " + p)
        return 2
    dst = _share_conflict(a.name, team)
    if dst is not None:
        ours, theirs = tree_sha256(src), tree_sha256(dst)
        if ours == theirs:
            if a.no_link:   # the person declined the link: running this again must not take that back
                print("the team copy of '%s' is already identical. Nothing changed: Drive copy %s; your local folder %s stays a separate copy." % (a.name, dst, src))
                return 0
            if not a.yes:   # a dry run never moves anything
                print("DRY-RUN (nothing moved). The team copy of '%s' is already identical. Would: move your local folder to the backup %s "
                      "and put a link at %s pointing to the Drive copy. Run again with --yes after the person says yes." % (a.name, backup_root(), src))
                return 0
            print("the team copy of '%s' is already identical — relinking only" % a.name)
            return _finish_share(a.name, src, dst, ours, scripts, a)
        print("CONFLICT: the team folder already has '%s', and it is DIFFERENT. Nothing was changed." % a.name)
        print("  local:  %s (modified %s)" % (src, datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(src, "SKILL.md"))).strftime("%Y-%m-%d %H:%M")))
        print("  team:   %s (modified %s)" % (dst, datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(dst, "SKILL.md"))).strftime("%Y-%m-%d %H:%M")))
        print("Ask the person, then: (a) keep the team copy and just link to it: remove yours or "
              "rename it, then run `use`;  (b) replace the team copy: run "
              "`unshare --retire`-style move by hand is NOT needed — say 'replace' and this tool "
              "moves the team copy to _versions/ first;  (c) cancel. Never overwrite silently.")
        if a.yes and a.replace:
            versions = os.path.join(team, "_versions")
            os.makedirs(versions, exist_ok=True)
            moved = os.path.join(versions, "%s-%s" % (a.name, _now()))
            shutil.move(dst, moved)
            print("moved the old team copy to %s" % moved)
            dst = None
        else:
            return 3
    plan = os.path.join(team, "skills", a.name)
    if not a.yes:
        if a.no_link:
            print("DRY-RUN (nothing moved). Would: copy %s -> %s (the shared copy). Your local folder stays as it is "
                  "(a separate copy, not live). Run again with --yes --no-link after the person says yes." % (src, plan))
        else:
            print("DRY-RUN (nothing moved). Would: copy %s -> %s (the shared copy), move your local folder to the backup "
                  "%s, and put a link at %s pointing to the Drive copy (recommended, best practice but not required: your "
                  "edits and the team's stay one copy; each computer makes its link once). The person can decline it "
                  "(--no-link keeps the local folder as a separate copy). Run again with --yes after the person says yes."
                  % (src, plan, backup_root(), src))
        return 0
    os.makedirs(os.path.join(team, "skills"), exist_ok=True)
    shutil.copytree(src, plan, symlinks=False)
    # verify the copy byte-for-byte
    if tree_sha256(plan) != tree_sha256(src):
        print("REFUSED: the Drive copy did not verify byte-for-byte; nothing was moved. "
              "Check the Drive folder is fully synced ('Available offline') and try again.")
        return 2
    with open(os.path.join(plan, MARKER_NAME), "w", encoding="utf-8") as f:
        f.write(json.dumps({"shared_by": os.environ.get("USER", "unknown"), "when": _now(),
                            "tree_sha256": tree_sha256(plan)}, indent=1) + "\n")
    if a.no_link:
        print("shared '%s' (no link): Drive copy %s; your local folder %s is unchanged and is now a SEPARATE "
              "copy (edits to one do not reach the other). Teammates run `use` to link the Drive copy. The link is recommended, "
              "not required: to make it on this computer, share again with --yes." % (a.name, plan, src))
        return 0
    return _finish_share(a.name, src, plan, tree_sha256(plan), scripts, a)


def _finish_share(name, src, drive_copy, sha, scripts, a):
    """Move the local real folder to the backup (never deleted), link in its place, ledger, ONE line."""
    mode = "symlink"
    if not os.path.islink(src) and os.path.isdir(src):
        os.makedirs(backup_root(), exist_ok=True)
        b = os.path.join(backup_root(), "%s-%s" % (name, _now()))
        shutil.move(src, b)
        mode, notes = link_skill(drive_copy, src)
        for n in notes:
            print(n)
    else:  # relink path: the local folder is already gone/linked
        if not os.path.lexists(src):
            mode, notes = link_skill(drive_copy, src)
            for n in notes:
                print(n)
    upsert_row({"name": name, "target": os.path.realpath(drive_copy), "sha256": sha,
                "mode": mode, "linked_at": _now()})
    script_note = (" (this skill has %d script%s: %s — allowed, scanned)"
                   % (len(scripts), "s" if len(scripts) != 1 else "", ", ".join(scripts))) if scripts else ""
    print("shared '%s'%s: Drive copy %s, link %s, backup %s" % (name, script_note, drive_copy, src, backup_root()))
    return 0


def cmd_use(_a):
    team = _team_root_or_die()
    if team is None:
        return 2
    skills_dir = os.path.join(team, "skills")
    if not os.path.isdir(skills_dir):
        print("the team folder has no skills/ yet — nothing to use.")
        return 0
    linked, skipped = 0, 0
    for name in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, name)
        if not os.path.isdir(d) or os.path.islink(d):
            continue
        if not os.path.isfile(os.path.join(d, "SKILL.md")) or not os.path.isfile(os.path.join(d, MARKER_NAME)):
            print("skipped %s: not a shared skill (no SKILL.md / no %s marker)" % (name, MARKER_NAME))
            skipped += 1
            continue
        ok, problems, scripts = vet_skill(d)
        if not ok:
            print("NOT linked %s — it did not pass the vet:" % name)
            for p in problems:
                print("  - " + p)
            skipped += 1
            continue
        link = os.path.join(skills_home(), name)
        if os.path.lexists(link) and not os.path.islink(link):
            print("skipped %s: you already have your own '%s'; yours was left alone (rename yours "
                  "and run use again if you want the team's too)." % (name, name))
            skipped += 1
            continue
        if os.path.islink(link):
            os.unlink(link)  # refresh an existing tool-made link
        mode, notes = link_skill(d, link)
        for n in notes:
            print(n)
        upsert_row({"name": name, "target": os.path.realpath(d), "sha256": tree_sha256(d),
                    "mode": mode, "linked_at": _now()})
        print("linked %s (%s) — this skill updates itself from the team folder%s"
              % (name, mode, "; it has %d script%s (allowed, scanned)" % (len(scripts), "s" if len(scripts) != 1 else "") if scripts else ""))
        linked += 1
    print("done: %d linked, %d skipped." % (linked, skipped))
    return 0


def _check_row(row, rehash):
    """One ledger row through the verify/update engine. -> a report line, or None when healthy.
    Drops the link (never touches the Drive copy) on a dangling link or a failed re-vet."""
    name, link = row["name"], os.path.join(skills_home(), row["name"])
    if not os.path.islink(link) and not os.path.isdir(link):
        os.unlink(link) if os.path.lexists(link) else None
        drop_row(name)
        return "shared skill '%s' is gone (link missing) — removed from the shared list" % name
    if os.path.islink(link) and not os.path.isdir(os.path.realpath(link)):
        os.unlink(link)
        drop_row(name)
        return "shared skill '%s' is broken (its team folder is gone or unsynced) — link removed" % name
    if not rehash:
        return None
    if not os.path.isdir(row["target"]):   # copy mode, team copy unreachable: keep the local copy, say so
        return "shared skill '%s': the team copy %s is not reachable (unsynced?) — your local copy was left as it is" % (name, row["target"])
    current = tree_sha256(row["target"])
    if current == row.get("sha256"):
        return None
    ok, problems, _scripts = vet_skill(row["target"])
    if not ok:
        if os.path.islink(link):
            os.unlink(link)
        else:
            os.makedirs(backup_root(), exist_ok=True)
            shutil.move(link, os.path.join(backup_root(), "%s-%s" % (name, _now())))
        drop_row(name)
        return ("shared skill '%s' CHANGED and failed the re-scan — link removed, Drive copy "
                "untouched. Why: %s" % (name, "; ".join(problems[:3])))
    if not os.path.islink(link):   # copy mode (Windows fallback): a copy is not live, so re-copy the vetted version
        os.makedirs(backup_root(), exist_ok=True)
        shutil.move(link, os.path.join(backup_root(), "%s-%s" % (name, _now())))
        shutil.copytree(row["target"], link, symlinks=False)
    upsert_row(dict(row, sha256=current))
    return "teammate updated '%s' (change passed the scan; pinned the new version)" % name


def cmd_update(_a):
    team = _team_root_or_die()
    if team is None:
        return 2
    reports = [r for r in (_check_row(row, rehash=True) for row in read_ledger()) if r]
    for r in reports:
        print(r)
    if not reports:
        print("all shared skills unchanged.")
    return 0


def cmd_verify(_a):
    reports = [r for r in (_check_row(row, rehash=False) for row in read_ledger()) if r]
    for r in reports:
        print(r)
    return 0


def cmd_session_check(_a):
    """The SessionStart half: silent when the switch is OFF (the default) or everything is healthy;
    one line per problem otherwise. Reads the switch through lib/roundb.py like every other part."""
    try:
        sys.path.insert(0, os.path.join(SHARED, "..", "system", "hooks", "lib"))
        from roundb import roundb_on
        on = roundb_on("team_skill_verify")
    except Exception:
        on = False
    finally:
        p = os.path.join(SHARED, "..", "system", "hooks", "lib")
        if p in sys.path:
            sys.path.remove(p)
    if not on:
        return 0
    for row in read_ledger():
        try:   # fail-soft PER ROW: one bad row never hides the others, and never fails a session start
            r = _check_row(row, rehash=True)
        except Exception as e:
            r = "could not check '%s' (%s: %s)" % (row.get("name", "?"), type(e).__name__, e)
        if r:
            print("shared skill problem: " + r)
    return 0


def cmd_remove(a):
    rows = read_ledger()
    if not a.all and not a.name:
        print("REFUSED: name a shared skill, or pass --all.")
        return 2
    listed = [r["name"] for r in rows]
    names = listed if a.all else [a.name]
    if not a.all and a.name not in listed:
        print("REFUSED: '%s' is not a tool-made link (only links in %s are ever removed)." % (a.name, ledger_path()))
        return 2
    for n in names:
        link = os.path.join(skills_home(), n)
        if os.path.islink(link):
            os.unlink(link)
            drop_row(n)
            print("removed the link to shared skill '%s' (the team copy is untouched)." % n)
        else:
            print("'%s' is not a link (a real folder or copy is never removed). Skipped." % n)
    return 0


def cmd_unshare(a):
    rows = {r["name"]: r for r in read_ledger()}
    if a.name not in rows:
        print("REFUSED: '%s' is not a tool-made shared link. Nothing done." % a.name)
        return 2
    link = os.path.join(skills_home(), a.name)
    target = rows[a.name]["target"]
    if not os.path.isdir(target):
        print("REFUSED: the team copy at %s is gone or unsynced; the link was left in place." % target)
        return 2
    if os.path.islink(link):
        os.unlink(link)
    elif os.path.isdir(link):  # copy mode
        shutil.move(link, os.path.join(backup_root(), "%s-%s" % (a.name, _now())))
    # hash-verified local copy in the link's place
    shutil.copytree(target, link, symlinks=False)
    if tree_sha256(link) != tree_sha256(target):
        print("WARNING: the local copy of '%s' did not verify byte-for-byte — check the sync." % a.name)
    drop_row(a.name)
    if a.retire:
        retired = os.path.join(os.path.dirname(target), "..", "_retired")
        retired = os.path.realpath(os.path.join(target, "..", "..", "_retired"))
        os.makedirs(retired, exist_ok=True)
        shutil.move(target, os.path.join(retired, "%s-%s" % (a.name, _now())))
        print("unshared '%s': a real local copy now sits at %s; the team copy was RETIRED to %s." % (a.name, link, retired))
    else:
        print("unshared '%s': a real local copy now sits at %s; the team copy at %s is untouched." % (a.name, link, target))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="share skills with a team through a Google Drive folder (file-system only)")
    ap.add_argument("--session-check", action="store_true", help="the SessionStart check: silent unless a shared skill is broken/missing/changed-bad")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("route", help="print the one route for sharing a skill, in commands that work as printed"); s.set_defaults(fn=cmd_route)
    s = sub.add_parser("question", help="print the one setup question, verbatim"); s.set_defaults(fn=cmd_question)
    s = sub.add_parser("discover", help="list this computer's Google Drive folders and likely team folders (read-only)")
    s.set_defaults(fn=cmd_discover)
    s = sub.add_parser("set", help="store the answer (team <folder> [--create] | solo)")
    s.add_argument("mode"); s.add_argument("folder", nargs="?"); s.add_argument("--create", action="store_true")
    s.set_defaults(fn=cmd_set)
    s = sub.add_parser("status", help="what is shared right now"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("share", help="share one of your skills (dry-run by default)")
    s.add_argument("name"); s.add_argument("--yes", action="store_true"); s.add_argument("--replace", action="store_true")
    s.add_argument("--no-link", action="store_true", help="copy to Drive, leave the local folder as it is (the link is recommended, not required; the person can decline it)")
    s.set_defaults(fn=cmd_share)
    s = sub.add_parser("unshare", help="replace the link with a real local copy")
    s.add_argument("name"); s.add_argument("--retire", action="store_true"); s.set_defaults(fn=cmd_unshare)
    s = sub.add_parser("use", help="link every good skill the team shares"); s.set_defaults(fn=cmd_use)
    s = sub.add_parser("update", help="re-hash every linked skill; re-vet changes"); s.set_defaults(fn=cmd_update)
    s = sub.add_parser("verify", help="report broken/missing links; drop dangling ones"); s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("remove", help="remove tool-made links only (never a real folder, never the Drive copy)")
    s.add_argument("name", nargs="?"); s.add_argument("--all", action="store_true"); s.set_defaults(fn=cmd_remove)
    a = ap.parse_args(argv)
    if a.session_check:
        return cmd_session_check(a)
    if not getattr(a, "fn", None):
        ap.print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
