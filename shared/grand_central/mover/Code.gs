/**
 * GC-mover: the drop-box mover. Five actions only: addLabel, removeLabel, archive, trash, untrash (trash = add the TRASH label,
 * untrash = remove it; both through batchModify, recoverable, never a delete).
 * Reads request.json from its own Drive folder every 15 min, applies it with Gmail batchModify, writes result.json
 * and a move log (one small JSON file per batch) with the undo for every batch. It never reads mail, sends, deletes or forwards.
 * Public functions: setup, run, pause, resume, teardownTriggers. Everything else ends in "_" (private).
 * The constants below that are mirrored in mover_schema.py are checked by tests/test_gs.py.
 */
var FOLDER_NAME = 'GC-mover';
var REQUEST_NAME = 'request.json';
var RESULT_NAME = 'result.json';
var ALLOWED_OPS = ['addLabel', 'removeLabel', 'archive', 'trash', 'untrash'];
var LABELLESS_OPS = ['archive', 'trash', 'untrash'];
var REQUEST_KEYS = ['request_id', 'created_at', 'actions'];
var ACTION_KEYS = ['op', 'label', 'ids'];
var SYSTEM_LABELS = ['INBOX', 'SENT', 'DRAFT', 'SPAM', 'TRASH', 'UNREAD', 'STARRED', 'IMPORTANT', 'CHAT',
  'CATEGORY_PERSONAL', 'CATEGORY_SOCIAL', 'CATEGORY_PROMOTIONS', 'CATEGORY_UPDATES', 'CATEGORY_FORUMS', 'YELLOW_STAR'];
var REQUEST_ID_RE = /^[A-Za-z0-9._-]{8,64}$/;
var CREATED_AT_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;
var MSG_ID_RE = /^[0-9a-f]{8,24}$/;
var LABEL_MAX_LEN = 225;

// Per-request SAFETY cap (typo guard; not a Google quota rule).
var MAX_IDS_PER_REQUEST = 5000;
var MAX_ACTIONS_PER_REQUEST = 20;
var MAX_TRASH_IDS_PER_REQUEST = 1000;   // total ids across all 'trash' actions in one request
var BATCH_SIZE = 1000;                 // Gmail batchModify maximum ids per call (confirmed 2026-11-12)
var MAX_BATCH_CALLS_PER_RUN = 10;
// Stop early so a run is never killed mid-batch at Google's 6-minute hard stop. Not a quota rule: leftovers carry
// over to the next run through the CURSOR script property.
var RUN_TIME_BUDGET_MS = 120000;
var MAX_FAILED_RUNS = 3;               // a batch that errors this many runs in a row aborts the request
var USAGE_KEEP_DAYS = 30;
var TRIGGER_MINUTES = 15;
var KEEP_PROCESSED = 100;

// ---------- public ----------
function setup() {
  var ctx = newCtx_();
  var folder = getFolder_(ctx, true);
  var names = [REQUEST_NAME, RESULT_NAME];
  for (var i = 0; i < names.length; i++) {
    if (!findFile_(folder, names[i], ctx)) {
      createInFolder_(folder, names[i], names[i] === RESULT_NAME ? '{"schema":1,"usage":[]}' : '', ctx);
    }
  }
  var have = ScriptApp.getProjectTriggers().filter(function (t) { return t.getHandlerFunction() === 'run'; });
  if (!have.length) { ScriptApp.newTrigger('run').timeBased().everyMinutes(TRIGGER_MINUTES).create(); }
  Logger.log('setup ok; run triggers: ' + Math.max(have.length, 1));
}

function run() {
  var t0 = Date.now();
  var ctx = newCtx_();
  if (pget_(ctx, 'PAUSED') === '1') { Logger.log('paused'); return 'paused'; }
  var S = { ctx: ctx, t0: t0, result: null, resFile: null };
  var out;
  try {
    out = runInner_(S);
  } catch (e) {
    Logger.log('run error: ' + e);
    out = 'error: ' + e;
    noteError_(S, S.key || null, null, 'run error: ' + e);   // never silent: it lands in result.json
  }
  try { finish_(S); } catch (e2) { Logger.log('finish error: ' + e2); }
  return out;
}

