# REFUSE fixture — one planted instance of EVERY rule the lane can compile

⚠ **THIS FILE EXISTS TO BE CAUGHT.** It is deliberately full of the exact shapes the
shipping lane refuses. It is a test artifact: it ships with the lane, it is never in a
shipping manifest, and nothing here belongs to anybody. **Every credential below is
SYNTHETIC and obviously fake.** The person is the fixture identity, Wren Oakley, who does
not exist — see `identity-fixture.md`.

If `verify_rules.py` ever reports a rule that did NOT fire against this file, that rule is
dead and the lane is quietly weaker than it looks. That is the whole point of this fixture,
and it is why the file has to carry a planted instance of the personal tier too: those
rules are compiled from a person's own identity file, so a fixture that only covered the
shipped generic rules would leave the half that actually protects them unproven.

## home paths — the account name IS the path segment
- path-home-unix (macOS): the store lives under /Users/wren/Library and is not portable.
- path-home-unix (Linux): the same store on a server sits at /home/woakley/store.
- path-home-windows: on Windows it is C:\Users\wren\Documents\notes, which no `$HOME`
  substitution can portably rewrite, so it is reported rather than guessed at.

## cloud-drive mounts — the mount name embeds the account
- path-drive-cloudstorage: mounted at Library/CloudStorage/GoogleDrive-someone/My Drive.
- path-drive-account: the mount is literally GoogleDrive-wren.oakley@example.com/My Drive.

## the personal tier — compiled from the fixture identity file, not shipped in this repo
- identity, multi-word name: Wren Oakley reviews every publish personally.
- identity, given name alone: ask Wren before the branch merges.
- identity, family name alone: the oakley_notes.md file is a draft, not a release.
- identity, handle: the account woakley owns the private working tree.
- identity, address: reachable at wren.oakley@example.com for anything urgent.
- identity, a client who has not been announced: the Whitfield Contracting engagement
  starts in March.

## credentials — ALL SYNTHETIC, NONE REAL
- key-openai: sk-FAKEFAKEFAKEFAKEFAKE1234
- key-anthropic: sk-ant-FAKEFAKEFAKEFAKEFAKE1234
- key-github-token: ghp_FAKEFAKEFAKEFAKEFAKE1234
- key-github-pat: github_pat_FAKEFAKEFAKEFAKEFAKE1234
- key-google-api: AIzaFAKEFAKEFAKEFAKEFAKEFAKEFAKE1234
- key-google-oauth: ya29.FAKEFAKEFAKEFAKEFAKEFAKE1234
- key-slack: xoxb-FAKEFAKE1234
- key-aws: AKIAFAKEFAKEFAKEFAKE
- key-private-block: -----BEGIN RSA PRIVATE KEY-----
- key-bearer: Authorization: Bearer FAKEFAKEFAKEFAKEFAKE1234
- key-assignment: api_key = "FAKEFAKEFAKEFAKE1234"

## presence-detectors in canon.py, NOT JSON rules
⚠ The three entries below are **not** rule-file entries, and `verify_rules.py` never sees
them. A literal-text regex against raw bytes cannot express "this Unicode codepoint is
present anywhere" (bidi controls, TAG-block characters), and small-caps text is not its own
rule at all — it feeds the EXISTING identity rules through `canon.py`'s fold. What proves
these three catch their target is `canon.py --selftest` at unit level, and `scrub.py` /
`push_gate.py --selftest`, each of which plants one in a real staged file and confirms
NOT-CLEAN / REFUSED. They are listed here anyway so a human skimming this fixture sees the
full hunted set in one place.
- unicode-bidi-control (`canon.scan_bidi_controls`): a name stored reversed inside a bidi
  override, rendering as the forward name in most editors and terminals — ‮nerW‬
  (storage order: RLO, "n","e","r","W", PDF).
- unicode-tag-chars (`canon.scan_tag_chars`): the name hidden entirely in invisible
  Unicode TAG-block characters after ordinary-looking text — notes󠁷󠁲󠁥󠁮󠀠󠁯󠁡󠁫󠁬󠁥󠁹
  (everything after "notes" is invisible TAG-block spelling "wren oakley").
- small-caps fold (feeds the compiled identity rules via `canon.py`, not its own rule id):
  signed ᴡʀᴇɴ ᴏᴀᴋʟᴇʏ
