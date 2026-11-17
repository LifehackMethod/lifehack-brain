// origin: 92a9739:mover/tests/harness.js
// node harness.js <Code.gs> <spec.json>  -> prints JSON. Runs the .gs in a vm with a pretend Gmail + Advanced Drive v3 (Drive.Files.*). No network.
const vm = require('vm'), fs = require('fs'), crypto = require('crypto');
const [,, codePath, specPath] = process.argv;
const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
const clock = { t: Date.parse(spec.clock_start || '2026-11-12T12:00:00Z'), perCall: spec.per_call_ms || 0 };
class FakeDate extends Date {
  constructor(...a) { if (a.length) super(...a); else super(clock.t); }
  static now() { return clock.t; }
}
let labels = (spec.labels || []).map(x => ({ ...x }));
const messages = {}; for (const [id, ls] of Object.entries(spec.messages || {})) messages[id] = new Set(ls);
const calls = [], props = {}, triggers = []; let failNext = 0, nextId = 1, readMode = spec.read_mode || 'live', driveFail = null;
const folders = [];   // {name, id, files:[{id,name,content}]}
const mkfile = (folder, name, content) => { const f = { id: 'f' + (nextId++), name, content }; folder.files.push(f); return f; };
const FOLDER_MIME = 'application/vnd.google-apps.folder';
const txt = b => (b && b.__blob) ? b.data : '';
const meta = f => ({ id: f.id, name: f.name, parents: f.parent ? [f.parent] : undefined });
const allFiles = () => folders.flatMap(fo => fo.files);
const driveApi = { Files: {
  list: (o) => { const q = o.q || ''; const nm = /name='([^']*)'/.exec(q)[1];
    if (q.includes(FOLDER_MIME)) return { files: folders.filter(f => f.name === nm).map(f => ({ id: f.id, name: f.name })) };
    const pm = /'([^']*)' in parents/.exec(q); if (!pm) throw new Error('unconfined file query (fake)');
    return { files: allFiles().filter(f => f.name === nm && f.parent === pm[1]).map(meta) }; },
  create: (res, blob) => {
    if (driveFail && driveFail.times > 0 && String(res.name).startsWith(driveFail.prefix)) { driveFail.times--; throw new Error('Drive write failed (fake)'); }
    if (res.mimeType === FOLDER_MIME) { const fo = { id: 'd' + (nextId++), name: res.name, files: [] }; folders.push(fo); return { id: fo.id, name: fo.name }; }
    const fo = folders.find(x => x.id === (res.parents || [])[0]); if (!fo) throw new Error('no such parent (fake)');
    const f = mkfile(fo, res.name, txt(blob)); f.parent = fo.id; return meta(f); },
  update: (res, id, blob) => { const f0 = allFiles().find(x => x.id === id);
    if (driveFail && driveFail.times > 0 && f0 && f0.name.startsWith(driveFail.prefix)) { driveFail.times--; throw new Error('Drive write failed (fake)'); }
    const f = allFiles().find(x => x.id === id); if (!f) throw new Error('404 (fake)'); f.content = txt(blob); return meta(f); },
  get: (id, opt) => { const f = allFiles().find(x => x.id === id); if (!f) throw new Error('404 (fake)');
    if (!opt || opt.alt !== 'media') throw new Error('metadata get not modelled');
    const m = readMode, c = f.content;
    if (m === 'blob') return { getDataAsString: () => c };
    if (m === 'bytes') return Array.from(Buffer.from(c, 'utf8')).map(b => b > 127 ? b - 256 : b);
    if (m === 'parsed') return JSON.parse(c);
    if (m === 'live') {   // what the real Advanced Drive service does: JSON-parse media; non-JSON throws with code 200
      if (c === '') return '';
      try { return JSON.parse(c); } catch (e) { throw new Error('HttpResponseException: Response Code: 200. Message: ' + c); } }
    if (m === 'weird') return 42;
    return c; },
} };
const sandbox = {
  Logger: { log: m => { (sandbox.__log = sandbox.__log || []).push(String(m)); } }, Date: FakeDate, JSON, Math, Array, Object, String, RegExp, Error,
  Utilities: { newBlob: (data, mime, name) => ({ __blob: true, data, mime, name, getDataAsString: () => Array.isArray(data) ? Buffer.from(data.map(b => b & 255)).toString('utf8') : data }), DigestAlgorithm: { SHA_256: 'sha256' }, Charset: { UTF_8: 'utf8' },
    computeDigest: (a, s) => Array.from(crypto.createHash('sha256').update(s, 'utf8').digest()).map(b => b > 127 ? b - 256 : b) },
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => (k in props ? props[k] : null), setProperty: (k, v) => { props[k] = String(v); },
    deleteProperty: k => { delete props[k]; } }) },
  Drive: driveApi,
  ScriptApp: { getProjectTriggers: () => triggers.map(t => ({ getHandlerFunction: () => t.fn, _t: t })),
    deleteTrigger: t => { triggers.splice(triggers.indexOf(t._t), 1); },
    newTrigger: fn => ({ timeBased: () => ({ everyMinutes: n => ({ create: () => { triggers.push({ fn, minutes: n }); } }) }) }) },
  Gmail: { Users: {
    Labels: { list: u => { clock.t += clock.perCall; calls.push({ fn: 'Labels.list', u }); return { labels: labels.map(x => ({ ...x })) }; } },
    Messages: { batchModify: (body, u) => {
      clock.t += clock.perCall; calls.push({ fn: 'batchModify', body: JSON.parse(JSON.stringify(body)), u });
      if (failNext > 0) { failNext--; throw new Error('Gmail quota exceeded (fake)'); }
      if (body.ids.length > 1000) throw new Error('too many ids');
      for (const id of body.ids) { const s = messages[id]; if (!s) continue;
        (body.addLabelIds || []).forEach(l => s.add(l)); (body.removeLabelIds || []).forEach(l => s.delete(l)); } } } } },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(codePath, 'utf8'), sandbox);