function pause() { pset_(newCtx_(), 'PAUSED', '1'); Logger.log('PAUSED'); }
function resume() { PropertiesService.getScriptProperties().deleteProperty('PAUSED'); Logger.log('resumed'); }
function teardownTriggers() {
  var ts = ScriptApp.getProjectTriggers();
  for (var i = 0; i < ts.length; i++) { ScriptApp.deleteTrigger(ts[i]); }
  Logger.log('deleted ' + ts.length + ' trigger(s)');
}

// ---------- plumbing ----------
function newCtx_() { return { gmail_calls: 0, ids_modified: 0, drive_ops: 0, properties_ops: 0 }; }
function pget_(ctx, k) { ctx.properties_ops++; return PropertiesService.getScriptProperties().getProperty(k); }
function pset_(ctx, k, v) { ctx.properties_ops++; PropertiesService.getScriptProperties().setProperty(k, v); }
function pdel_(ctx, k) { ctx.properties_ops++; PropertiesService.getScriptProperties().deleteProperty(k); }
function pjson_(ctx, k) { var v = pget_(ctx, k); return v ? JSON.parse(v) : null; }
function nowIso_() { return new Date(Date.now()).toISOString(); }

// Drive goes through the Advanced Drive service (v3): the built-in Drive class would need the full drive scope.
// A folder is its id (a string); a file is {id, name, parents}. Lookups are always by name inside our own folder.
var FOLDER_MIME = 'application/vnd.google-apps.folder';
var TEXT_MIME = 'text/plain';
function getFolder_(ctx, create) {
  var q = "mimeType='" + FOLDER_MIME + "' and name='" + FOLDER_NAME + "' and trashed=false";
  ctx.drive_ops++;
  var r = Drive.Files.list({ q: q, fields: 'files(id,name)', pageSize: 10 });
  var f = r.files || [];
  if (f.length > 1) { throw new Error('REFUSED: ' + f.length + ' folders named ' + FOLDER_NAME); }
  if (f.length === 1) { return f[0].id; }
  if (!create) { return null; }
  ctx.drive_ops++;
  return Drive.Files.create({ name: FOLDER_NAME, mimeType: FOLDER_MIME }).id;
}
function findFile_(folderId, name, ctx) {
  var q = "name='" + name + "' and '" + folderId + "' in parents and trashed=false";
  ctx.drive_ops++;
  var r = Drive.Files.list({ q: q, fields: 'files(id,name,parents)', pageSize: 20 });
  var out = r.files || [];
  out.forEach(function (f) {
    if (!f.parents || f.parents.indexOf(folderId) < 0) { throw new Error('REFUSED: file outside our folder: ' + f.id); }
  });
  if (out.length > 1) { throw new Error('REFUSED: ' + out.length + ' files named ' + name); }
  return out.length ? out[0] : null;
}
function createInFolder_(folderId, name, text, ctx) {
  ctx.drive_ops++;
  return Drive.Files.create({ name: name, parents: [folderId], mimeType: TEXT_MIME }, Utilities.newBlob(text, TEXT_MIME, name));
}
function writeText_(file, text, ctx) {
  ctx.drive_ops++;
  return Drive.Files.update({}, file.id, Utilities.newBlob(text, TEXT_MIME, file.name));
}
function decodeRead_(out) {
  if (typeof out === 'string') { return out; }
  if (out && typeof out.getDataAsString === 'function') { return out.getDataAsString(); }
  var isArr = Array.isArray(out) || (out && typeof out === 'object' && typeof out.length === 'number' && typeof out.byteLength !== 'function' &&
    (out.length === 0 || typeof out[0] === 'number') && Object.prototype.toString.call(out) !== '[object Object]');
  if (isArr) { return Utilities.newBlob(Array.prototype.slice.call(out)).getDataAsString(); }
  var ptag = Object.prototype.toString.call(out);
  if (ptag === '[object Object]' || ptag === '[object Array]') { return JSON.stringify(out); }
  throw new Error('unexpected Drive read result: type=' + typeof out + ' tag=' + Object.prototype.toString.call(out) +
    ' keys=' + (out && typeof out === 'object' ? JSON.stringify(Object.keys(out).slice(0, 5)) : 'n/a'));
}
// The Advanced Drive service JSON-parses media responses. Valid JSON comes back as an object (decodeRead_ re-serialises
// it); anything else (e.g. an old multi-line moves-*.jsonl) makes it throw HttpResponseException "Response Code: 200.
// Message: <the file body>". That throw is a successful read, so the body is recovered from the message.
function bodyFromHttp200_(e) {
  var m = String(e && e.message !== undefined ? e.message : e);
  var i = m.indexOf('Response Code: 200');
  if (i < 0) { return null; }
  var j = m.indexOf('Message: ', i);
  return j < 0 ? null : m.slice(j + 9);
}
function readText_(file, ctx) {
  ctx.drive_ops++;
  var out;
  try { out = Drive.Files.get(file.id, { alt: 'media' }); }
  catch (e) {
    var body = bodyFromHttp200_(e);
    if (body === null) { throw e; }
    return body;
  }
  return decodeRead_(out);
}

