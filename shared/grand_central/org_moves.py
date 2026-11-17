"""org_moves.py: Phase 3 step 3.1. Move today's `company` things and `circle` things into organizations (Vision 3.7.3, plan 3.1).

  python3 org_moves.py --db PATH            # dry run: what would move
  python3 org_moves.py --db PATH --apply    # act (on a COPY; the live file is moved by the build window at step 3.9)

Two halves, so a rebuild reproduces the same model with the same keys:
  record_moves(con)  decides and RECORDS (org_moves + thing_keys): one organization per old thing, key minted once. Run once.
  apply_moves(con)   reads that record and builds the model from it: the organization, its type, the old thing's current facts
                     and links re-pointed onto it, the old thing retired and merged (never deleted). Idempotent. `gc rebuild`
                     calls it after the replay, so the moves are part of the rebuild.
Code stores no guess: the type of an old company is the kind it already had; the type `group` for a circle is his 2026-11-16
ruling, stored as 'likely' (not his word) and, where a circle does not look like a group, a QUESTION goes to him instead.
Circle membership lines the code wrote itself are NOT carried (placement is his word); the ones that cite his recorded words
were already carried over as his (step 2.5) and move across with their answer.
"""
import argparse
import os
import secrets
import sys

import clock
import db
import store_graph as sg

QKIND = "onboarding-org-type"   # the queue kind for "what kind of thing is this?": HELD for the onboarding sitting (step 3.10)
HELD = "held for the onboarding sitting (step 3.10); not asked in the everyday list"
SOURCE = "migration 021"


def _ts():
    return sg._ts()


def _mint(con):
    while True:
        key = "organization:" + secrets.token_hex(5)
        if not con.execute("SELECT 1 FROM thing_keys WHERE key=?", (key,)).fetchone():
            return key


def record_moves(con):
    """One org_moves row (and one thing_keys row, old key as made_from) per company and circle thing not yet moved.
    Returns {"company": n, "circle": n}. The caller owns the transaction."""
    done = {r[0] for r in con.execute("SELECT old_key FROM org_moves")}
    n = {"company": 0, "circle": 0}
    for tid, kind, key, name, created_by in con.execute(
            "SELECT id, kind, key, name, created_by FROM kg_things WHERE kind IN ('company','circle') AND merged_into IS NULL "
            "ORDER BY kind DESC, id").fetchall():     # companies first, then circles (stable order)
        if key in done:
            continue
        if kind == "company":
            otype = "company"
            cert = "sure" if created_by == "owner" else "likely"
            src = "%s: the kind it already had (company), key %s" % (SOURCE, key)
        else:
            otype, cert = "group", "likely"
            src = "%s: his 2026-11-16 ruling (circles become groups), key %s" % (SOURCE, key)
        new = con.execute("SELECT key FROM thing_keys WHERE made_from=? AND kind='organization'", (key,)).fetchone()
        new = new[0] if new else _mint(con)
        now = _ts()
        con.execute("INSERT OR IGNORE INTO thing_keys(key, kind, made_from, created_at) VALUES(?,?,?,?)",
                    (new, "organization", key, now))
        con.execute("INSERT INTO org_moves(old_key, old_kind, new_key, name, org_type, certainty, source, moved_at) "
                    "VALUES(?,?,?,?,?,?,?,?)", (key, kind, new, name, otype, cert, src, now))
        n[kind] += 1
    return n


