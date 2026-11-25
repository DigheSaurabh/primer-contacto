/**
 * Primer Contacto: one-link web app for teachers (Google Apps Script).
 *
 * Lives in the SAME Apps Script project as setup_intake.gs (Code.gs) and uses its constants and
 * helpers (COLUMNS, CHOICES, STAGES, sheet_, nextId_, parseDateTime_, ...). It writes to the same
 * Requests tab with the same columns, so the forms stay a working backup and the Python pipeline
 * reads app data unchanged.
 *
 * Each teacher opens their own link: <web app URL>?t=<private code>. The code is looked up in the
 * private "Teachers" tab; a teacher only ever sees and changes their own requests.
 *
 * One-time setup (after setup() has created the sheet and forms):
 *   1. Run setupTeachers()      -> creates the Teachers tab with T1-T4 and private codes
 *   2. Deploy > New deployment > Web app: Execute as "Me", Who has access "Anyone"
 *   3. Run showTeacherLinks()   -> prints each teacher's personal link
 * Steps with screenshots-level detail: docs/tutorial.md
 */

const WEB = {
  teachersTab: 'Teachers',
  updatesTab: 'Updates',             // one row per change, so any update can be undone
  replyOverdueDays: 7,
  quoteFollowUpDays: 3,
};
const TEACHER_COLUMNS = ['teacher_id', 'name', 'code', 'active'];
const UPDATE_COLUMNS = ['at', 'teacher_id', 'request_id', 'action', 'detail', 'before_json'];

// ---------------------------------------------------------------- page

