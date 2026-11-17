#!/usr/bin/env python3
"""worker.py — the untrusted-content half of the hand-off reader. ALWAYS launched as `python -I worker.py ...`
by handoff.py, with cwd = the fresh working dir, and this file living OUTSIDE that dir.

Modes (JSON on stdout, nothing else):
  parse   <eml_path> <out_dir>          parse MIME (stdlib email, policy.default); write each attachment's bytes to
                                        <out_dir>/att/<n>.<kind-ext> under a SAFE name; report headers, body, attachments.
  extract <kind> <path>                 pull text out of ONE attachment through the matching safe_* reader.

Nothing here judges safety — the Sentinel gate in handoff.py does that. This file only parses, caps, and fails closed.
"""
import email
import io
import json
import os
import re
import sys
import zipfile

# Launched with -I (no cwd/script-dir/PYTHONPATH/user-site on sys.path), so code planted next to the
# untrusted .eml can never be imported. The harness document readers (pdfplumber, python-docx, openpyxl)
# live in the user's own site-packages, which -I also drops; add back exactly that one trusted folder,
# at the END of sys.path so stdlib always wins. Nothing else is re-enabled.
try:
    import site as _site
    _usp = _site.getusersitepackages()
    if _usp and os.path.isdir(_usp) and _usp not in sys.path:
        sys.path.append(_usp)
except Exception as _e:  # allow-silence: readers then fail closed with "not installed", which is reported
    print(f"user site not added: {_e}", file=sys.stderr)
from email import policy
from html.parser import HTMLParser

LIFEHACK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # the plugin this code runs from
SAFE_TOOLS = os.path.join(LIFEHACK, "system", "tools")

MAX_EML_BYTES = 100_000_000
MAX_ATT_BYTES = 10_000_000
MAX_ATTACHMENTS = 20
MAX_PAGES = 50
MAX_TEXT_CHARS = 100_000
MAX_ZIP_ENTRIES = 2000
MAX_ZIP_UNCOMPRESSED = 100_000_000

ARCHIVE_EXT = {"zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "xz", "z", "cab", "iso", "dmg", "jar"}
IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "bmp", "tif", "tiff", "webp", "heic", "heif", "svg", "ico"}
TEXT_EXT = {"txt", "md", "log", "ics", "vcf", "json", "xml", "rtf_no"}
IMAGE_MAGIC = (b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"BM", b"II*\x00", b"MM\x00*")


def out(obj):
    sys.stdout.write(json.dumps(obj))
    sys.stdout.flush()


def safe_label(s, n=80):
    """Display-safe version of an untrusted string: printable ASCII-ish only."""
    s = re.sub(r"[^A-Za-z0-9._ ()\-]", "_", str(s or ""))
    return s[:n]


