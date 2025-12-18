const CACHE_NAME = 'app-cache-v1';

const urlsToCache = [
  '/static/offline.html',
  '/static/css/index.css',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png'
];

self.addEventListener('install', event => {
  console.log("Service Worker: install event");
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log("Service Worker: caching files");
      return cache.addAll(urlsToCache);
    })
  );
});

self.addEventListener('activate', event => {
  console.log("Service Worker: activate event");
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(name => {
          if (name !== CACHE_NAME) {
            console.log("Service Worker: deleting old cache", name);
            return caches.delete(name);
          }
        })
      );
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() => {
      // ネットワーク失敗時はキャッシュを探し、なければ offline.html を返す
      return caches.match(event.request).then(response => {
        return response || caches.match('/static/offline.html');
      });
    })
  );
});
