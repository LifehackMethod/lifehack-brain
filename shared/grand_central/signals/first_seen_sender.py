"""first_seen_sender: this is the first message ever from this address in the DB. Only fires when true."""
import common as C

NAME, VERSION = "first_seen_sender", 1


def compute(con, item_ids):
    info = C.email_info(con, item_ids)
    seq = C.sender_sequence(con)
    out = {}
    for iid, em in info.items():
        rn = seq.get(em["message_id"], (None, None))[0]
        if rn == 1:
            out[iid] = (1.0, "first message ever from %s" % em["from"])
    return out
