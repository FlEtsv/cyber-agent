const SHARED_SECRET = 'CAMBIA_ESTE_SECRETO_LARGO';

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents || '{}');
    if (body.secret !== SHARED_SECRET) {
      return json_({ ok: false, error: 'unauthorized' }, 401);
    }

    const email = String(body.email || '').trim();
    const code = String(body.code || '').trim();
    const device = body.device || {};
    const ttl = Math.round(Number(body.ttl_seconds || 600) / 60);
    if (!email || !/^\d{6}$/.test(code)) {
      return json_({ ok: false, error: 'bad_request' }, 400);
    }

    const subject = `CyberAgent login: ${code}`;
    const text =
      `Codigo de acceso CyberAgent: ${code}\n\n` +
      `Caduca en ${ttl} minutos.\n\n` +
      `Dispositivo: ${device.label || 'desconocido'}\n` +
      `Plataforma: ${device.platform || 'desconocida'}\n` +
      `IP: ${device.ip || 'desconocida'}\n` +
      `User-Agent: ${device.user_agent || 'desconocido'}\n\n` +
      `Si no has sido tu, ignora este correo.`;

    GmailApp.sendEmail(email, subject, text, { name: 'CyberAgent Relay' });
    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false, error: String(err) }, 500);
  }
}

function json_(obj, status) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
