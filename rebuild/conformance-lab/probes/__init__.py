# conformance-lab probes package.
#
# Each module here exposes ONE callable with the driver's probe interface:
#
#     def probe(rule: dict, ctx: dict) -> dict:
#         # rule -> one parsed registry row (every column as a string)
#         # ctx  -> run context (reserved; currently {})
#         # returns {"verdict": str, "evidence": str}
#
# Verdicts must come from driver.VALID_VERDICTS. A probe that cannot score a row returns
# `unscored` with a reason — never a pass. Register probes in driver.PROBES, keyed by category
# letter.
#
# Built:     guard.py  (category C — guard-provoke-assert-blocked)
# Not built: static / session / completeness / parked — see driver.py's header.
