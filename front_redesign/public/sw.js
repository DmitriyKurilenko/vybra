/* sw.js — service worker для Vybra PWA.
 *
 * Стратегии:
 *  - navigation (HTML): network-first, fallback на кэшированную оболочку SPA.
 *    Гарантирует актуальность при онлайне и работоспособность офлайн.
 *  - static (/static/): stale-while-revalidate. Хешированные Vite-ассеты
 *    иммутабельны — кэш можно обновлять фоном без блокировки.
 *  - API (/api/): network-only, без кэширования — данные должны быть свежими.
 */
const CACHE = 'vybra-v1';
const SHELL = '/app/';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll([SHELL])).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(SHELL, copy));
          return res;
        })
        .catch(() => caches.match(SHELL))
    );
    return;
  }

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then((cached) => {
        const network = fetch(req).then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        }).catch(() => cached);
        return cached || network;
      })
    );
    return;
  }

  if (url.pathname.startsWith('/api/')) {
    return;
  }
});
