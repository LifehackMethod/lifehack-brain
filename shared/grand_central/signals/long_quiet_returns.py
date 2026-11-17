"""long_quiet_returns: the sender's previous message was more than 90 days before this one. Only fires when true."""
import common as C

NAME, VERSION = "long_quiet_returns", 1
QUIET_DAYS = 90


def compute(con, item_ids):
    info = C.email_info(con, item_ids)
    seq = C.sender_sequence(con)
    out = {}
    for iid, em in info.items():
        prev = seq.get(em["message_id"], (None, None))[1]
        if prev is None or em["ms"] is None:
            continue
        gap = (em["ms"] - prev) / 86400000.0
        if gap > QUIET_DAYS:
            out[iid] = (round(min(1.0, gap / 365.0), 3), "back after %d days (last wrote %s)" % (
                int(gap), C.ms_dt(prev).date().isoformat()))
    return out
