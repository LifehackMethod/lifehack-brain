#!/usr/bin/env node
// ── LLM CONTEXT ──────────────────────────────────────────────────────────────
// PURPOSE: Prune archived-copy nodes from the obsidian-brain search index
//          (kg.db) that outrank live canon in /read search.  These are nodes
//          whose IDs fall under well-known archive prefixes — they accumulate
//          from vault archiving but the indexer re-indexes them at parity with
//          live canon, causing ~15% search pollution.
// WHY:     Debt item [SEARCH-INDEX-ARCHIVE-PRUNE] — recon confirmed 371/2408
//          nodes (15.4%) are archived duplicates outranking live canon.
// SAFE:    Calls the package's own deleteNode(), which handles the full cascade:
//          nodes, nodes_fts, nodes_vec, chunks, chunks_vec, edges, sync, communities.
//          An inline orphan assertion runs after the delete loop — exits non-zero
//          if any cascade missed a dependent row.
// USAGE:   node obsidian-prune-archive.mjs [db-path]
//          Default db-path: ~/.local/share/obsidian-brain/kg.db
// WIRED:   obsidian-reindex.sh runs this post-reindex (rc=0 gate only).
// BUILT:   2026-06-27 — Task A2-PRUNE
// ─────────────────────────────────────────────────────────────────────────────

import path from 'path';
import os from 'os';

// Absolute path to the pinned 1.7.24 build's store module.
// Using the npx-cache path directly so this script doesn't require a separate
// npm install — the obsidian-brain indexer already pulled this build.
// NOTE: the npx cache at 60329cdc3f47b3b7 has better-sqlite3 compiled for
// NODE_MODULE_VERSION 141 (Node 24/25); at runtime we are on Node v26 (NMV 147).
// The 271d0627516ce9e8 cache was built for Node v26 and works.
const OB_DIST = process.env.OBSIDIAN_BRAIN_DIST ?? path.join(os.homedir(), '.npm/_npx/271d0627516ce9e8/node_modules/obsidian-brain/dist');

// Fail loudly and by name if the pinned build is not in the npx cache (5.7). Nothing is installed.
let openDb, deleteNode;
try {
  ({ openDb } = await import(`${OB_DIST}/store/db.js`));
  ({ deleteNode } = await import(`${OB_DIST}/store/nodes.js`));
} catch (e) {
  console.error(`[obsidian-prune-archive] FATAL: cannot load the pinned obsidian-brain build from ${OB_DIST}: ${e.message}`);
  process.exit(1);
}

// ── Config ────────────────────────────────────────────────────────────────────
const DEFAULT_DB = path.join(os.homedir(), '.local/share/obsidian-brain/kg.db');
const dbPath = process.argv[2] ?? DEFAULT_DB;

// Noise prefixes — IDs starting with any of these are archived copies that
// should not appear in live search results.
const NOISE_PREFIXES = [
  'state/archive/',
  'system/archivist/insight-inbox/archive/',
  'desks/marc/records/backups/',
];

// Huddle: only sub-paths that contain /archive/ — live huddle threads are NOT touched.
function isNoiseId(id) {
  for (const p of NOISE_PREFIXES) {
    if (id.startsWith(p)) return true;
  }
  // state/huddle/.../archive/... — match any node whose huddle sub-path
  // contains an /archive/ segment (never the root state/huddle/<room>/*.md live files).
  if (id.startsWith('state/huddle/') && id.includes('/archive/')) return true;
  return false;
}

// ── Open DB ───────────────────────────────────────────────────────────────────
console.log(`[obsidian-prune-archive] opening: ${dbPath}`);
const db = openDb(dbPath);

// ── Collect targets ───────────────────────────────────────────────────────────
const allIds = db.prepare('SELECT id FROM nodes').all().map(r => r.id);
const targets = allIds.filter(isNoiseId);
console.log(`[obsidian-prune-archive] found ${targets.length} noise nodes (of ${allIds.length} total)`);

// ── Delete loop ───────────────────────────────────────────────────────────────
let deleted = 0;
for (const id of targets) {
  deleteNode(db, id);
  deleted++;
}
console.log(`[obsidian-prune-archive] deleted ${deleted} nodes`);

// ── Orphan assertion (inline) ─────────────────────────────────────────────────
// Verifies the cascade was complete: no dependent rows in chunks, chunks_vec,
// nodes_fts, or edges should reference a node_id / source_id / target_id that
// no longer exists in nodes.
//
// chunks has ON DELETE CASCADE from nodes, so it should always be 0.
// chunks_vec is a vec0 virtual table (no FK cascade) — deleteNode vacuums it.
// nodes_fts is content-external FTS5 — deleteNode fires the 'delete' command.
// edges (source_id + target_id) — deleteNode calls deleteEdgesBySource/Target.

const orphanChunks = db.prepare(
  "SELECT count(*) AS n FROM chunks WHERE node_id NOT IN (SELECT id FROM nodes)"
).get().n;

// chunks_vec rowids must match chunks rowids — check via cross-join existence
const orphanChunksVec = db.prepare(
  "SELECT count(*) AS n FROM chunks_vec WHERE rowid NOT IN (SELECT rowid FROM chunks)"
).get().n;

// nodes_fts is an external-content table — we can only check for stale rowids
// (rowids in nodes_fts shadow not in nodes).  The FTS5 'delete' inserts remove
// the content; stale rowids would surface as ghost matches.
const orphanFts = db.prepare(
  "SELECT count(*) AS n FROM nodes_fts WHERE rowid NOT IN (SELECT rowid FROM nodes)"
).get().n;

const orphanEdgesSource = db.prepare(
  "SELECT count(*) AS n FROM edges WHERE source_id NOT IN (SELECT id FROM nodes)"
).get().n;

const orphanEdgesTarget = db.prepare(
  "SELECT count(*) AS n FROM edges WHERE target_id NOT IN (SELECT id FROM nodes)"
).get().n;

const totals = {
  chunks:       orphanChunks,
  chunks_vec:   orphanChunksVec,
  nodes_fts:    orphanFts,
  edges_source: orphanEdgesSource,
  edges_target: orphanEdgesTarget,
};

const anyOrphans = Object.values(totals).some(n => n > 0);

if (anyOrphans) {
  console.error('[obsidian-prune-archive] ORPHAN ASSERTION FAILED — cascade incomplete:');
  for (const [table, count] of Object.entries(totals)) {
    if (count > 0) console.error(`  ${table}: ${count} orphan rows`);
  }
  process.exit(1);
}

console.log('[obsidian-prune-archive] orphan assertion CLEAN — all dependent tables consistent');
console.log(`[obsidian-prune-archive] done. pruned=${deleted} remaining=${allIds.length - deleted}`);
