// TableMaster Pro - Service Worker v7.1.0
const CACHE_NAME = 'tablemaster-pro-v7.1';
const OFFLINE_URL = './index.html';

// Lokálne zdroje - MUSIA byť nacachované (inštalácia zlyhá ak tieto chýbajú)
const SHELL_URLS = [
  './',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-512.png',
  './icons/apple-touch-icon.png',
  './icons/favicon-32.png'
];

// Externé CDN zdroje - best-effort (ak nedostupné, inštalácia pokračuje)
const EXTERNAL_URLS = [
  'https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js',
  'https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.4.1/papaparse.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.29/jspdf.plugin.autotable.min.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
  'https://cdn.jsdelivr.net/npm/docx@8.5.0/build/index.umd.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // App shell - povinné, atomické
      await cache.addAll(SHELL_URLS);

      // CDN knižnice - best-effort, inštalácia neprestane pri výpadku CDN
      await Promise.allSettled(
        EXTERNAL_URLS.map(url =>
          cache.add(url).catch(err => {
            console.warn('[ServiceWorker] Nepodárilo sa cachovať:', url, err);
          })
        )
      );

      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  if (!event.request.url.startsWith('http')) return;

  const url = new URL(event.request.url);

  // Navigačné requesty (HTML stránky): network-first, fallback na offline stránku
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          if (response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() =>
          caches.match(event.request).then(cached => cached || caches.match(OFFLINE_URL))
        )
    );
    return;
  }

  // Statické assety (JS, CSS, fonty, obrázky): cache-first, aktualizuj na pozadí
  event.respondWith(
    caches.match(event.request).then(cached => {
      const networkFetch = fetch(event.request).then(response => {
        if (response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => null);

      // Vrát cache okamžite, stiahni novú verziu na pozadí
      return cached || networkFetch;
    })
  );
});

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-data') {
    console.log('[ServiceWorker] Background sync');
  }
});

self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json();
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || null
    });
  }
});

self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') self.skipWaiting();
  if (event.data === 'getVersion') event.ports[0].postMessage({ version: CACHE_NAME });
});
