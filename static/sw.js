// Minimal service worker. Its job is not caching: Chrome on Android only installs a real app
// (a WebAPK, which is what honours "display": "fullscreen") when the site has one with a fetch
// handler. Without it, "Add to home screen" makes a plain shortcut that opens in a normal tab,
// browser bar and all, which is the whole problem we are solving.
self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', function (event) {
  event.respondWith(fetch(event.request));
});
