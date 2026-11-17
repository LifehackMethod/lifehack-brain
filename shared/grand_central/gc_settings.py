"""shared/grand_central/gc_settings.py: the ONE settings loader of the Grand Central engine.

The engine code is generic: the same code for any subscriber. Every value that belongs to one person (desk names,
label names, people, paths, parts of life, the words used about the owner) lives in that person's setup folder and is
read through this module, never written into the engine or the mailroom code.

Where the setup folder is (setup_dir(), first match wins):
  (a) env GC_SETUP_DIR (the tests point it at the synthetic fixture folder tests/fixtures/setup);
  (b) <personal code root>/tools/grand-central/setup. The personal code root comes from the plugin's own
      shared/person_roots.py (personal_code_root()), imported as a sibling; there is no second copy of that rule here.
  Neither -> SettingsError (fail loudly).

The files read: desks.json, routing.json, labels.json, leans.json, keywords.json, expected.json, alarm-settings.json,
status_lights.json (each by the module that owns it, through setup_path()), and gc.json for the values that had no
home before. A missing setting FAILS LOUDLY (SettingsError, naming the file and the key): never a silent fallback to
one person's values.

The product data folder (data_root()): env GC_DATA_ROOT, else gc.json data_root if the person's setup names one (an
existing install keeps its current folder until it is moved), else ~/.local/share/<harness-name>/grand-central/, where the
harness name is read at run time from the plugin's own manifest (harness_name()).
Python 3.9 compatible."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.dirname(HERE)                       # the plugin's shared/ (person_roots.py lives there)
PERSONAL_SUBDIR = os.path.join("tools", "grand-central", "setup")


# The SHIPPED generic defaults: the names the plugin ships with, by the owner's ruling of 2026-11-16 (the planning desk is the
# shipped generic desk, its diary is named by the one pattern below). They are not personal values, and the personal-values
# lock (check_personal_values.py) does not flag a setup value that equals one of them. This is the ONE list.
_DESK = "planning"
_PATTERN = "{display}-Diary"
SHIPPED_DEFAULTS = {
    "desk": _DESK,
    "main_diary": _PATTERN.format(display=_DESK.capitalize()),
    "diary_pattern": _PATTERN,
}


class SettingsError(RuntimeError):
    """A setting the engine needs is missing or unreadable. Never guessed."""


# ---- where things are ------------------------------------------------------------------------------------------
def plugin_root():
    """The plugin folder. env LIFEHACK_CODE_ROOT (job-run.sh exports it for every scheduled job) when that folder really holds
    the plugin (.claude-plugin/plugin.json); else the folder this code runs from (shared/grand_central -> two levels up).
    The pinned copy (live/<sha>/grand_central) has no plugin around it, so there the env var is the only way to find it."""
    env = os.environ.get("LIFEHACK_CODE_ROOT")
    if env and os.path.isfile(os.path.join(env, ".claude-plugin", "plugin.json")):
        return env
    return os.path.dirname(SHARED)


def harness_name():
    """The running harness's own name, read at run time from the plugin manifest (.claude-plugin/plugin.json "name");
    the plugin folder's name if the manifest cannot be read. Never hard-coded."""
    try:
        with open(os.path.join(plugin_root(), ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            name = json.load(f).get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    except (OSError, ValueError):
        pass
    return os.path.basename(plugin_root())


def personal_code_root():
    """The person's own code folder, from the plugin's shared person_roots.py (the one resolver). "" when none is set.
    An import failure is NOT swallowed: it raises, so a broken install is loud."""
    if SHARED not in sys.path:
        sys.path.append(SHARED)
    import person_roots
    return person_roots.personal_code_root() or ""


def setup_dir():
    """The person's setup folder (see the module docstring for the order). Raises SettingsError when there is none."""
    env = os.environ.get("GC_SETUP_DIR")
    if env:
        if not os.path.isdir(env):
            raise SettingsError("GC_SETUP_DIR names %s, which is not a folder" % env)
        return env
    personal = personal_code_root()
    if personal:
        cand = os.path.join(personal, PERSONAL_SUBDIR)
        if os.path.isdir(cand):
            return cand
    raise SettingsError("no Grand Central setup folder: set GC_SETUP_DIR, or create <personal code folder>/%s"
                        % PERSONAL_SUBDIR)


def setup_path(name):
    """Full path of one setup file (it need not exist; the reader of that file decides what missing means)."""
    return os.path.join(setup_dir(), name)


def load(name):
    """One setup file as JSON. Missing or unreadable -> SettingsError."""
    p = setup_path(name)
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise SettingsError("setup file %s cannot be read: %s" % (p, e))


def _need(doc, key, where):
    if not isinstance(doc, dict) or key not in doc or doc[key] in (None, ""):
        raise SettingsError("setting %r is missing from %s" % (key, where))
    return doc[key]


def gc(key):
    """One value from gc.json (the values with no other home). Missing -> SettingsError."""
    return _need(load("gc.json"), key, setup_path("gc.json"))


# ---- the product data folder (not personal; no setup file needed) -------------------------------------------------
def data_root():
    """env GC_DATA_ROOT, else gc.json data_root (an install that keeps its current folder until it is moved; no setup
    folder at all or no such key is simply not that; an expected setup that cannot be read raises), else ~/.local/share/<harness-name>/grand-central/."""
    env = os.environ.get("GC_DATA_ROOT")
    if env:
        return os.path.expanduser(env)
    try:
        configured = load("gc.json").get("data_root")
    except SettingsError:
        # An owner setup is EXPECTED when GC_SETUP_DIR is set or a personal code folder exists: then a setup that does not
        # resolve must fail loudly, never fall back to a new empty generic folder. Only a confirmed absence of any owner
        # setup (no GC_SETUP_DIR, no personal code root) keeps the student default.
        if os.environ.get("GC_SETUP_DIR") or personal_code_root():
            raise
        configured = None
    if configured:
        return os.path.expanduser(str(configured))
    return os.path.join(os.path.expanduser("~"), ".local", "share", harness_name(), "grand-central")


def db_path():
    return os.path.join(data_root(), "rig.db")


def front_room_dir():
    """env AGE_FRONT_ROOM (kept exactly as before), else <data root>/front-room."""
    return os.environ.get("AGE_FRONT_ROOM") or os.path.join(data_root(), "front-room")


def state_dir():
    """env GC_STATE_ROOT (kept exactly as before), else <data root>/state."""
    return os.environ.get("GC_STATE_ROOT") or os.path.join(data_root(), "state")


# ---- typed getters -------------------------------------------------------------------------------------------------
def default_desk():
    """The desk a job works for when none is named (gc.json default_desk); its folder is <notes>/desks/<desk>."""
    try:
        return str(load("gc.json").get("default_desk") or SHIPPED_DEFAULTS["desk"])
    except SettingsError:
        return SHIPPED_DEFAULTS["desk"]


def state_subdir():
    """Where the engine's state sits inside the notes folder, relative: gc.json notes_state_subdir (an install that keeps
    its current folder), else state/<harness-name>/grand-central."""
    try:
        configured = load("gc.json").get("notes_state_subdir")
    except SettingsError:
        configured = None
    return str(configured) if configured else os.path.join("state", harness_name(), "grand-central")


def pulse_desk():
    """The name the engine's own status pulses carry as their desk: gc.json pulse_desk, else the harness name."""
    try:
        configured = load("gc.json").get("pulse_desk")
    except SettingsError:
        configured = None
    return str(configured) if configured else harness_name()


def desks():
    """setup/desks.json (the desk list, the diary pattern, the main diary)."""
    return load("desks.json")


def routing():
    """setup/routing.json (part of life -> desk, the main diary)."""
    return load("routing.json")


def main_diary():
    """The main diary's name (setup/routing.json main_diary)."""
    return str(_need(routing(), "main_diary", setup_path("routing.json")))


def desk_for_part(part):
    """The desk that owns a part of life (routing.json parts_to_desk, case-insensitive), or None."""
    for k, v in (routing().get("parts_to_desk") or {}).items():
        if part is not None and k.casefold() == str(part).strip().casefold():
            return v
    return None


def labels():
    """setup/labels.json."""
    return load("labels.json")


def owner_id():
    """The word stored as the owner's id in decided_by / --by (gc.json owner_id). Kept as the word already stored, so
    stored rows stay identical; no migration."""
    return str(gc("owner_id"))


def owner_name():
    """The name the engine's wording uses for the person (gc.json owner_name)."""
    return str(gc("owner_name"))


def mailroom_user():
    """The mailroom's OS account: env AGE_MAILROOM_USER (kept as before), else gc.json mailroom_user."""
    return os.environ.get("AGE_MAILROOM_USER") or str(gc("mailroom_user"))


def mailroom_install_dir():
    """The mailroom's root-owned install folder (gc.json mailroom_install_dir)."""
    return str(gc("mailroom_install_dir"))


def mailroom_account_stem():
    """The stem the mailroom account's LuLu rule keys carry (gc.json mailroom_account_stem), lowercase."""
    return str(gc("mailroom_account_stem")).lower()


def drop_dir():
    """The one-way drop folder: env GC_DROP if set and non-empty (kept as before), else gc.json drop_dir."""
    return os.environ.get("GC_DROP") or str(gc("drop_dir"))


def configured_notes_root():
    """The person's notes folder as the plugin's shared resolver names it (person_roots.notes_root(); ignores
    AGE_NOTES_ROOT: used for 'is this the real notes folder?'). SettingsError when none is resolved."""
    if SHARED not in sys.path:
        sys.path.append(SHARED)
    import person_roots
    root = person_roots.notes_root()
    if not root:
        raise SettingsError("no notes folder resolved by shared/person_roots.py (set the brain root)")
    return root


def notes_root():
    """The person's notes folder: env AGE_NOTES_ROOT (kept as before), else the shared resolver's notes folder."""
    return os.environ.get("AGE_NOTES_ROOT") or configured_notes_root()


def notes_subpaths():
    """Where things sit inside the notes folder (the generic layout, the same for every person)."""
    return {"desk": os.path.join("desks", "{desk}"), "life_map": os.path.join("desks", "{desk}", "life-map.md"),
            "records_context": os.path.join("desks", "{desk}", "records", "context"),
            "backups": os.path.join(state_subdir(), "backups")}


def life_map_path():
    """<notes>/desks/<default desk>/life-map.md (the person's goals, in their own words)."""
    return os.path.join(configured_notes_root(), notes_subpaths()["life_map"].format(desk=default_desk()))


def domains():
    """gc.json domains: {name: {"label_prefix"?, "plain", "project_words"}} in the person's order. A domain is a part
    of life a desk looks after; the names are the person's."""
    d = gc("domains")
    if not isinstance(d, dict) or not d:
        raise SettingsError("setting 'domains' in %s must be a non-empty object" % setup_path("gc.json"))
    return d


def domain_names():
    return tuple(domains().keys())


def label_domains():
    """((label prefix lower case, domain), ...) for the domains that have a label prefix."""
    return tuple((str(v["label_prefix"]).lower(), k) for k, v in domains().items() if v.get("label_prefix"))


def domain_plain_words():
    """((domain, plain words), ...) in the person's order."""
    return tuple((k, str(_need(v, "plain", "gc.json domains.%s" % k))) for k, v in domains().items())


def domain_project_words():
    """{domain lower case: (project words, ...)}."""
    return dict((k.lower(), tuple(v.get("project_words") or ())) for k, v in domains().items())


def research_domain_values():
    """The domain values of an AI research fact the screen shows: the domains plus gc.json extra_research_domains
    (optional)."""
    return domain_names() + tuple(load("gc.json").get("extra_research_domains") or ())


def negative_fact_words():
    """gc.json negative_fact_words: {"<X>": {"words": regex, "projects": [...]}} for "No <X>" life facts. Optional."""
    d = load("gc.json").get("negative_fact_words") or {}
    return dict((k, {"words": v["words"], "projects": tuple(v.get("projects") or ())}) for k, v in d.items())


def prompt_example(key):
    """One example sentence the synthesis prompt shows the model (gc.json prompt_examples.<key>)."""
    return str(_need(gc("prompt_examples"), key, "gc.json prompt_examples"))


def trip_words():
    """gc.json trip_words (optional; the engine ships none): the person's own place and travel vocabulary for stitching trips.
    Keys: city_country {city: country}, home_places {word: place}, airports {code: city}, home_airports [code],
    airlines [name, lower case], travel_only {word: country}. A missing setup folder or key gives empty vocabularies."""
    try:
        d = load("gc.json").get("trip_words") or {}
    except SettingsError:
        d = {}
    return {"city_country": d.get("city_country") or {}, "home_places": d.get("home_places") or {},
            "airports": d.get("airports") or {}, "home_airports": list(d.get("home_airports") or ()),
            "airlines": list(d.get("airlines") or ()), "travel_only": d.get("travel_only") or {}}


def sanity_lists():
    """gc.json sanity: {"projects": [[label, [regex, ...]], ...], "near": [...]} -> two tuples of (label, [regex...])."""
    s = gc("sanity")
    return (tuple((p[0], list(p[1])) for p in _need(s, "projects", "gc.json sanity")),
            tuple((p[0], list(p[1])) for p in _need(s, "near", "gc.json sanity")))
