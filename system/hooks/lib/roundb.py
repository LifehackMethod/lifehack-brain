"""Round B switch reader. roundb_on("back_door") -> bool.
Env ROUNDB_<NAME> (upper case) overrides roundB.conf; anything but "on" is off."""
import os
from pathlib import Path

CONF = Path(__file__).resolve().parent.parent / "roundB.conf"


def roundb_on(name: str) -> bool:
    val = os.environ.get("ROUNDB_" + name.upper())
    if val is None:
        val = ""
        try:
            for line in CONF.read_text().splitlines():
                if line.startswith(name + "="):
                    val = line.split("=", 1)[1].strip()
        except OSError:
            pass
    return val.strip() == "on"


def roundb_val(name: str) -> str:
    """A VALUED line (not on|off), e.g. fc_private_push_mode=block|warn. Env ROUNDB_<NAME> wins; "" when absent."""
    val = os.environ.get("ROUNDB_" + name.upper())
    if val is None:
        val = ""
        try:
            for line in CONF.read_text().splitlines():
                if line.startswith(name + "="):
                    val = line.split("=", 1)[1].strip()
        except OSError:
            pass
    return val.strip()
