# Setup migrations

This folder holds the owner's own SQL migrations for the Grand Central database, numbered in order
(`001_*.sql`, `002_*.sql`, ...). They are the owner's files: the plugin ships none, and an EMPTY
series here is a valid, working state — a fresh setup needs no migration.

How a migration runs, and what the engine expects of the series, is in the plugin's migration
runner (shared/grand_central/migrate.py). Rules of thumb:

- Name files `NNN_description.sql`; they run in name order, once each.
- Never edit a migration that has already run; add a new one.
- A first-run copy of this README is the only thing first_run.py places here.
