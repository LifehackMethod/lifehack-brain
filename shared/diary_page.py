#!/usr/bin/env python3
# not-wired-yet: its first caller (planning-diary-capture.py) lands in the very next commit; Grand Central adopts it in its own follow-up
"""diary_page.py -- the ONE desk-neutral diary append: whoever produces an entry on a day's page APPENDS its own (Spec 3.10).

append_entry(path, body, mentions, staged, confidence="low", heading=None, after_write=None, read=None) -> "written" | "appended" | "exists"
  No page yet: created exclusively (a front matter block of mentions, staged, confidence, then the body) -> "written".
  A page already there: the body is appended at its END; mentions and staged are merged (union) into the TOP front matter;
  a confidence of high or medium stays; every other key and every existing line is left byte for byte; a page with no
  front matter gains a block on top and keeps every line -> "appended". `heading` given and already a line of the page ->
  "exists", nothing written (a re-run adds nothing). Atomic (temp file + os.replace), mode 0600. after_write(path) is
  called once after a write (a caller passes its own local-copy step); this module imports nothing of any desk.
  read (optional callable path -> text) is used ONLY to read an existing page (a scheduled job passes its Drive-safe
  reader); default None = the plain read. A read that raises -> DiaryPageError, nothing written.
  An unreadable page raises DiaryPageError (loud); a normal page never raises.
Lifted as-is from Grand Central's morning.py (_merge_front_matter, _replace_atomic_drive, write_diary_entry): no behaviour change.
Test: python3 shared/test_diary_page.py"""
import json
import os
import re
import tempfile

_FM_TOP = re.compile(r"\A---\n(.*?)\n---\n", re.S)


class DiaryPageError(Exception):
    """The page exists but cannot be read (not UTF-8, not a file, no permission): nothing is written."""


def front_matter(mentions, staged=None, confidence=None):
    """The block a new page gets: mentions line, a staged line when given, a confidence line when given."""
    st = "staged: %s\n" % json.dumps(list(staged), ensure_ascii=True) if staged else ""
    cf = "confidence: %s\n" % confidence if confidence else ""
    return "---\nmentions: %s\n%s%s---\n" % (json.dumps(list(mentions), ensure_ascii=True), st, cf)


def _json_list(s):
    try:
        v = json.loads(s)
        return v if isinstance(v, list) and all(isinstance(x, str) for x in v) else None
    except ValueError:
        return None


def _merge_front_matter(text, mentions, staged, confidence="low"):
    """Merge into the page's TOP front matter: mentions = union, staged = union, confidence kept when it already says
    high or medium (else low); every other line of the block is left exactly as it is. A page with no top block gets one
    in front (nothing existing is changed). -> the page text with the merged block."""
    m = _FM_TOP.match(text)
    if not m:
        return front_matter(mentions, staged, confidence) + text
    out, seen = [], set()
    for ln in m.group(1).split("\n"):
        if ln.startswith("mentions: ") and _json_list(ln[10:]) is not None:
            old = _json_list(ln[10:])
            ln = "mentions: %s" % json.dumps(old + [k for k in mentions if k not in old], ensure_ascii=True)
            seen.add("mentions")
        elif ln.startswith("staged: ") and _json_list(ln[8:]) is not None:
            old = _json_list(ln[8:])
            ln = "staged: %s" % json.dumps(old + [k for k in staged if k not in old], ensure_ascii=True)
            seen.add("staged")
        elif ln.startswith("confidence:"):
            seen.add("confidence")
            if ln.split(":", 1)[1].strip().lower() not in ("high", "medium", "low"):
                ln = "confidence: %s" % confidence
        out.append(ln)
    if "mentions" not in seen:
        out.append("mentions: %s" % json.dumps(list(mentions), ensure_ascii=True))
    if "staged" not in seen and staged:
        out.append("staged: %s" % json.dumps(list(staged), ensure_ascii=True))
    if "confidence" not in seen:
        out.append("confidence: %s" % confidence)
    return "---\n" + "\n".join(out) + "\n---\n" + text[m.end():]


def _replace_atomic(path, text):
    """temp file in the same folder, then rename."""
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".diary-", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _excl_write(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _read(path):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as e:
        raise DiaryPageError("cannot read the diary page %s (%s); nothing was written" % (path, e))


def append_entry(path, body, mentions, staged, confidence="low", heading=None, after_write=None, read=None):
    """-> "written" (new page) | "appended" (added to the page there) | "exists" (heading already on the page; nothing written)."""
    if os.path.lexists(path):
        if read is None:
            existing = _read(path)
        else:
            try:
                existing = read(path)
            except DiaryPageError:
                raise
            except Exception as e:
                raise DiaryPageError("cannot read the diary page %s (%s); nothing was written" % (path, e))
        if heading is not None and any(ln.strip() == heading for ln in existing.splitlines()):
            return "exists"
        merged = _merge_front_matter(existing, list(mentions), list(staged), confidence)
        if not merged.endswith("\n"):
            merged += "\n"
        _replace_atomic(path, merged + "\n" + body)
        status = "appended"
    else:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        try:
            _excl_write(path, front_matter(mentions, staged, confidence).rstrip("\n") + "\n" + body)
        except FileExistsError:
            return append_entry(path, body, mentions, staged, confidence, heading, after_write, read)
        status = "written"
    if after_write is not None:
        after_write(path)
    return status
