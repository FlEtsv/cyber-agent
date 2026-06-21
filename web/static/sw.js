// CyberAgent Service Worker — maneja push notifications y aprobaciones

self.addEventListener('install',  e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(clients.claim()));

self.addEventListener('push', e => {
  if (!e.data) return;
  let data;
  try { data = e.data.json(); } catch { return; }

  const isApproval = data.type === 'approval';
  const opts = {
    body:               data.body || '',
    icon:               '/static/icon.png',
    badge:              '/static/badge.png',
    data:               data,
    requireInteraction: isApproval,
    vibrate:            isApproval ? [200, 100, 200, 100, 400] : [200],
    actions: isApproval ? [
      { action: 'approve', title: '✓ Aprobar' },
      { action: 'reject',  title: '✗ Rechazar' },
    ] : [],
  };

  e.waitUntil(self.registration.showNotification(data.title || 'CyberAgent', opts));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const data   = e.notification.data || {};
  const action = e.action;

  if (data.type === 'approval' && data.token) {
    const decision = (action === 'approve') ? 'approve' : 'reject';
    e.waitUntil(
      fetch(`/approval/${data.token}/decide`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ decision }),
      }).catch(() => {})
    );
  }

  // Abre la ventana si hay URL asociada
  if (data.url) {
    e.waitUntil(
      clients.matchAll({ type: 'window' }).then(wins => {
        if (wins.length) return wins[0].focus();
        return clients.openWindow(data.url);
      })
    );
  }
});
