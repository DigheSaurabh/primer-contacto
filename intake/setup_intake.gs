/**
 * Primer Contacto: intake setup (Google Apps Script)
 *
 * Builds the two forms in docs/schema.md and one Google Sheet, shared by all pilot teachers:
 *   Form A  "New request / Nueva solicitud"         one per request, under 2 minutes
 *   Form B  "Stage update / Actualizar etapa"       one per movement, under 30 seconds
 *   Sheet   "Primer Contacto – Request Log"         tab "Requests": one row per request,
 *                                                   in the wide CSV format from docs/schema.md
 *
 * Each teacher picks their name first. The sheet stores only a code (T1, T2, ...).
 * In Form B each teacher is sent to their own section, which lists only their open requests.
 *
 * Privacy: no client names, handles, phone numbers, emails or street addresses are asked for.
 * Put the real teacher names in CONFIG.teachers in your Apps Script copy only; don't commit them.
 *
 * Setup and testing steps: docs/tutorial.md
 */

const CONFIG = {
  timeZone: 'America/Chicago',
  sheetName: 'Primer Contacto – Request Log',
  // [code stored in the sheet, name shown on the forms]. Edit names in Apps Script, not in GitHub.
  teachers: [
    ['T1', 'Teacher 1'],
    ['T2', 'Teacher 2'],
    ['T3', 'Teacher 3'],
    ['T4', 'Teacher 4'],
  ],
};

// Requests tab columns: the wide CSV format from docs/schema.md, then computed fields.
const COLUMNS = [
  'request_id', 'teacher_id', 'received_at', 'channel', 'request_type', 'language', 'client_type',
  'event_zip', 'replied_at', 'quoted_at', 'confirmed_at', 'delivered_at', 'invoiced_at', 'paid_at',
  'lost_at', 'lost_reason', 'quoted_amount', 'note',
  // computed by the script, not entered
  'outcome', 'last_stage', 'update_notes', 'logged_at',
];

const STAGES = ['received', 'replied', 'quoted', 'confirmed', 'delivered', 'invoiced', 'paid'];

// [stored code, label shown on the form]
const CHOICES = {
  channel: [
    ['instagram_dm', 'Instagram DM'],
    ['linktree_form', 'Linktree form / Formulario de Linktree'],
    ['text_message', 'Text message / Mensaje de texto'],
    ['email', 'Email / Correo electrónico'],
    ['phone_call', 'Phone call / Llamada'],
    ['in_person', 'In person / En persona'],
    ['referral', 'Referral / Recomendación'],
    ['other', 'Other / Otro'],
  ],
  request_type: [
    ['private_session', 'Private session / Sesión privada'],
    ['small_group', 'Small group / Grupo pequeño'],
    ['corporate_session', 'Corporate session / Sesión corporativa'],
    ['school_event', 'School event / Evento escolar'],
    ['community_event', 'Community event / Evento comunitario'],
    ['workshop', 'Workshop / Taller'],
    ['class_series', 'Class series / Serie de clases'],
    ['other', 'Other / Otro'],
  ],
  language: [
    ['en', 'English'],
    ['es', 'Español'],
    ['both', 'Both / Ambos'],
    ['other', 'Other / Otro'],
  ],
  client_type: [
    ['individual', 'Individual / Persona'],
    ['company', 'Company / Empresa'],
    ['school', 'School / Escuela'],
    ['nonprofit_community', 'Nonprofit or community organization / Organización comunitaria'],
    ['studio', 'Studio / Estudio'],
    ['other', 'Other / Otro'],
  ],
  stage: [
    ['replied', 'Replied / Respondí'],
    ['quoted', 'Quoted (price or proposal sent) / Cotizado'],
    ['confirmed', 'Confirmed (yes, date set) / Confirmado'],
    ['delivered', 'Delivered (it happened) / Realizado'],
    ['invoiced', 'Invoiced / Facturado'],
    ['paid', 'Paid / Pagado'],
    ['lost', 'Lost / Perdido'],
  ],
  lost_reason: [
    ['no_reply_from_client', 'No reply from client / El cliente no respondió'],
    ['declined_price', 'Declined price / Rechazó el precio'],
    ['scheduling_conflict', 'Scheduling conflict / Conflicto de horario'],
    ['went_elsewhere', 'Went elsewhere / Eligió otra opción'],
    ['cancelled', 'Cancelled / Cancelado'],
    ['other', 'Other / Otro'],
  ],
};

const NO_NAMES = 'No names, handles or phone numbers. / Sin nombres, usuarios ni teléfonos.';