function doGet(e) {
  const code = String((e && e.parameter && e.parameter.t) || '').trim();
  const teacher = teacherByCode_(code);
  const tpl = HtmlService.createTemplateFromFile('Index');
  tpl.code = teacher ? code : '';
  tpl.teacherName = teacher ? teacher.name : '';
  return tpl.evaluate()
    .setTitle('Primer Contacto')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/** Everything the page needs for one teacher: their requests and the choice lists. */
function getState(code) {
  const teacher = requireTeacher_(code);
  const rows = readRequests_().filter(r => r.teacher_id === teacher.id);
  const undoable = lastUpdates_(teacher.id);
  const now = new Date();
  return {
    teacher: { id: teacher.id, name: teacher.name },
    now: iso_(now),
    choices: webChoices_(),
    requests: rows
      .sort((a, b) => b.received_at - a.received_at)
      .map(r => toClient_(r, now, undoable[r.request_id])),
  };
}

// ---------------------------------------------------------------- actions (called from the page)

/** New request. Same fields and reply rule as Form A. */
function addRequest(code, form) {
  const teacher = requireTeacher_(code);
  return withLock_(() => {
    const now = new Date();
    const received = parseDateTime_(form.received_at) || now;
    if (received > now) throw new Error('future_date');
    const channel = pick_('channel', form.channel);
    const repliedAt = replyTimeFromFormA_(pick_('replied', form.replied) || 'not_yet',
      parseDateTime_(form.replied_at), channel, received, now);
    const zip = String(form.event_zip || '').trim();
    if (zip && !/^\d{5}$/.test(zip)) throw new Error('bad_zip');
    const sheet = sheet_();
    const row = {
      request_id: nextId_(sheet, received),
      teacher_id: teacher.id,
      received_at: received,
      channel: channel,
      request_type: pick_('request_type', form.request_type),
      language: pick_('language', form.language),
      client_type: pick_('client_type', form.client_type),
      event_zip: zip,
      replied_at: repliedAt || '',
      quoted_amount: amount_(form.quoted_amount),
      note: String(form.note || '').slice(0, 500),
      outcome: 'open',
      last_stage: repliedAt ? 'replied' : 'received',
      logged_at: now,
    };
    if (!row.channel || !row.request_type || !row.language || !row.client_type) throw new Error('missing_field');
    sheet.appendRow(COLUMNS.map(c => (c in row ? row[c] : '')));
    logUpdate_(teacher.id, row.request_id, 'new', 'received', null);
    refreshFormsQuietly_();
    return { saved: row.request_id, state: getState(code) };
  });
}

/** Stage change. Same rules as Form B: only the chosen stage gets a date; nothing is back-filled. */
function updateStage(code, requestId, stage, when, lostReason, quotedAmount) {
  const teacher = requireTeacher_(code);
  return withLock_(() => {
    const found = findRequest_(requestId, teacher.id);
    const r = found.record;
    const before = JSON.stringify(found.values);
    stage = pick_('stage', stage);
    if (!stage) throw new Error('missing_field');
    const now = new Date();
    const at = parseDateTime_(when) || now;
    if (at > now) throw new Error('future_date');
    if (at < r.received_at) throw new Error('before_received');
    const amt = amount_(quotedAmount);
    if (amt !== '') r.quoted_amount = amt;

    if (stage === 'lost') {
      r.lost_at = at;
      r.lost_reason = pick_('lost_reason', lostReason) || 'other';
      r.outcome = 'lost';
    } else {
      r[stage + '_at'] = at;
      if (STAGES.indexOf(stage) > STAGES.indexOf(r.last_stage)) r.last_stage = stage;
      if (r.delivered_at && r.paid_at && r.outcome !== 'lost') r.outcome = 'delivered_paid';
    }
    found.range.setValues([COLUMNS.map(c => r[c])]);
    logUpdate_(teacher.id, requestId, 'stage', stage, before);
    refreshFormsQuietly_();
    return { saved: requestId, stage: stage, state: getState(code) };
  });
}

/** Puts a request back exactly as it was before its last change made in the app. */
function undoLast(code, requestId) {
  const teacher = requireTeacher_(code);
  return withLock_(() => {
    const log = updatesSheet_();
    const data = log.getDataRange().getValues();
    for (let i = data.length - 1; i >= 1; i--) {
      const [, tid, rid, action, , beforeJson] = data[i];
      if (tid !== teacher.id || rid !== requestId) continue;
      if (action !== 'stage' || !beforeJson) throw new Error('nothing_to_undo');
      const found = findRequest_(requestId, teacher.id);
      const before = JSON.parse(beforeJson).map((v, j) =>
        isDateColumn_(COLUMNS[j]) && v ? new Date(v) : v);
      found.range.setValues([before]);
      log.getRange(i + 1, 4).setValue('undone');
      refreshFormsQuietly_();
      return { undone: requestId, state: getState(code) };
    }
    throw new Error('nothing_to_undo');
  });
}

// ---------------------------------------------------------------- teachers and links

/** Creates the private Teachers tab from CONFIG.teachers, with a random code for each. Safe to re-run. */
function setupTeachers() {
  const ss = SpreadsheetApp.openById(PropertiesService.getScriptProperties().getProperty('SHEET_ID'));
  let tab = ss.getSheetByName(WEB.teachersTab);
  if (!tab) {
    tab = ss.insertSheet(WEB.teachersTab);
    tab.getRange(1, 1, 1, TEACHER_COLUMNS.length).setValues([TEACHER_COLUMNS]).setFontWeight('bold');
    tab.setFrozenRows(1);
  }
  const have = new Set(tab.getDataRange().getValues().slice(1).map(r => r[0]));
  CONFIG.teachers.forEach(([id, name]) => {
    if (!have.has(id)) tab.appendRow([id, name, newCode_(), true]);
  });
  updatesSheet_();
  Logger.log('Teachers tab ready. Add a teacher by adding a row (code: run newLinkFor("T5")).');
}

/** Prints every active teacher's personal link. Deploy the web app first. */
function showTeacherLinks() {
  // Run from the editor, getUrl() can return the /dev test address, which only works for you.
  // Teachers need the /exec address of the deployed app.
  const raw = ScriptApp.getService().getUrl();
  if (!raw) throw new Error('Deploy the web app first: Deploy > New deployment > Web app.');
  const url = raw.replace(/\/dev$/, '/exec');
  teachers_().filter(t => t.active).forEach(t => Logger.log(`${t.id}  ${t.name}:  ${url}?t=${t.code}`));
}

/** Gives one teacher a new private code (use it if a link was shared by mistake). The old link stops working. */
function newLinkFor(teacherId) {
  const tab = teachersSheet_();
  const data = tab.getDataRange().getValues();
  const i = data.findIndex((r, n) => n > 0 && r[0] === teacherId);
  if (i === -1) {
    tab.appendRow([teacherId, teacherId, newCode_(), true]);
  } else {
    tab.getRange(i + 1, 3).setValue(newCode_());
  }
  showTeacherLinks();
}

// ---------------------------------------------------------------- helpers

function teachersSheet_() {
  const ss = SpreadsheetApp.openById(PropertiesService.getScriptProperties().getProperty('SHEET_ID'));
  const tab = ss.getSheetByName(WEB.teachersTab);
  if (!tab) throw new Error('Run setupTeachers() first.');
  return tab;
}

function updatesSheet_() {
  const ss = SpreadsheetApp.openById(PropertiesService.getScriptProperties().getProperty('SHEET_ID'));
  let tab = ss.getSheetByName(WEB.updatesTab);
  if (!tab) {
    tab = ss.insertSheet(WEB.updatesTab);
    tab.getRange(1, 1, 1, UPDATE_COLUMNS.length).setValues([UPDATE_COLUMNS]).setFontWeight('bold');
    tab.setFrozenRows(1);
  }
  return tab;
}

function teachers_() {
  return teachersSheet_().getDataRange().getValues().slice(1)
    .filter(r => r[0])
    .map(r => ({ id: String(r[0]), name: String(r[1] || r[0]), code: String(r[2]), active: r[3] !== false }));
}

function teacherByCode_(code) {
  if (!code || code.length < 8) return null;
  return teachers_().find(t => t.active && t.code === code) || null;
}

function requireTeacher_(code) {
  const t = teacherByCode_(String(code || ''));
  if (!t) throw new Error('unknown_link');
  return t;
}

function newCode_() {
  return Utilities.getUuid().replace(/-/g, '').slice(0, 12);
}

function readRequests_() {
  return sheet_().getDataRange().getValues().slice(1).filter(v => v[0]).map(v => {
    const r = {};
    COLUMNS.forEach((c, i) => (r[c] = v[i]));
    return r;
  });
}

function findRequest_(requestId, teacherId) {
  const sheet = sheet_();
  const rowNum = findRow_(sheet, requestId);
  if (!rowNum) throw new Error('not_found');
  const range = sheet.getRange(rowNum, 1, 1, COLUMNS.length);
  const values = range.getValues()[0];
  const record = {};
  COLUMNS.forEach((c, i) => (record[c] = values[i]));
  if (record.teacher_id !== teacherId) throw new Error('not_found'); // never another teacher's request
  return { range: range, values: values.map(v => (v instanceof Date ? v.toISOString() : v)), record: record };
}

function lastUpdates_(teacherId) {
  const out = {};
  updatesSheet_().getDataRange().getValues().slice(1).forEach(([, tid, rid, action]) => {
    if (tid === teacherId) out[rid] = action === 'stage';
  });
  return out;
}

function logUpdate_(teacherId, requestId, action, detail, beforeJson) {
  updatesSheet_().appendRow([new Date(), teacherId, requestId, action, detail, beforeJson || '']);
}

/** Page labels: "English label / Spanish label" in CHOICES becomes {code, en, es}. */
function webChoices_() {
  const out = {};
  Object.keys(CHOICES).forEach(k => {
    out[k] = CHOICES[k].map(([code, label]) => {
      const [en, es] = label.split(' / ');
      return { code: code, en: en, es: es || en };
    });
  });
  return out;
}

function pick_(list, value) {
  return CHOICES[list].some(([c]) => c === value) ? value : '';
}

function amount_(v) {
  if (v === undefined || v === null || String(v).trim() === '') return '';
  const n = Number(v);
  if (!(n >= 0)) throw new Error('bad_amount');
  return n;
}

function isDateColumn_(c) { return /_at$/.test(c); }

function iso_(d) { return d instanceof Date ? d.toISOString() : ''; }

/** What the page shows for one request, including whether it needs attention and why. */
function toClient_(r, now, canUndo) {
  const days = at => (now - at) / 86400000;
  const done = r.outcome === 'lost' || r.outcome === 'delivered_paid';
  let attention = '';
  if (!done) {
    if (!(r.replied_at instanceof Date)) attention = 'no_reply';
    else if (r.quoted_at instanceof Date && !(r.confirmed_at instanceof Date)
      && days(r.quoted_at) > WEB.quoteFollowUpDays) attention = 'follow_up_quote';
    else if (days(r.received_at) > WEB.replyOverdueDays) attention = 'open_long';
  }
  const out = { attention: attention, done: done, can_undo: !!canUndo,
    age_days: Math.floor(days(r.received_at)) };
  ['request_id', 'channel', 'request_type', 'language', 'client_type', 'event_zip', 'lost_reason',
    'quoted_amount', 'note', 'outcome', 'last_stage'].forEach(c => (out[c] = r[c] === '' ? null : r[c]));
  COLUMNS.filter(isDateColumn_).forEach(c => (out[c] = iso_(r[c])));
  return out;
}

function withLock_(fn) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try { return fn(); } finally { lock.releaseLock(); }
}

/** Keeps the backup forms' request lists in step; never blocks a save if the forms are gone. */
function refreshFormsQuietly_() {
  try { refreshOpenRequests(); } catch (err) { Logger.log('Form refresh skipped: ' + err); }
}
