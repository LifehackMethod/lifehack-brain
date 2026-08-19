# IDENTITY fixture — a made-up person, so the lane can test its own personal tier
#
# ⚠ NOBODY REAL IS IN THIS FILE. Wren Oakley does not exist. This is the identity file the
# lane's own `verify_rules.py` and self-tests compile against, so that the personal tier —
# the half that cannot ship as a copy, because it is different for every person — is proved
# to work by the same two-sided test as everything else.
#
# THIS IS NOT YOUR IDENTITY FILE AND IT NEVER BECOMES ONE. Yours lives outside this repo, at
# `<notes>/config/ship-identity.md`. Make it with:
#     python3 system/shipping-lane/identity_rules.py --write-example
#
# Each line below exercises one of the three shapes `identity_rules.py` detects: a
# multi-word name, single words, a handle, an address, and a client name.
#
# ⚠ EVERY EXPLANATORY LINE IN THIS FILE IS COMMENTED, AND THAT IS LOAD-BEARING. An
# un-commented sentence is read as a term. The parser refuses one rather than compiling it,
# but the refusal is only useful if the file it ships as an example does not model the
# mistake.

Wren Oakley
Wren
Oakley
woakley
wren.oakley@example.com
Whitfield Contracting
