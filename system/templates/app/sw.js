/* creaite's service worker (BL-86): it does one thing. When the live server isn't running, a page the installed app opens
   shows the offline page instead of Chrome's error. Nothing else is cached or intercepted. */
const CACHE = "creaite-offline-v1";
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.add("/offline"))); self.skipWaiting(); });
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  if (e.request.mode !== "navigate") return;
  e.respondWith(fetch(e.request).catch(() => caches.match("/offline")));
});
