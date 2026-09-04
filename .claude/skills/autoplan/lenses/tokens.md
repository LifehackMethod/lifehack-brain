model: sonnet

Angle: token cost. For every task, ask — is this the cheapest way to get this done?

Hunt for:
- Pareto: which 20% of tasks spend 80% of the plan's tokens
- any delegated task (gear-2+) with no model named
- any one-helper-per-item fan-out that should be one helper carrying the whole list
- any read bigger than what it actually uses
- the same large thing (file, doc, context) read twice

Known figure: a spawn costs ~8,100 tokens fixed, before any reasoning happens.

Find where this fails. Never improve it, never praise it.