class _VisibleText(HTMLParser):
    """HTML -> visible text. Drops script/style/head and elements hidden by inline style."""
    HIDDEN = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0|opacity\s*:\s*0"
                        r"|color\s*:\s*(#fff(fff)?\b|white\b|rgb\(\s*255\s*,\s*255\s*,\s*255)", re.I)
    VOID = {"br", "hr", "img", "meta", "link", "input", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.stack, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            if tag in ("br", "hr") and not self.skip:
                self.parts.append("\n")
            return
        style = dict(attrs).get("style") or ""
        hidden = tag in ("script", "style", "head", "title") or bool(self.HIDDEN.search(style)) \
            or "hidden" in dict(attrs)
        self.stack.append(hidden)
        if hidden:
            self.skip += 1
        elif tag in ("p", "div", "tr", "li", "h1", "h2", "h3", "h4", "table"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.VOID or not self.stack:
            return
        if self.stack.pop():
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html):
    p = _VisibleText()
    try:
        p.feed(html)
        p.close()
    except Exception as e:  # noqa: BLE001  -- malformed markup: keep the text gathered so far, and say so
        sys.stderr.write("worker: html_to_text stopped early (%s: %s)\n" % (type(e).__name__, e))
    return re.sub(r"\n{3,}", "\n\n", "".join(p.parts)).strip()


def classify(name, ctype, head, data):
    """Return (kind, ext, None) or (None, None, reason). Content (magic bytes) outranks the claimed type."""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    ctype = (ctype or "").lower()
    if head.startswith(b"%PDF"):
        return "pdf", "pdf", None
    if ext == "pdf" or ctype == "application/pdf":
        return None, None, "claims to be a PDF but is not (no %PDF header)"
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
            names = zf.namelist()
            infos = zf.infolist()
        except Exception:  # noqa: BLE001
            return None, None, "malformed zip container"
        if ext in ("docx", "xlsx") or "officedocument" in ctype:
            if len(infos) > MAX_ZIP_ENTRIES or sum(i.file_size for i in infos) > MAX_ZIP_UNCOMPRESSED:
                return None, None, "office file expands too far (zip-bomb guard)"
            if "word/document.xml" in names:
                return "docx", "docx", None
            if "xl/workbook.xml" in names:
                return "xlsx", "xlsx", None
        return None, None, "zip/archive refused (v1 does not open archives)"
    if ext in ARCHIVE_EXT or head.startswith((b"Rar!", b"7z\xbc\xaf", b"\x1f\x8b", b"BZh", b"\xfd7zXZ")) \
            or ctype in ("application/zip", "application/x-zip-compressed", "application/gzip",
                         "application/x-tar", "application/x-7z-compressed", "application/x-rar-compressed"):
        return None, None, "archive refused (v1 does not open archives)"
    if ctype.startswith("image/") or ext in IMAGE_EXT or head.startswith(IMAGE_MAGIC) \
            or (head[:4] == b"RIFF" and head[8:12] == b"WEBP"):
        return None, None, "image: OCR not supported in v1"
    if ctype == "message/rfc822" or ext == "eml":
        return None, None, "nested email refused (v1)"
    if ext == "csv" or ctype == "text/csv":
        return "csv", "csv", None
    if ctype in ("text/plain", "text/calendar", "text/markdown") or ext in TEXT_EXT:
        if b"\x00" in data[:4096]:
            return None, None, "claims to be text but contains binary data"
        return "text", "txt", None
    if ctype == "text/html" or ext in ("html", "htm"):
        return None, None, "html attachment refused (v1)"
    return None, None, f"unsupported file type ({safe_label(ctype, 60) or 'unknown'}{'/' + ext if ext else ''})"


def parse(eml_path, out_dir):
    size = os.path.getsize(eml_path)
    if size > MAX_EML_BYTES:
        return {"ok": False, "reason": f".eml too large ({size} bytes)"}
    with open(eml_path, "rb") as fh:
        msg = email.message_from_binary_file(fh, policy=policy.default)

    def hdr(name):
        try:
            return str(msg.get(name, "") or "")
        except Exception:  # noqa: BLE001
            return ""

    plain, html, atts = [], [], []
    for part in msg.walk():
        if part.is_multipart():
            continue
        try:
            fname = part.get_filename() or ""
        except Exception:  # noqa: BLE001
            fname = ""
        disp = part.get_content_disposition()
        ctype = part.get_content_type()
        if not fname and disp != "attachment" and ctype in ("text/plain", "text/html"):
            try:
                txt = part.get_content()
            except Exception:  # noqa: BLE001
                txt = ""
            (plain if ctype == "text/plain" else html).append(str(txt))
            continue
        atts.append((fname, ctype, part))

    body = "\n\n".join(plain).strip() or html_to_text("\n".join(html))
    att_dir = os.path.join(out_dir, "att")
    os.makedirs(att_dir, exist_ok=True)
    report = []
    for i, (fname, ctype, part) in enumerate(atts, 1):
        entry = {"index": i, "raw_name": fname or f"(unnamed part {i})", "content_type": ctype}
        if i > MAX_ATTACHMENTS:
            entry.update(status="fail", reason=f"over the {MAX_ATTACHMENTS}-attachment cap; not opened")
            report.append(entry)
            continue
        try:
            data = part.get_payload(decode=True) or b""
        except Exception:  # noqa: BLE001
            data = b""
        entry["size"] = len(data)
        if len(data) > MAX_ATT_BYTES:
            entry.update(status="fail", reason=f"over the {MAX_ATT_BYTES // 1_000_000} MB cap; not opened")
        elif not data:
            entry.update(status="fail", reason="empty attachment")
        else:
            kind, ext, why = classify(fname, ctype, data[:16], data)
            if why:
                entry.update(status="fail", reason=why)
            else:
                path = os.path.join(att_dir, f"{i}.{ext}")
                with open(path, "wb") as fh:
                    fh.write(data)
                entry.update(status="pending", kind=kind, path=path)
        report.append(entry)
    return {"ok": True, "headers": {"from": hdr("From"), "to": hdr("To"), "subject": hdr("Subject"),
                                    "date": hdr("Date")},
            "body": body, "attachments": report}


def extract(kind, path):
    sys.path.insert(0, SAFE_TOOLS)
    try:
        if kind == "text":
            with open(path, "rb") as fh:
                text = fh.read().decode("utf-8", errors="replace")
            pages = None
        elif kind == "pdf":
            try:
                import pdfplumber  # noqa: F401
            except ImportError:
                return {"ok": False, "reason": "pdf reader not installed"}
            try:
                with pdfplumber.open(path) as pdf:
                    pages = len(pdf.pages)
            except Exception as e:  # noqa: BLE001
                m = str(e).lower()
                return {"ok": False, "reason": "encrypted PDF" if ("password" in m or "encrypt" in m)
                        else "malformed PDF"}
            if pages > MAX_PAGES:
                return {"ok": False, "reason": f"over the {MAX_PAGES}-page cap ({pages} pages); not read"}
            import safe_pdf
            text = safe_pdf.extract_and_sanitize(path)
        elif kind == "docx":
            try:
                import docx  # noqa: F401
            except ImportError:
                return {"ok": False, "reason": "docx reader not installed"}
            import safe_docx
            text, pages = safe_docx.extract_and_sanitize(path), None
        elif kind == "xlsx":
            try:
                import openpyxl  # noqa: F401
            except ImportError:
                return {"ok": False, "reason": "xlsx reader not installed"}
            import safe_xlsx
            text, pages = safe_xlsx.extract_and_sanitize(path), None
        elif kind == "csv":
            import safe_csv
            text, pages = safe_csv.read_and_sanitize(path), None
        else:
            return {"ok": False, "reason": "no reader for this type"}
    except SystemExit:
        return {"ok": False, "reason": f"{kind} reader not installed"}
    except Exception as e:  # noqa: BLE001
        m = str(e).lower()
        return {"ok": False, "reason": "encrypted file" if ("password" in m or "encrypt" in m)
                else f"could not be read ({type(e).__name__})"}
    text = (text or "").strip()
    if not text:
        return {"ok": False, "reason": "no extractable text (scanned or empty)"}
    truncated = len(text) > MAX_TEXT_CHARS
    return {"ok": True, "text": text[:MAX_TEXT_CHARS], "truncated": truncated, "pages": pages}


def main(argv):
    try:
        if argv[1] == "parse":
            out(parse(argv[2], argv[3]))
        elif argv[1] == "extract":
            out(extract(argv[2], argv[3]))
        else:
            out({"ok": False, "reason": "bad mode"})
    except Exception as e:  # noqa: BLE001
        out({"ok": False, "reason": f"worker error ({type(e).__name__})"})


if __name__ == "__main__":
    main(sys.argv)
