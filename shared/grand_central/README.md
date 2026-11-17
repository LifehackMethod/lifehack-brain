# Grand Central

## Commands run by a person or from outside the plugin

- The mailroom daemon is started by the mailroom installer: `python3 shared/grand_central/reader/readerd.py`
- First-run setup creates the setup folder from the shipped examples: `python3 shared/grand_central/first_run.py`
- The mailroom wall proof: `python3 shared/grand_central/wall_test.py`
- The same wall proof from a terminal: `bash shared/grand_central/wall_test_terminal.sh`
- The mailroom firewall check: `python3 shared/grand_central/tools/lulu_rules_check.py`
- The handoff folder Sentinel gate: `python3 shared/grand_central/handoff/handoff.py`
- Seed the local working copies of the Drive files the scheduled jobs read (run once from a terminal after a deploy; never from launchd): `python3 shared/grand_central/local_first.py --seed`