// Canonical JSON: recursively sorted keys, no whitespace. Same parsed content gives the same string.
function canon_(v) {
  if (v === null || typeof v !== 'object') { return JSON.stringify(v); }
  if (Array.isArray(v)) { return '[' + v.map(canon_).join(',') + ']'; }
  return '{' + Object.keys(v).sort().map(function (k) { return JSON.stringify(k) + ':' + canon_(v[k]); }).join(',') + '}';
}

function sha256Hex_(s) {
  var d = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, s, Utilities.Charset.UTF_8);
  return d.map(function (b) { b = b < 0 ? b + 256 : b; return (b < 16 ? '0' : '') + b.toString(16); }).join('');
}

function isProcessed_(ctx, key) { var l = pjson_(ctx, 'PROCESSED') || []; return l.indexOf(key) >= 0; }
function markProcessed_(ctx, key) {
  var l = pjson_(ctx, 'PROCESSED') || [];
  if (l.indexOf(key) < 0) { l.push(key); }
  pset_(ctx, 'PROCESSED', JSON.stringify(l.slice(-KEEP_PROCESSED)));
}

// ---------- schema (mirror of mover_schema.py) ----------
function validate_(req) {
  var errs = [], i, k;
  if (req === null || typeof req !== 'object' || Array.isArray(req)) { return ['request must be a JSON object']; }
  for (k in req) { if (REQUEST_KEYS.indexOf(k) < 0) { errs.push('unknown request field: ' + k); } }
  REQUEST_KEYS.forEach(function (key) { if (!(key in req)) { errs.push('missing request field: ' + key); } });
  if ('request_id' in req && !(typeof req.request_id === 'string' && REQUEST_ID_RE.test(req.request_id))) { errs.push('bad request_id'); }
  if ('created_at' in req && !(typeof req.created_at === 'string' && CREATED_AT_RE.test(req.created_at))) { errs.push('bad created_at'); }
  if (!('actions' in req)) { return errs; }
  var acts = req.actions;
  if (!Array.isArray(acts) || !acts.length) { return errs.concat(['actions must be a non-empty list']); }
  if (acts.length > MAX_ACTIONS_PER_REQUEST) { errs.push('too many actions'); }
  var total = 0, trashTotal = 0;
  for (i = 0; i < acts.length; i++) {
    var a = acts[i], p = 'actions[' + i + ']';
    if (a === null || typeof a !== 'object' || Array.isArray(a)) { errs.push(p + ' must be an object'); continue; }
    for (k in a) { if (ACTION_KEYS.indexOf(k) < 0) { errs.push(p + ' unknown field: ' + k); } }
    var op = a.op;
    if (!(typeof op === 'string' && ALLOWED_OPS.indexOf(op) >= 0)) { errs.push(p + ' unknown op'); continue; }
    if (LABELLESS_OPS.indexOf(op) >= 0) {
      if ('label' in a) { errs.push(p + ' ' + op + ' takes no label'); }
    } else {
      var lab = a.label;
      if (typeof lab !== 'string' || !lab || lab.length > LABEL_MAX_LEN || lab !== lab.trim() || /[\x00-\x1f]/.test(lab)) {
        errs.push(p + ' bad label');
      } else if (SYSTEM_LABELS.indexOf(lab.toUpperCase()) >= 0 && !(op === 'addLabel' && lab === 'INBOX')) {
        errs.push(p + ' system label not allowed');
      }
    }
    var ids = a.ids;
    if (!Array.isArray(ids) || !ids.length) { errs.push(p + ' ids must be a non-empty list'); continue; }
    var bad = false, seen = {}, dup = false;
    ids.forEach(function (x) {
      if (!(typeof x === 'string' && MSG_ID_RE.test(x))) { bad = true; } else { if (seen[x]) { dup = true; } seen[x] = 1; }
    });
    if (bad) { errs.push(p + ' bad message id'); }
    if (dup) { errs.push(p + ' duplicate ids'); }
    total += ids.length;
    if (op === 'trash') { trashTotal += ids.length; }
  }
  if (trashTotal > MAX_TRASH_IDS_PER_REQUEST) { errs.push('too many trash ids in request (cap ' + MAX_TRASH_IDS_PER_REQUEST + ')'); }
  if (total > MAX_IDS_PER_REQUEST) { errs.push('too many ids in request (cap ' + MAX_IDS_PER_REQUEST + ')'); }
  return errs;
}

