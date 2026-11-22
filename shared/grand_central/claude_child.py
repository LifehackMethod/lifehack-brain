"""One shared helper for the argv the front room's `claude -p` children get, so they run the same hooks his windows do
(coordinator 38, route A). His interactive windows launch `claude --setting-sources ... --plugin-dir <harness root> --settings ...`;
without these a child loads an old user-level plugin whose gate blinds the lenses.

  --plugin-dir   the FIRST LINE of ~/.config/lifehack/code-root (override for tests: $GC_CODE_ROOT_FILE). A V2 session-start hook
                 rewrites that file to the child's plugin root, so the value MUST equal what the file already holds (a no-op write).
                 This module only READS the file, never writes it. A value inside a plugin cache (/.claude/plugins/cache/) is refused.
  --setting-sources / --settings   from $GC_CHILD_SETTING_SOURCES / $GC_CHILD_SETTINGS in the engine's OWN environment (his job
                 wrapper sets them). No path or value of his is written in this code. The variables become argv only; they are
                 never passed into a child's environment (child_env strips them).
If anything is missing the argv is [] plus a warning "window flags missing: <which>": behaviour is exactly as before."""
import os

ENV_VARS = ("GC_CHILD_SETTING_SOURCES", "GC_CHILD_SETTINGS", "GC_CODE_ROOT_FILE")
CACHE_MARK = "/.claude/plugins/cache/"


def pointer_file():
    return os.environ.get("GC_CODE_ROOT_FILE") or os.path.expanduser("~/.config/lifehack/code-root")


def window_flags():
    """-> (extra argv list, warning string or None)"""
    missing = []
    plugin = None
    try:
        with open(pointer_file(), encoding="utf-8") as f:
            plugin = (f.readline() or "").strip()
    except OSError:
        plugin = None
    if not plugin:
        missing.append("code-root pointer")
    elif CACHE_MARK in plugin.replace("\\", "/") + "/":
        missing.append("code-root pointer (a plugin-cache path is refused)")
        plugin = None
    ss, st = os.environ.get("GC_CHILD_SETTING_SOURCES"), os.environ.get("GC_CHILD_SETTINGS")
    if not ss:
        missing.append("GC_CHILD_SETTING_SOURCES")
    if not st:
        missing.append("GC_CHILD_SETTINGS")
    if missing:
        return [], "window flags missing: " + ", ".join(missing)
    return ["--plugin-dir", plugin, "--setting-sources", ss, "--settings", st], None


def child_env(env):
    """a copy of `env` without the variables that only become argv"""
    return {k: v for k, v in env.items() if k not in ENV_VARS}
