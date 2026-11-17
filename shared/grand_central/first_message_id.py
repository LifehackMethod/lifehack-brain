"""Print the id of one recent message, read through the sanctioned email door with the rig login.
Used only by wall_test_terminal.sh to aim its (must-be-refused) change attempts at a real message."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_env  # noqa: E402



def main():
    rig_env.apply_to_this_process()
    sys.path.insert(0, rig_env.EMAIL_DOOR_DIR)
    import email_fetch  # noqa: E402

    data, err = email_fetch.list_threads({"maxResults": 1})
    tid = ((data or {}).get("threads") or [{}])[0].get("id") if not err else None
    if not tid:
        return 1
    data, err = email_fetch.get_thread(tid, "metadata")
    print(((data or {}).get("messages") or [{}])[0].get("id", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