function inverse_(a) {
  if (a.op === 'addLabel') { return { op: 'removeLabel', label: a.label, ids: a.ids.slice() }; }
  if (a.op === 'removeLabel') { return { op: 'addLabel', label: a.label, ids: a.ids.slice() }; }
  if (a.op === 'trash') { return { op: 'untrash', ids: a.ids.slice() }; }
  if (a.op === 'untrash') { return { op: 'trash', ids: a.ids.slice() }; }
  return { op: 'addLabel', label: 'INBOX', ids: a.ids.slice() };
}

// ---------- the run ----------
function runInner_(S) {
  var ctx = S.ctx;
  var folder = getFolder_(ctx, false);
  if (!folder) { Logger.log('not set up: no folder'); return 'not_set_up'; }
  var reqFile = findFile_(folder, REQUEST_NAME, ctx);
  S.resFile = findFile_(folder, RESULT_NAME, ctx);
  if (!reqFile || !S.resFile) { Logger.log('not set up: files missing'); return 'not_set_up'; }
  S.folder = folder;
  var txt = readText_(S.resFile, ctx), res = null;
  try { res = JSON.parse(txt); } catch (e) { res = null; }
  S.result = (res && typeof res === 'object') ? res : {};
  S.result.schema = 1;
  if (!Array.isArray(S.result.usage)) { S.result.usage = []; }

  var raw = readText_(reqFile, ctx);
  var cursor = pjson_(ctx, 'CURSOR');
  // "Changed" is judged on the PARSED request (canonical form), never the raw bytes: Drive may hand back the same
  // file as text, bytes or an already-parsed object, with any whitespace/key order, and the bytes are not stable.
  var req, parsed = true;
  try { req = JSON.parse(raw); } catch (e) { parsed = false; }
  var h = parsed ? sha256Hex_(canon_(req)) : sha256Hex_(raw);
  if (cursor && (!parsed || cursor.hash !== h)) {
    S.result.request_id = cursor.request_id; S.result.status = 'aborted_request_changed';
    S.result.reason = 'request.json changed while a request was in progress'; S.result.finished_at = nowIso_();
    markProcessed_(ctx, cursor.request_id); pdel_(ctx, 'CURSOR'); cursor = null;
  }
  if (!cursor && raw.replace(/\s/g, '') === '') { return 'idle'; }
  if (!parsed) { return badJson_(S, h); }
  var key = (req && typeof req.request_id === 'string' && REQUEST_ID_RE.test(req.request_id)) ? req.request_id : 'hash:' + h;
  if (!cursor && isProcessed_(ctx, key)) { return 'idle'; }

  if (!cursor) {
    var errs = validate_(req);
    if (errs.length) { return refuse_(S, key, errs); }
  }
  // resolve labels by name (Labels.list is the only label call); whole request refused if any is missing
  var needLabels = req.actions.some(function (a) { return LABELLESS_OPS.indexOf(a.op) < 0 && a.label !== 'INBOX'; });
  var byName = {};
  if (needLabels) {
    var ll = gm_(ctx, function () { return Gmail.Users.Labels.list('me'); });
    (ll.labels || []).forEach(function (l) { byName[l.name] = l; });
  }
  var ids = [];
  for (var i = 0; i < req.actions.length; i++) {
    var a = req.actions[i];
    if (LABELLESS_OPS.indexOf(a.op) >= 0) { ids.push(null); continue; }
    if (a.label === 'INBOX') { ids.push('INBOX'); continue; }
    var l = byName[a.label];
    if (!l || l.type !== 'user') {
      var msg = 'label not found (or not a user label): ' + a.label;
      return cursor ? abort_(S, cursor, 'aborted_label_missing', msg) : refuse_(S, key, [msg]);
    }
    ids.push(l.id);
  }
  return apply_(S, req, key, h, cursor, ids);
}

