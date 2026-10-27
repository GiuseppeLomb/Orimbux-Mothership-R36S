// ORIMBOX offline: every file of the app is kept on the phone the first time it opens (cache first).
// tools/build_web.py fills in the version and the file list; a new version replaces the old cache.
var CACHE = "orimbox-v1.12-2b8c8bfc3f";
var FILES = ["./", "index.html", "kit.json", "manifest.webmanifest", "a/aah.wav", "a/bada.wav", "a/baixo.wav", "a/batalha.wav", "a/boing.wav", "a/bumtss.wav", "a/cajon.wav", "a/coro.wav", "a/cosmos.wav", "a/dum.wav", "a/kalimba.wav", "a/marimba.wav", "a/nave.wav", "a/nuvem.wav", "a/ocarina.wav", "a/orimbux.wav", "a/risco.wav", "a/robo.wav", "a/robos.wav", "a/selva.wav", "a/shaker.wav", "a/tabla.wav", "a/tchka.wav", "a/uuu.wav", "a/zap.wav", "img/aliens.png", "img/icon-180.png", "img/icon-192.png", "img/icon-32.png", "img/icon-512.png", "img/icon-maskable-512.png", "img/ringed.png", "img/ship.png", "fonts/Tiny5-Bold.woff2", "fonts/Tiny5-OFL.txt", "fonts/Tiny5-Regular.woff2"];

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
