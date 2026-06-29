const CACHE = 'cyberagent-v13';
const PRECACHE = [
  '/',
  '/static/style.css',
  '/static/app.js',
  '/static/ui.js',
  '/manifest.json',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => clients.claim())
  );
});

// ¿Es un recurso propio del shell (HTML/JS/CSS/manifest)? Para estos usamos
// network-first para que los updates lleguen SIEMPRE; el resto, cache-first.
function isShellAsset(url) {
  return url.origin === self.location.origin && (
    url.pathname === '/' ||
    url.pathname === '/index.html' ||
    url.pathname === '/manifest.json' ||
    url.pathname.startsWith('/static/')
  );
}

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // WebSocket y API: siempre a red, nunca caché.
  if (url.pathname.startsWith('/ws') || url.pathname.startsWith('/api') || url.pathname === '/terminal') {
    return;
  }

  // Navegaciones (deep links con ?action=...): red primero; si falla, shell
  // cacheado para que la app abra con el PC apagado (offline parcial).
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).catch(() => caches.match('/'))
    );
    return;
  }

  // Shell/estáticos propios: NETWORK-FIRST con revalidación (cache:'no-cache'
  // → 304 barato cuando no cambian). Así un deploy nuevo se ve al instante.
  // Cae a caché solo si no hay red (offline parcial).
  if (e.request.method === 'GET' && isShellAsset(url)) {
    e.respondWith(
      fetch(e.request, { cache: 'no-cache' })
        .then(res => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then(c => c.put(e.request, copy));
          }
          return res;
        })
        .catch(() => caches.match(e.request).then(c => c || caches.match('/')))
    );
    return;
  }

  // Resto (CDNs de terceros, etc.): cache-first con relleno en segundo plano.
  e.respondWith(
    caches.match(e.request).then(cached => {
      const network = fetch(e.request).then(res => {
        if (res.ok && e.request.method === 'GET') {
          caches.open(CACHE).then(c => c.put(e.request, res.clone()));
        }
        return res;
      });
      return cached || network;
    })
  );
});
