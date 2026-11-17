"""diary_names.py: Phase 4 (ruling 4.1). A desk's diary is named by ONE pattern, '<Desk>-Diary'.
Shared code holds only the pattern; the desk list (and the main diary's own name) is read from the person's setup/desks.json
(through gc_settings).
The folder on disk is always <notes>/desks/<desk_slug>/diary (the slug is the desk's id; the NAME is a label)."""
import json
import os

import gc_settings

DEFAULT_PATTERN = "{display}-Diary"


def load(path=None):
    if path is None:
        return gc_settings.desks()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def diary_name(desk_id, cfg=None):
    """-> the main diary's own name for the main diary's desk, else the pattern filled with the desk's display name
    ('desk-b' with display 'Desk-B' -> 'Desk-B-Diary'). A desk missing from setup raises KeyError: never guessed."""
    cfg = cfg or load()
    main = cfg.get("main_diary") or {}
    if desk_id == main.get("desk"):
        return main["name"]
    display = cfg["desks"][desk_id]["display"]
    return cfg.get("diary_pattern", DEFAULT_PATTERN).format(display=display)


def diary_folder(notes, desk_id):
    return os.path.join(notes, "desks", desk_id, "diary")
