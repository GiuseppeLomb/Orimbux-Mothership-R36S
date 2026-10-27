// ORIMBOX offline: every file of the app is kept on the phone the first time it opens (cache first).
// tools/build_web.py fills in the version and the file list; a new version replaces the old cache.
var CACHE = "orimbox-__VERSION__";
var FILES = __FILES__;

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(FILES); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k.indexOf("orimbox-") === 0 && k !== CACHE; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
var URLS = null;
self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  // only ORIMBOX's own files: the other apps on the same site (o-meu-dia/...) go straight to the network
  URLS = URLS || FILES.map(function (f) { return new URL(f, self.registration.scope).href; });
  if (URLS.indexOf(e.request.url.split("#")[0].split("?")[0]) < 0) return;
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(function (r) { return r || fetch(e.request); }));
});