def apply_moves(con):
    """Build every recorded move into the model. Idempotent. Returns counts."""
    c = {"organizations": 0, "facts_moved": 0, "links_moved": 0, "facts_left": 0, "links_left": 0, "retired": 0}
    for mid, old_key, old_kind, new_key, name, otype, cert, src, moved_at in con.execute(
            "SELECT id, old_key, old_kind, new_key, name, org_type, certainty, source, moved_at FROM org_moves ORDER BY id").fetchall():
        org = sg.thing(con, "organization", name, created_by="code", key=new_key)
        own = sg.thing_by_key(con, new_key)["id"]
        merged_away = own != org      # he merged this organization into another (step 3.6): its rows go to the survivor, which keeps its own name and type
        if not merged_away:
            con.execute("UPDATE kg_things SET name=? WHERE id=? AND name<>?", (name, org, name))   # display name kept as it was
        c["organizations"] += 1
        old = sg.thing_by_key(con, old_key)
        old_id = old["id"] if old else sg.thing(con, old_kind, name, created_by="code", key=old_key)
        if old_id == org:
            continue
        if not merged_away and not con.execute("SELECT 1 FROM kg_facts WHERE thing_id=? AND fact_key='org_type' AND source_ref=?", (org, src)).fetchone():
            sg.assert_fact(con, org, "org_type", otype, "code", cert, "legacy", src)
        for fid, key, val, who, cer, sk, sref, aid, tf, tu, cond in con.execute(
                "SELECT id, fact_key, value, who, certainty, source_kind, source_ref, answer_id, true_from, true_until, condition "
                "FROM kg_facts WHERE thing_id=? AND replaced_by IS NULL ORDER BY id", (old_id,)).fetchall():
            try:
                sg.check_fact(con, "organization", key, val)
            except sg.Refused:
                c["facts_left"] += 1       # e.g. circle_kind: not carried (a standing circle needs no kind; a dated one is a question)
                continue
            new = sg.assert_fact(con, org, key, val, who, cer, sk, sref, aid, tf, tu, cond)
            con.execute("UPDATE kg_facts SET replaced_by=? WHERE id=?", (new, fid))
            c["facts_moved"] += 1
        for lid, a, kind, b, role, who, cer, sk, sref, aid, tf, tu in con.execute(
                "SELECT id, from_id, kind, to_id, role, who, certainty, source_kind, source_ref, answer_id, true_from, true_until "
                "FROM kg_links WHERE (from_id=? OR to_id=?) AND replaced_by IS NULL ORDER BY id", (old_id, old_id)).fetchall():
            na, nb = (org if a == old_id else a), (org if b == old_id else b)
            try:
                new = sg.add_link(con, na, kind, nb, who, cer, sk, sref, aid, tf, tu, role)
            except sg.Refused:
                c["links_left"] += 1       # a membership the code wrote itself: placement is his word, so it stays history
                continue
            con.execute("UPDATE kg_links SET replaced_by=? WHERE id=?", (new, lid))
            c["links_moved"] += 1
        if con.execute("UPDATE kg_things SET merged_into=?, retired_at=? WHERE id=? AND merged_into IS NULL",
                       (own, moved_at, old_id)).rowcount:
            c["retired"] += 1
    return c


def _people_ever_linked(con, *thing_ids):
    """People with any membership line to these things, current or not (a line waiting on his answer still says who was named)."""
    q = ",".join("?" * len(thing_ids))
    return con.execute("SELECT count(DISTINCT from_id) FROM kg_links WHERE kind='member_of' AND to_id IN (%s)" % q, thing_ids).fetchone()[0]


def ask_what_kind(con):
    """A circle that may not be a group becomes a QUESTION for him (queue), never a guess in the model: one that is dated (a
    job with an end), or has had just one person named for it (a business or an arrangement rather than a circle of people). Held for the
    onboarding sitting (not in the open list), once per organization. Returns the number of questions added."""
    added = 0
    for ok, name, ck in con.execute("SELECT m.new_key, m.name, m.old_key FROM org_moves m WHERE m.old_kind='circle' ORDER BY m.id").fetchall():
        old = sg.thing_by_key(con, ck)
        dated = con.execute("SELECT 1 FROM kg_facts WHERE thing_id=? AND fact_key='circle_kind' AND value='dated' AND replaced_by IS NULL",
                            (old["id"],)).fetchone()
        # people named for it, on the organization (his carried-over lines) and on the old circle (any line, current or not)
        members = _people_ever_linked(con, sg.thing_by_key(con, ok)["id"], old["id"])
        one_member = members == 1
        if not (dated or one_member):
            continue
        if con.execute("SELECT 1 FROM queue WHERE kind=? AND subject_ref=?", (QKIND, ok)).fetchone():
            continue
        q = ('What kind of thing is "%s"? I filed it as a group (a family, a circle of friends, a club: everyone at the same level) '
             "because you ruled that the old circles become groups, but it may be something else: a company, a team, or one job "
             "with an end date.%s Which is it?" % (name, " It was marked as dated: when does it end?" if dated else ""))
        # the queue has no "not yet asked" status (open / answered / dismissed only, and every everyday list reads 'open'), so a held
        # question is stored dismissed with the reason in `answer`; the sitting collects it by its kind (onboarding_set), not by status
        con.execute("INSERT INTO queue(kind, subject_ref, question, proposed_answer, status, created_at, answered_at, answer) "
                    "VALUES(?,?,?,?,'dismissed',?,NULL,?)", (QKIND, ok, q, "group", _ts(), HELD))
        added += 1
    return added


