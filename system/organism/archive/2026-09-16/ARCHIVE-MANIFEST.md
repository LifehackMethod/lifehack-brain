---
status: active
authority: user
---

# Organism-docs archive manifest — 2026-09-16

> Replaces an earlier local draft of this K3 snapshot that copied full file contents into this
> directory. That draft is not represented here because the copied files' worked examples describe
> personally identifying detail; this manifest carries the same audit intent (a fixed, checksummed
> record of the organism-docs set as it stood on 2026-09-16) without reproducing that content in this
> public repo.

## What this is

A paths + sha256 record of the `system/organism/` documentation set — the root map (`CLAUDE.md`), the
manual, and every `system/organism/elements/*.md` file — exactly as each stood in this repo on
2026-09-16, per the no-deletions doctrine: a dated checkpoint that lets a later session prove whether
one of these files has since drifted, without a byte-for-byte copy sitting in the public tree.

A full byte-identical copy of each file listed below, taken on the same date, lives in a private
archive, not in this repo.

## How to verify a file against this record

```
shasum -a 256 <path>
```

The result matches the hex value in the table below when the file is unchanged since 2026-09-16.

## Manifest

| path | sha256 |
|---|---|
| `CLAUDE.md` | `fda1cd655b107a36b98d65756d7c2f42f3c20583db7fceed03b5f96ef2b24347` |
| `system/organism/manual.md` | `d6d9cb079a86359d999519ccc807d3aa0f813e24ab8b43b60dcdee9ca14d182b` |
| `system/organism/elements/archivist.md` | `eaab473bfeffa5efe0f2d89b59af170d3baf75498bb173e38eaf0530e67219de` |
| `system/organism/elements/backlog-authority.md` | `eea2a8028590d4bc25a3c2b3dd1485a02e73b6d87ff017628a1466217a029a78` |
| `system/organism/elements/brain.md` | `0352314ea30f4cd8b71c51b1a79b002ba3c00b9f64836cfc064388851e6357ce` |
| `system/organism/elements/build-plan-plane.md` | `2d0cca859c5746db14a768fea86a3314396eb5cb38f595daddd287fe8ef43514` |
| `system/organism/elements/calculate.md` | `88637eb62cc1ff434d4ddda0d0f582798e7a97e79c923fba53cbaed3f0646e8d` |
| `system/organism/elements/canon.md` | `1275a00cadd9c2f191933dd81ba70bf29b7e6c2463cc05f839a14e985227ae8f` |
| `system/organism/elements/claude-md-pyramid.md` | `70512a74d8f036b89532f08bb070a7c2b9309da83610e0be07d510a3022f9af7` |
| `system/organism/elements/compute-mechanically-gate.md` | `17bac617e99911783f3fef8feb9466a6d1c49f990dce5fea62e63e7059d64159` |
| `system/organism/elements/council-engine.md` | `a071855e4e562978d0d611495799d11283e126590df50ee9b1fecb993acfb778` |
| `system/organism/elements/efficiency.md` | `c93b5108c626cfb4ba0682addfb235e3abee658abde5597576d64943d8d0d55a` |
| `system/organism/elements/egress-allowlist-wall.md` | `4d425fa65abc427d4d6392044c164b1388fe113e016149ba19d026e4e4f824c1` |
| `system/organism/elements/email-service.md` | `fb6a31a2ad5c17bd2600281aef38e28f9f25ad8adad526a71230aff7874e7b9c` |
| `system/organism/elements/google-sheet.md` | `e176c7b8fd195edabd2266cac0f5e747dabf6770147ea6c710bc6ee92a51997f` |
| `system/organism/elements/grand-central.md` | `55f2e9e5ff03320d72633d3efd2d890452bc1772b3a5db9f29c83d225df8344b` |
| `system/organism/elements/gws-plane.md` | `d355fd3000982a309bb67528305c0cea2864de647f8a7961fb94f23248f6abc4` |
| `system/organism/elements/health-invariants.md` | `580a23b64e6a9a1baaefe892f340e8656d21104b237834309f49c7fe5466bf66` |
| `system/organism/elements/hook-plane.md` | `17a134e10dcdc4ad283c304685bcbc596e3cce4859e3dd23dd56ba71359ef988` |
| `system/organism/elements/hospital.md` | `ef00b3362214365acfca8192ff448f075eb82041f6df79178998be688674e7d2` |
| `system/organism/elements/ingest-gate.md` | `e74e7e189c915968802e03f9a7a96354512e82dfaeea690c6e49ce5687dd3b75` |
| `system/organism/elements/ingest-run-lib.md` | `d41139d33030ec32515b320e56be6b774897c0118e1c38227142e0eb496f6162` |
| `system/organism/elements/item-store.md` | `17ce700352c9fb17b5482614a18a58873a4b53a9c27fb77712e51ab0913eef98` |
| `system/organism/elements/journal.md` | `fd644c37509488179128b8f3c98de79dcc17f1935399ea7f6387a0b6fc0ca816` |
| `system/organism/elements/label-checker.md` | `164309d3981fe33eb1beb28d306e4ec46a5099ceeeccf791b7c4c31905b08981` |
| `system/organism/elements/notify-plane.md` | `0971b67477a8364f1ac4dd2ec255c269f4e0d353a028027fcf20aa6f915b1c19` |
| `system/organism/elements/plan-integrity-cluster.md` | `20d9af5d9a30249412950a9997b921d1f2d6e6687945723c6f76288b17802fca` |
| `system/organism/elements/planning.md` | `ebf29600161bbcab4fe1e74b1d1cd7e84ebe6f5d060047de153fdc4f1d0d5384` |
| `system/organism/elements/pm-flag.md` | `2e46bb25c97e52599953fd14aa953517325c715ab5a0ce744b7dc1d368e3a767` |
| `system/organism/elements/project-manager.md` | `352edce0a0f1a8742cb4087f3b22e799dcafa80a17d60d432aef733eacb6e45b` |
| `system/organism/elements/pulse-cron.md` | `ac90412e23d6a38e81c40d6872f9c0401ada0741f97391e113fab881d3771510` |
| `system/organism/elements/read.md` | `4f2accee6d57330398eab56c7b6365af21432fdf7d7e870faaa0651b14112ea5` |
| `system/organism/elements/red-team.md` | `70491c09429ae2955dd560f28b30d0f91817e3f99f8420c95e7ea880bea3ae39` |
| `system/organism/elements/research-web-plane.md` | `f7c0d404f2936931b775af450f549fb124f64fdee5ef4be6ae48cc8ea047d3b1` |
| `system/organism/elements/safe-reader-plane.md` | `159492c95f723f06440469311318c4301287cb71fca0989294847d3d0a574335` |
| `system/organism/elements/save.md` | `a22a07d81a61d40782a65d550c26175294f44bc8f7516d1d9a054f99f4f5050a` |
| `system/organism/elements/scratch-capture-gate.md` | `b48680981ef306a55ade514e49bb367b43c03eeb5c4a75a186f638d2b6647f6a` |
| `system/organism/elements/security-ingest-gate.md` | `4670c6f9d54a9dd10c15c4dcc0f224a54628563cbd6f58a818e0fe8a5e6a4629` |
| `system/organism/elements/sentinel.md` | `2256a400ce19136271ca72ca0f0141c14c525b85048d8c33bca6c4ccd03737e8` |
| `system/organism/elements/skill-system.md` | `7db8c715a6733ee3373f40e80e690ff11cfe86b0ed013479bbe19f54ad0d7bd6` |
| `system/organism/elements/statusline-hud.md` | `63982a55357e1c840fcaa22bfa470ba27bbd7b5fecfd0a2f7630b51382725c4c` |
| `system/organism/elements/strategic-navigation-cluster.md` | `5700c9a4434ea9d65c17ade4da352903c0ed9bc91c2efcb0f8f413cd52db2b5b` |
| `system/organism/elements/topic-vocab-lint.md` | `7a986959892911dd045a9862cae350ee74e8699047fc42e37d9e75296b0615f9` |
| `system/organism/elements/translator-cluster.md` | `461fefd51fee481efec89848bfee494e5a2e600025277761165af07301c80a33` |
| `system/organism/elements/where-things-live.md` | `5e90d5ae275840873ec1b3afb0df32cbcdd871b965882e5032de043baf56c535` |
| `system/organism/elements/world-model-ingestion.md` | `3ce396001a317ac69fff1529fa6454e2846cde663781b33bb7e32fea5430f41b` |

## Notes

- `pulse-cron.md`'s hash above is the file's content as currently live in this repo. A pending R6
  citation correction to that file (striking a stale "landed" claim) is a separate change, not folded
  into this manifest; if it lands, this row will need a refresh.
- 46 paths total: `CLAUDE.md` (the root map), `system/organism/manual.md`, and the 44 files under
  `system/organism/elements/`.
- No file under `system/organism/` was moved or removed from its live location to produce this
  manifest — every path above still resolves at its normal, in-use location in this repo.
