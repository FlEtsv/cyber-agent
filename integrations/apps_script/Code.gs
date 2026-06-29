/**
 * CyberAgent — Puente Apps Script (WEBPROD-016)
 * ---------------------------------------------------------------------------
 * Webapp que TÚ (Steve) despliegas en tu cuenta de Google. Da a tu agente la
 * capacidad de ejecutar acciones AVANZADAS en tu Workspace bajo demanda:
 * crear/modificar Sheets, Docs, Slides, gestionar Gmail, Drive, Calendar, etc.
 *
 * SEGURIDAD:
 *  - Protegido por un SECRETO compartido (Script Properties: SHARED_SECRET).
 *    ESTE secreto es lo que protege la webapp: doPost rechaza todo sin él.
 *  - Cada acción que pide el agente pasa por la tarjeta de aprobación del agente
 *    (es una tool peligrosa) → tú das el consentimiento.
 *
 * DESPLIEGUE:
 *  1. script.google.com → Nuevo proyecto → pega este archivo.
 *  2. Configuración del proyecto → Propiedades de script → añade
 *     SHARED_SECRET = (un secreto largo aleatorio).
 *  3. Implementar → Nueva implementación → Aplicación web:
 *       - Ejecutar como: Yo (mismo)
 *       - Quién tiene acceso: CUALQUIERA   ← necesario para POST programático;
 *         la seguridad la da el SHARED_SECRET (no "Solo yo", que exigiría login
 *         OAuth por cada petición y bloquearía al PC).
 *  4. Autoriza los permisos que pida (Sheets/Docs/Slides/Gmail/Drive/Calendar).
 *  5. Copia la URL /exec y pásala al PC:
 *       APPS_SCRIPT_URL=<url>   APPS_SCRIPT_SECRET=<el secreto>
 *
 * PROTOCOLO (POST JSON):
 *   { "secret": "...", "op": "<operación>", "params": { ... }, "code": "<JS opcional>" }
 *   Respuesta: { "ok": true, "result": <...> }  |  { "ok": false, "error": "..." }
 */

function doPost(e) {
  try {
    var body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    var expected = PropertiesService.getScriptProperties().getProperty('SHARED_SECRET');
    if (!expected || body.secret !== expected) {
      return _json({ ok: false, error: 'unauthorized' });
    }
    var op = String(body.op || '').trim();
    var p = body.params || {};
    var result = (op === 'exec') ? _exec(body.code, p) : _dispatch(op, p);
    return _json({ ok: true, op: op, result: result });
  } catch (err) {
    return _json({ ok: false, error: String(err) });
  }
}

function doGet() {
  // Comprobación de salud (no expone nada).
  return _json({ ok: true, service: 'cyberagent-apps-script', ts: Date.now() });
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * exec: ejecuta código Apps Script que escribe el agente. Es el camino "avanzado
 * / arbitrario" (crear cualquier cosa). El código recibe `params` y debe devolver
 * un valor serializable (return ...). Disponibles: SpreadsheetApp, DocumentApp,
 * SlidesApp, GmailApp, DriveApp, CalendarApp, Utilities, etc.
 */
function _exec(code, params) {
  if (!code) throw new Error('exec requiere "code"');
  var fn = new Function('params', code);
  return fn(params || {});
}

/** Catálogo de operaciones comunes (atajos seguros sin escribir código). */
function _dispatch(op, p) {
  switch (op) {
    // ── Sheets ──────────────────────────────────────────────────────────────
    case 'sheets_create': {
      var ss = SpreadsheetApp.create(p.title || 'Hoja CyberAgent');
      if (p.rows) ss.getActiveSheet().getRange(1, 1, p.rows.length, p.rows[0].length).setValues(p.rows);
      return { id: ss.getId(), url: ss.getUrl() };
    }
    case 'sheets_append': {
      var sh = SpreadsheetApp.openById(p.id).getActiveSheet();
      (p.rows || []).forEach(function (r) { sh.appendRow(r); });
      return { id: p.id, appended: (p.rows || []).length };
    }
    case 'sheets_read': {
      var values = SpreadsheetApp.openById(p.id).getActiveSheet().getDataRange().getValues();
      return { id: p.id, values: values };
    }
    // ── Docs ────────────────────────────────────────────────────────────────
    case 'doc_create': {
      var doc = DocumentApp.create(p.title || 'Documento CyberAgent');
      if (p.text) doc.getBody().setText(p.text);
      doc.saveAndClose();
      return { id: doc.getId(), url: doc.getUrl() };
    }
    case 'doc_append': {
      var d = DocumentApp.openById(p.id);
      d.getBody().appendParagraph(p.text || '');
      d.saveAndClose();
      return { id: p.id, ok: true };
    }
    // ── Slides ──────────────────────────────────────────────────────────────
    case 'slides_create': {
      var pres = SlidesApp.create(p.title || 'Presentación CyberAgent');
      (p.slides || []).forEach(function (s) {
        var slide = pres.appendSlide(SlidesApp.PredefinedLayout.TITLE_AND_BODY);
        var ph = slide.getPlaceholders();
        if (ph[0]) ph[0].asShape().getText().setText(s.title || '');
        if (ph[1] && s.body) ph[1].asShape().getText().setText(s.body);
      });
      return { id: pres.getId(), url: pres.getUrl() };
    }
    // ── Gmail ───────────────────────────────────────────────────────────────
    case 'gmail_search': {
      var threads = GmailApp.search(p.query || '', 0, p.max || 10);
      return threads.map(function (t) {
        var m = t.getMessages()[0];
        return { id: t.getId(), from: m.getFrom(), subject: t.getFirstMessageSubject(),
                 date: m.getDate(), snippet: m.getPlainBody().slice(0, 160) };
      });
    }
    case 'gmail_send': {
      GmailApp.sendEmail(p.to, p.subject || '', p.body || '', p.options || {});
      return { ok: true, to: p.to };
    }
    case 'gmail_label': {
      var label = GmailApp.getUserLabelByName(p.label) || GmailApp.createLabel(p.label);
      GmailApp.search(p.query || '', 0, p.max || 50).forEach(function (t) {
        t.addLabel(label);
        if (p.archive) t.moveToArchive();
        if (p.markRead) t.markRead();
      });
      return { ok: true, label: p.label };
    }
    // ── Drive ───────────────────────────────────────────────────────────────
    case 'drive_list': {
      var it = DriveApp.searchFiles(p.query || "trashed = false");
      var out = [], n = 0;
      while (it.hasNext() && n < (p.max || 20)) {
        var f = it.next(); n++;
        out.push({ id: f.getId(), name: f.getName(), url: f.getUrl(), type: f.getMimeType() });
      }
      return out;
    }
    // ── Calendar ──────────────────────────────────────────────────────────────
    case 'calendar_create': {
      var ev = CalendarApp.getDefaultCalendar().createEvent(
        p.title || 'Evento', new Date(p.start), new Date(p.end || p.start),
        { description: p.description || '', location: p.location || '' });
      return { id: ev.getId(), title: ev.getTitle() };
    }
    default:
      throw new Error('operación desconocida: ' + op + ' (usa op:"exec" para acciones arbitrarias)');
  }
}