def onboarding_set(con):
    """The questions held for the onboarding sitting: [(id, subject_ref, question, proposed_answer)], whatever their status."""
    return con.execute("SELECT id, subject_ref, question, proposed_answer FROM queue WHERE kind LIKE 'onboarding-%' "
                       "AND answer=? ORDER BY id", (HELD,)).fetchall()


def check_moves(con):
    """The finish check, as a function: -> list of problems (empty = fine).
      every company and circle thing has exactly one organization, one org_moves row and one thing_keys row (old key as made_from);
      each organization has exactly one current org_type; nothing was deleted (every old thing is still there, retired and merged)."""
    bad = []
    for key, kind in con.execute("SELECT key, kind FROM kg_things WHERE kind IN ('company','circle')").fetchall():
        rows = con.execute("SELECT new_key FROM org_moves WHERE old_key=?", (key,)).fetchall()
        if len(rows) != 1:
            bad.append("%s has %d organization(s), expected exactly 1" % (key, len(rows)))
            continue
        nk = rows[0][0]
        if con.execute("SELECT count(*) FROM thing_keys WHERE key=? AND kind='organization' AND made_from=?", (nk, key)).fetchone()[0] != 1:
            bad.append("%s: its organization %s has no thing_keys row naming it as the source" % (key, nk))
        org = con.execute("SELECT id, merged_into FROM kg_things WHERE key=? AND kind='organization'", (nk,)).fetchone()
        if org is None:
            bad.append("%s: organization %s is missing from the model" % (key, nk))
            continue
        if con.execute("SELECT count(*) FROM kg_facts WHERE thing_id=? AND fact_key='org_type' AND replaced_by IS NULL", (org[0],)).fetchone()[0] != 1:
            bad.append("%s: organization %s must have exactly one current org_type" % (key, nk))
        merged = con.execute("SELECT merged_into, retired_at FROM kg_things WHERE key=?", (key,)).fetchone()
        if merged[0] != org[0] or not merged[1]:
            bad.append("%s was not retired and merged into %s" % (key, nk))
    for key, in con.execute("SELECT m.old_key FROM org_moves m WHERE NOT EXISTS (SELECT 1 FROM kg_things WHERE key=m.old_key)").fetchall():
        bad.append("%s was deleted (an old thing may only be retired)" % key)
    for nk, n in con.execute("SELECT new_key, count(*) FROM org_moves GROUP BY new_key HAVING count(*)>1").fetchall():
        bad.append("organization %s was made from %d old things" % (nk, n))
    return bad


def run(db_path, apply=False, out=print):
    con = db.connect(db_path)
    con.isolation_level = None
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name='org_moves'").fetchone():
        raise SystemExit("migration 021 is not applied to %s" % db_path)
    if not apply:
        todo = con.execute("SELECT kind, count(*) FROM kg_things WHERE kind IN ('company','circle') AND merged_into IS NULL "
                           "AND key NOT IN (SELECT old_key FROM org_moves) GROUP BY kind").fetchall()
        out("dry run on %s: would record moves for %s" % (db_path, dict(todo) or "nothing"))
        return 0
    con.execute("BEGIN IMMEDIATE")
    try:
        r = {"recorded": record_moves(con), "applied": apply_moves(con)}
        r["questions_added"] = ask_what_kind(con)
        r["problems"] = check_moves(con)
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    out(str(r))
    return 1 if r["problems"] else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", required=True, help="the database to move (always a copy until the live deploy)")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    return run(os.path.abspath(a.db), apply=a.apply)


if __name__ == "__main__":
    sys.exit(main())