function gm_(ctx, fn) { ctx.gmail_calls++; return fn(); }

function badJson_(S, h) {
  var ctx = S.ctx;
  if (pget_(ctx, 'BAD_HASH') !== h) { pset_(ctx, 'BAD_HASH', h); return 'unreadable_wait'; }   // maybe a half-written file
  if (pget_(ctx, 'REFUSED_BAD') === h) { return 'idle'; }
  pset_(ctx, 'REFUSED_BAD', h);
  S.result.request_id = null; S.result.status = 'refused'; S.result.errors = ['request.json is not valid JSON'];
  S.result.actions = []; S.result.finished_at = nowIso_();
  return 'refused';
}

function refuse_(S, key, errs) {
  S.result.request_id = key; S.result.status = 'refused'; S.result.errors = errs;
  S.result.actions = []; S.result.finished_at = nowIso_();
  markProcessed_(S.ctx, key);
  return 'refused';
}

function abort_(S, cursor, status, reason) {
  S.result.request_id = cursor.request_id; S.result.status = status; S.result.reason = reason;
  S.result.finished_at = nowIso_();
  markProcessed_(S.ctx, cursor.request_id); pdel_(S.ctx, 'CURSOR');
  return status;
}

function bodyFor_(a, labelId, chunk) {
  if (a.op === 'archive') { return { ids: chunk, removeLabelIds: ['INBOX'] }; }
  if (a.op === 'trash') { return { ids: chunk, addLabelIds: ['TRASH'] }; }
  if (a.op === 'untrash') { return { ids: chunk, removeLabelIds: ['TRASH'] }; }
  if (a.op === 'addLabel') { return { ids: chunk, addLabelIds: [labelId] }; }
  return { ids: chunk, removeLabelIds: [labelId] };
}