// Question titles (also used to read answers back)
const Q = {
  teacher: 'Who are you? / ¿Quién eres?',
  received: 'When did the request arrive? / ¿Cuándo llegó la solicitud?',
  channel: 'Where did it come from? / ¿Por dónde llegó?',
  type: 'Request type / Tipo de solicitud',
  language: 'Language / Idioma',
  clientType: 'Client type / Tipo de cliente',
  zip: 'Event ZIP code (optional) / Código postal del evento (opcional)',
  amount: 'Quoted amount, USD (optional) / Monto cotizado, USD (opcional)',
  note: 'What did they ask for? (optional) / ¿Qué pidieron? (opcional)',
  request: 'Request ID / ID de la solicitud', // Form B: one per teacher, title + ' · ' + code
  stage: 'New stage / Nueva etapa',
  stageAt: 'When did it happen? / ¿Cuándo pasó?',
  lostReason: 'If lost: why? / Si se perdió: ¿por qué?',
  updateNote: 'Note (optional) / Nota (opcional)',
};

const NO_OPEN = 'No open requests yet / Aún no hay solicitudes abiertas';

// ---------------------------------------------------------------- setup

function setup() {
  const props = PropertiesService.getScriptProperties();
  if (props.getProperty('SHEET_ID')) {
    throw new Error('Already set up. Run showLinks() to see the links, or resetSetup() to start over.');
  }

  const ss = SpreadsheetApp.create(CONFIG.sheetName);
  ss.setSpreadsheetTimeZone(CONFIG.timeZone);
  const sheet = ss.getSheets()[0];
  sheet.setName('Requests');
  sheet.getRange(1, 1, 1, COLUMNS.length).setValues([COLUMNS]).setFontWeight('bold');
  sheet.setFrozenRows(1);
  sheet.setFrozenColumns(2);
  ['received_at', 'replied_at', 'quoted_at', 'confirmed_at', 'delivered_at', 'invoiced_at',
    'paid_at', 'lost_at', 'logged_at']
    .forEach(c => sheet.getRange(2, col_(c), 1000, 1).setNumberFormat('yyyy-mm-dd hh:mm'));
  sheet.getRange(2, col_('quoted_amount'), 1000, 1).setNumberFormat('$#,##0.00');
  sheet.getRange(2, col_('event_zip'), 1000, 1).setNumberFormat('@');

  const formA = buildFormA_();
  const formB = buildFormB_();
  formA.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  formB.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  ss.setActiveSheet(sheet);
  ss.moveActiveSheet(1);

  props.setProperties({ SHEET_ID: ss.getId(), FORM_A_ID: formA.getId(), FORM_B_ID: formB.getId() });
  ScriptApp.newTrigger('onNewRequest').forForm(formA).onFormSubmit().create();
  ScriptApp.newTrigger('onStageUpdate').forForm(formB).onFormSubmit().create();

  refreshOpenRequests();
  showLinks();
}

function buildFormA_() {
  const f = FormApp.create('Primer Contacto – New request / Nueva solicitud');
  f.setDescription('Log each request once, as soon as you can. Under 2 minutes.\n' +
    'Registra cada solicitud una vez, lo antes posible. Menos de 2 minutos.\n\n' + NO_NAMES);
  f.setConfirmationMessage('Saved. / Guardado.');
  f.setShowLinkToRespondAgain(true);

  f.addListItem().setTitle(Q.teacher).setChoiceValues(teacherNames_()).setRequired(true);
  f.addDateTimeItem().setTitle(Q.received).setRequired(true)
    .setHelpText('When it arrived, not when you are logging it. / Cuándo llegó, no cuándo la registras.');
  f.addListItem().setTitle(Q.channel).setChoiceValues(labels_('channel')).setRequired(true);
  f.addListItem().setTitle(Q.type).setChoiceValues(labels_('request_type')).setRequired(true);
  f.addMultipleChoiceItem().setTitle(Q.language).setChoiceValues(labels_('language')).setRequired(true);
  f.addListItem().setTitle(Q.clientType).setChoiceValues(labels_('client_type')).setRequired(true);
  f.addTextItem().setTitle(Q.zip)
    .setHelpText('Event ZIP only, never a street address. / Solo el código postal, nunca la dirección.')
    .setValidation(FormApp.createTextValidation()
      .requireTextMatchesPattern('^\\d{5}$')
      .setHelpText('5 digits. / 5 dígitos.')
      .build());
  f.addTextItem().setTitle(Q.amount)
    .setValidation(FormApp.createTextValidation()
      .requireNumberGreaterThanOrEqualTo(0)
      .setHelpText('Numbers only. / Solo números.')
      .build());
  f.addParagraphTextItem().setTitle(Q.note).setHelpText(NO_NAMES);
  return f;
}

