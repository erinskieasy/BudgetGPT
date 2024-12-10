
// Service Worker for GPT Budget Tracker
const CACHE_NAME = 'gpt-budget-tracker-v3';
const urlsToCache = [
  '/',
  '/manifest.json',
  '/generated-icon-192.png',
  '/generated-icon-512.png',
  '/sw.js'
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});