function apply_(S, req, key, h, cursor, labelIds) {
  var ctx = S.ctx, i, j;
  S.key = key;
  var batches = [];   // flat, deterministic order
  for (i = 0; i < req.actions.length; i++) {
    for (j = 0; j < req.actions[i].ids.length; j += BATCH_SIZE) { batches.push({ a: i, from: j }); }
  }
  if (!cursor) {
    cursor = { request_id: key, hash: h, next: 0, fails: 0, done: req.actions.map(function () { return 0; }),
               received_at: nowIso_() };
  }
  var calls = 0, lastErr = null;
  while (cursor.next < batches.length && calls < MAX_BATCH_CALLS_PER_RUN && (Date.now() - S.t0) < RUN_TIME_BUDGET_MS) {
    var b = batches[cursor.next], act = req.actions[b.a];
    var chunk = act.ids.slice(b.from, b.from + BATCH_SIZE);
    try {
      gm_(ctx, function () { return Gmail.Users.Messages.batchModify(bodyFor_(act, labelIds[b.a], chunk), 'me'); });
    } catch (e) {
      lastErr = String(e); cursor.fails++;
      noteError_(S, key, cursor.next, lastErr);
      break;
    }
    calls++; cursor.fails = 0;
    ctx.ids_modified += chunk.length;
    cursor.done[b.a] += chunk.length;
    cursor.next++;
    // Progress is saved FIRST: the mail has moved, so nothing after this may lose the fact. (Before, an exception in
    // logMove_ escaped apply_ and ended the run silently with the cursor one batch behind.)
    pset_(ctx, 'CURSOR', JSON.stringify(cursor));
    try { logMove_(S, key, cursor.next - 1, b.a, act, chunk); }
    catch (e3) { noteError_(S, key, cursor.next - 1, 'move log write failed: ' + e3); }
  }
  var finished = cursor.next >= batches.length;
  S.result.request_id = key;
  S.result.received_at = cursor.received_at;
  S.result.actions = req.actions.map(function (a, k) {
    var o = { op: a.op, count: cursor.done[k], requested: a.ids.length, ids_hash: sha256Hex_(a.ids.slice().sort().join(',')) };
    if (LABELLESS_OPS.indexOf(a.op) < 0) { o.label = a.label; }
    return o;
  });
  S.result.undo_log = 'move-' + key + '-b*.json';
  delete S.result.errors; delete S.result.reason;
  if (finished) {
    S.result.status = 'done'; S.result.finished_at = nowIso_();
    markProcessed_(ctx, key); pdel_(ctx, 'CURSOR');
    return 'done';
  }
  if (lastErr) {
    S.result.last_error = lastErr;
    if (cursor.fails >= MAX_FAILED_RUNS) {
      S.result.status = 'failed'; S.result.reason = 'batch failed ' + cursor.fails + ' runs in a row: ' + lastErr;
      S.result.finished_at = nowIso_();
      markProcessed_(ctx, key); pdel_(ctx, 'CURSOR');
      return 'failed';
    }
  }
  S.result.status = 'in_progress';
  pset_(ctx, 'CURSOR', JSON.stringify(cursor));
  return 'in_progress';
}

var ERRORS_KEEP = 20;
// Bounded history of errors in result.json (last_error is kept too, for compatibility).
function noteError_(S, requestId, batchIdx, msg) {
  if (!S.result) { return; }
  if (!Array.isArray(S.result.errors_history)) { S.result.errors_history = []; }
  S.result.errors_history.push({ ts: nowIso_(), request_id: requestId, batch: batchIdx, error: String(msg).slice(0, 500) });
  S.result.errors_history = S.result.errors_history.slice(-ERRORS_KEEP);
  S.result.last_error = String(msg).slice(0, 500);
}

// Move log: ONE SMALL FILE PER BATCH (move-<request_id>-b<NNNN>.json), each a single valid JSON object. Nothing is
// ever read back or appended, so the Drive service's JSON-parsing of media can never break logging. Re-running a batch
// finds its file by name and leaves it alone.
function moveLogName_(key, batchIdx) { return 'move-' + key + '-b' + ('0000' + batchIdx).slice(-4) + '.json'; }

function logMove_(S, key, batchIdx, idx, act, chunk) {
  var ctx = S.ctx, name = moveLogName_(key, batchIdx);
  if (findFile_(S.folder, name, ctx)) { return; }
  var doc = JSON.stringify({ ts: nowIso_(), request_id: key, batch: batchIdx, action: idx, op: act.op, label: act.label || null,
                             count: chunk.length, undo: inverse_({ op: act.op, label: act.label, ids: chunk }) });
  createInFolder_(S.folder, name, doc, ctx);
}

function finish_(S) {
  if (!S.result || !S.resFile) { return; }
  var ctx = S.ctx;
  var cutoff = Date.now() - USAGE_KEEP_DAYS * 86400000;
  S.result.usage = S.result.usage.filter(function (u) { return Date.parse(u.ts) >= cutoff; });
  ctx.drive_ops++;   // the write below, counted before the usage row records it
  S.result.usage.push({ ts: nowIso_(), runtime_ms: Date.now() - S.t0, gmail_calls: ctx.gmail_calls,
                        ids_modified: ctx.ids_modified, drive_ops: ctx.drive_ops, properties_ops: ctx.properties_ops });
  S.result.updated_at = nowIso_();
  writeText_(S.resFile, JSON.stringify(S.result), { drive_ops: 0 });   // already counted above
}
