"""sender_history: how much this sender has written him and how much he wrote back (s_addr_signals). Every email item."""
import common as C

NAME, VERSION = "sender_history", 1


def compute(con, item_ids):
    info = C.email_info(con, item_ids)
    stats = {r[0]: (r[1], r[2]) for r in con.execute("SELECT address, msgs_from, replies_to FROM s_addr_signals")}
    out = {}
    for iid, em in info.items():
        n, rep = stats.get(em["from"], (0, 0))
        v = round(0.5 * min(1.0, n / 20.0) + 0.5 * min(1.0, rep / 5.0), 3)
        out[iid] = (v, "wrote %d time%s; you replied %d" % (n, "" if n == 1 else "s", rep))
    return out