/**
 * Form B layout:
 *   Section 1   "Who are you?"  (each name jumps to that teacher's section)
 *   Section T1  Request ID list with only T1's open requests
 *   Section T2  ...                                   (each teacher section then jumps to Details)
 *   Details     stage, date, lost reason, amount, note
 */
function buildFormB_() {
  const f = FormApp.create('Primer Contacto – Stage update / Actualizar etapa');
  f.setDescription('Use this each time a request moves. Under 30 seconds.\n' +
    'Úsalo cada vez que una solicitud avance. Menos de 30 segundos.');
  f.setConfirmationMessage('Updated. / Actualizado.');
  f.setShowLinkToRespondAgain(true);

  const who = f.addListItem().setTitle(Q.teacher).setRequired(true);

  const sections = CONFIG.teachers.map(([code, name]) => {
    const page = f.addPageBreakItem().setTitle(name);
    f.addListItem().setTitle(requestTitle_(code)).setChoiceValues([NO_OPEN]).setRequired(true)
      .setHelpText('Only your open requests, newest first. / Solo tus solicitudes abiertas.');
    return page;
  });

  const details = f.addPageBreakItem().setTitle('What happened? / ¿Qué pasó?');
  f.addListItem().setTitle(Q.stage).setChoiceValues(labels_('stage')).setRequired(true);
  f.addDateTimeItem().setTitle(Q.stageAt).setRequired(true);
  f.addListItem().setTitle(Q.lostReason).setChoiceValues(labels_('lost_reason'))
    .setHelpText('Only if the new stage is Lost. / Solo si la etapa es Perdido.');
  f.addTextItem().setTitle(Q.amount)
    .setHelpText('Only when you send a quote. / Solo al enviar una cotización.')
    .setValidation(FormApp.createTextValidation()
      .requireNumberGreaterThanOrEqualTo(0)
      .setHelpText('Numbers only. / Solo números.')
      .build());
  f.addParagraphTextItem().setTitle(Q.updateNote).setHelpText(NO_NAMES);

  // Name -> that teacher's section.
  who.setChoices(CONFIG.teachers.map(([, name], i) => who.createChoice(name, sections[i])));
  // After a teacher's section, skip the other teachers' sections and go to Details.
  // (A page break's "go to" applies to the section just before it.)
  sections.slice(1).forEach(page => page.setGoToPage(details));
  return f;
}

// ---------------------------------------------------------------- triggers

function onNewRequest(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const a = answers_(e.response);
    const now = e.response.getTimestamp();
    const received = parseDateTime_(a[Q.received]) || now;
    const amount = a[Q.amount];
    const sheet = sheet_();

    const row = {
      request_id: nextId_(sheet, received),
      teacher_id: teacherCode_(a[Q.teacher]),
      received_at: received,
      channel: code_('channel', a[Q.channel]),
      request_type: code_('request_type', a[Q.type]),
      language: code_('language', a[Q.language]),
      client_type: code_('client_type', a[Q.clientType]),
      event_zip: a[Q.zip] || '',
      quoted_amount: amount !== undefined && amount !== '' ? Number(amount) : '',
      note: a[Q.note] || '',
      outcome: 'open',
      last_stage: 'received',
      logged_at: now,
    };
    sheet.appendRow(COLUMNS.map(c => (c in row ? row[c] : '')));
    refreshOpenRequests();
  } finally {
    lock.releaseLock();
  }
}

function onStageUpdate(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const a = answers_(e.response);
    const teacher = teacherCode_(a[Q.teacher]);
    const picked = a[requestTitle_(teacher)];
    const id = String(picked || '').split(' · ')[0];
    const sheet = sheet_();
    const rowNum = findRow_(sheet, id);
    if (!rowNum) return; // placeholder or unknown ID

    const range = sheet.getRange(rowNum, 1, 1, COLUMNS.length);
    const values = range.getValues()[0];
    const r = {};
    COLUMNS.forEach((c, i) => (r[c] = values[i]));
    if (r.teacher_id !== teacher) return; // never update another teacher's request

    const stage = code_('stage', a[Q.stage]);
    const when = parseDateTime_(a[Q.stageAt]) || e.response.getTimestamp();
    const amount = a[Q.amount];
    if (amount !== undefined && amount !== '') r.quoted_amount = Number(amount);
    if (a[Q.updateNote]) r.update_notes = (r.update_notes ? r.update_notes + ' | ' : '') + a[Q.updateNote];

    if (stage === 'lost') {
      r.lost_at = when;
      r.lost_reason = code_('lost_reason', a[Q.lostReason]) || 'other';
      r.outcome = 'lost';
    } else if (stage) {
      // Only the chosen stage gets a date. Skipped stages stay blank so validate.py can flag them.
      r[stage + '_at'] = when;
      if (STAGES.indexOf(stage) > STAGES.indexOf(r.last_stage)) r.last_stage = stage;
      if (r.delivered_at && r.paid_at && r.outcome !== 'lost') r.outcome = 'delivered_paid';
    }
    range.setValues([COLUMNS.map(c => r[c])]);
    refreshOpenRequests();
  } finally {
    lock.releaseLock();
  }
}

