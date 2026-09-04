# Lens contract

Every lens receives:
- the plan FILE path (never chat history)
- its one angle (this lens's own file)
- the instruction: find where this fails — never improve it, never praise it
- when testing, a fixture path

Rules:
- attack every phase equally — never phase 1 harder than the rest
- you are blind — you never see another lens's output
- do not spawn sub-agents
- an honest empty return is valid; do not pad findings to look thorough

Return EXACTLY this shape:

```
model: <sonnet|opus>
findings:
- task_id: <id or "plan-level">
  claim: <one sentence: what fails>
  evidence: <the line(s) in the plan, quoted or line-numbered>
  proposed_change: <one sentence>
  severity: HIGH | MED | LOW
verdict: <one line>
```

If there are no findings, return `findings: []` — an empty findings[] list is
a valid, honest result, not a failure to try.

Cost line: six lenses cost ~6 × 8,100 = 48,600 tokens fixed per run before any
reasoning; two of the six run on opus.
