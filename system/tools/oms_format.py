#!/usr/bin/env python3
"""Format /overmyshoulder relay JSON into sanitizer-ready text.

The relay's /read-active and /list-tabs return JSON; this turns that into the
plain text block that over_my_shoulder.sh then pipes through safe_input.py.

Usage:
    oms_format.py read   < json   # a single tab's text  (from /read-active)
    oms_format.py tabs   < json   # the open-tab list     (from /list-tabs)

URL query strings and fragments are REDACTED here — that is where session
tokens hide, and this output goes into the model's context.

Exit 0 = formatted text on stdout. Exit 2 = error (message on stderr).
"""
import sys
import json
from urllib.parse import urlparse


def redact(u):
    """Drop query/fragment from a URL; hidden/empty URLs become a placeholder."""
    if not u:
        return "(hidden)"
    try:
        x = urlparse(u)
        base = "{}://{}{}".format(x.scheme, x.netloc, x.path)
        return base + (" ?[redacted]" if (x.query or x.fragment) else "")
    except Exception:
        return u.split("?")[0]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "read"
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        sys.stderr.write("oms_format: could not parse relay response: {}\n".format(e))
        return 2

    if isinstance(data, dict) and data.get("error"):
        sys.stderr.write(str(data["error"]) + "\n")
        return 2

    if mode == "tabs":
        print("OPEN TABS:")
        for t in data.get("tabs", []):
            mark = " *" if t.get("active") else "  "
            note = "" if t.get("readable", True) else "  (not readable)"
            print("  [{}]{} {} — {}{}".format(
                t.get("index"), mark, t.get("title") or "", redact(t.get("url")), note))
        return 0

    # read mode
    text = (data.get("text") or "")[:12000]
    print("TAB [{}]: {} — {}".format(
        data.get("index"), data.get("title") or "", redact(data.get("url"))))
    print("----")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