for (const [k, v] of Object.entries(spec.constants || {})) vm.runInContext(k + '=' + JSON.stringify(v), sandbox);
const findFile = n => { const fo = folders[0]; return fo && fo.files.find(f => f.name === n); };
const results = [], snaps = {};
const snap = () => Object.fromEntries(Object.entries(messages).map(([k, s]) => [k, [...s].sort()]));
for (const st of spec.steps) {
  if (st.call) { let r; try { r = vm.runInContext(st.call + '(' + (st.args || []).map(a => JSON.stringify(a)).join(',') + ')', sandbox); }
    catch (e) { r = 'THROW ' + e; } results.push(r === undefined ? null : r); }
  else if (st.mac_write) { const f = findFile(st.mac_write.name); f.content = st.mac_write.content; }   // in place: same id
  else if (st.seed_file) { const fo = folders[0]; const f = mkfile(fo, st.seed_file.name, st.seed_file.content); f.parent = fo.id; }
  else if (st.prop) Object.assign(props, st.prop);
  else if (st.read_mode) readMode = st.read_mode;
  else if (st.drive_fail) driveFail = { ...st.drive_fail };
  else if (st.advance) clock.t += st.advance;
  else if (st.per_call_ms !== undefined) clock.perCall = st.per_call_ms;
  else if (st.gmail_fail) failNext = st.gmail_fail;
  else if (st.add_label) labels.push(st.add_label);
  else if (st.snapshot) snaps[st.snapshot] = snap();
}
const files = {}; for (const fo of folders) for (const f of fo.files) files[f.name] = { id: f.id, content: f.content };
console.log(JSON.stringify({ results, messages: snap(), calls, files, props, triggers, snaps, log: sandbox.__log || [], folders: folders.length }));
