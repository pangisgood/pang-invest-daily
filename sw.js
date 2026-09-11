const CACHE = 'pang-invest-v2';
const STATIC = ['./manifest.webmanifest', './icon-192.png', './icon-512.png', './ocr.js'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(STATIC)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // 최신 HTML과 data.json은 먼저 네트워크에서 확인.
  if (event.request.mode === 'navigate' || url.pathname.endsWith('/index.html') || url.pathname.endsWith('/data.json')) {
    event.respondWith(
      fetch(event.request, { cache: 'no-store' })
        .then(resp => {
          const copy = resp.clone();
          caches.open(CACHE).then(cache => cache.put(event.request, copy));
          return resp;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // 나머지 정적 파일은 캐시 우선.
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