/** Rebuilds each teacher's request list in Form B: their open requests only, newest first. */
function refreshOpenRequests() {
  const props = PropertiesService.getScriptProperties();
  const lists = FormApp.openById(props.getProperty('FORM_B_ID')).getItems(FormApp.ItemType.LIST);
  const typeShort = Object.fromEntries(CHOICES.request_type.map(([c, l]) => [c, l.split(' / ')[0]]));
  const open = sheet_().getDataRange().getValues().slice(1)
    .filter(v => v[0] && v[col_('outcome') - 1] === 'open')
    .sort((x, y) => new Date(y[col_('received_at') - 1]) - new Date(x[col_('received_at') - 1]));

  CONFIG.teachers.forEach(([code]) => {
    const item = lists.find(i => i.getTitle() === requestTitle_(code));
    if (!item) return;
    const mine = open.filter(v => v[col_('teacher_id') - 1] === code)
      .map(v => [v[0], typeShort[v[col_('request_type') - 1]] || '', v[col_('last_stage') - 1]].join(' · '));
    item.asListItem().setChoiceValues(mine.length ? mine : [NO_OPEN]);
  });
}

// ---------------------------------------------------------------- utilities

function showLinks() {
  const p = PropertiesService.getScriptProperties();
  Logger.log('Request Log (sheet):      ' + SpreadsheetApp.openById(p.getProperty('SHEET_ID')).getUrl());
  Logger.log('Form A, New request:      ' + FormApp.openById(p.getProperty('FORM_A_ID')).getPublishedUrl());
  Logger.log('Form B, Stage update:     ' + FormApp.openById(p.getProperty('FORM_B_ID')).getPublishedUrl());
}

/** Removes triggers and stored IDs so setup() can run again. Does not delete the old sheet or forms. */
function resetSetup() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  PropertiesService.getScriptProperties().deleteAllProperties();
}

/** request_id = received date plus a letter: 2026-11-14-A, -B, … -Z, -AA. Unique across teachers. */
function nextId_(sheet, received) {
  const day = Utilities.formatDate(received, CONFIG.timeZone, 'yyyy-MM-dd');
  const n = sheet.getDataRange().getValues().slice(1)
    .filter(v => String(v[0]).indexOf(day + '-') === 0).length;
  let i = n, letters = '';
  do { letters = String.fromCharCode(65 + (i % 26)) + letters; i = Math.floor(i / 26) - 1; } while (i >= 0);
  return day + '-' + letters;
}

function requestTitle_(code) { return Q.request + ' · ' + code; }

function teacherNames_() { return CONFIG.teachers.map(([, name]) => name); }

function teacherCode_(name) {
  const hit = CONFIG.teachers.find(([, n]) => n === name);
  return hit ? hit[0] : '';
}

function sheet_() {
  const id = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
  return SpreadsheetApp.openById(id).getSheetByName('Requests');
}

function col_(name) { return COLUMNS.indexOf(name) + 1; }

function labels_(list) { return CHOICES[list].map(([, label]) => label); }

function code_(list, label) {
  const hit = CHOICES[list].find(([, l]) => l === label);
  return hit ? hit[0] : '';
}

function answers_(response) {
  const out = {};
  response.getItemResponses().forEach(r => (out[r.getItem().getTitle()] = r.getResponse()));
  return out;
}

function findRow_(sheet, id) {
  if (!id || sheet.getLastRow() < 2) return 0;
  const ids = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1).getValues();
  const i = ids.findIndex(([v]) => v === id);
  return i === -1 ? 0 : i + 2;
}

/** Form date-times arrive as "YYYY-MM-DD HH:MM"; read them in the script's time zone. */
function parseDateTime_(s) {
  const m = String(s || '').match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
  return m ? new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) : null;
}
