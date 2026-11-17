"""to_vs_cc: he is in To (1.0), only in Cc (0.4), neither (0.0: list or bcc). 'Him' = the addresses in s_me."""
import common as C

NAME, VERSION = "to_vs_cc", 1


def compute(con, item_ids):
    info = C.email_info(con, item_ids)
    me = C.me_set(con)
    out = {}
    for iid, em in info.items():
        if me & set(em["to"]):
            out[iid] = (1.0, "you are in To")
        elif me & set(em["cc"]):
            out[iid] = (0.4, "you are only in Cc")
        else:
            out[iid] = (0.0, "not in To or Cc (list or bcc)")
    return out
