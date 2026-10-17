// SemiScope service worker: makes the dashboard installable and usable offline.
// - Our own files (pages, scripts, data): network-first, so updates show up immediately
//   when online; the last cached copy is used when offline.
// - Chart.js from the CDN: cache-first (the pinned version never changes).
//   Cached fallbacks carry an "X-SW-Cache: 1" header so the page can show an offline banner.
const VERSION = 'semiscope-v5';
const SHELL = [
  './', 'index.html', 'setup.html', 'weekly.html', 'practice.html', 'setup_steps.js', 'helpers.js', 'manifest.webmanifest',
  'icon-192.png', 'icon-512.png', 'apple-touch-icon.png',
  'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js',
];
const DATA = ['data.json', 'detail.json', 'run_log.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => null))))
    .then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function networkFirst(req, key) {
  const cache = await caches.open(VERSION);
  try {
    const res = await fetch(req);
    if (res.ok) cache.put(key, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(key);
    if (!hit) throw err;
    const headers = new Headers(hit.headers); headers.set('X-SW-Cache', '1');
    return new Response(await hit.blob(), {status: 200, headers});
  }
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const file = url.pathname.split('/').pop();
  if (url.origin === location.origin && DATA.includes(file)) {
    // ignore the ?cache-buster so every version of data.json shares one cache entry
    e.respondWith(networkFirst(req, new Request(url.origin + url.pathname)));
    return;
  }
  if (url.origin === location.origin) {
    e.respondWith(networkFirst(req, new Request(url.origin + url.pathname))
      .catch(() => caches.match('index.html')));
    return;
  }
  if (url.hostname === 'cdnjs.cloudflare.com') {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); }
      return res;
    })));
  }
});
