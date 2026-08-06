const CACHE='ss34-catalog-vote-recovery';
self.addEventListener('install',e=>{self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil((async()=>{const keys=await caches.keys();await Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)));await self.clients.claim();})());});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(u.origin!==location.origin)return;e.respondWith(fetch(e.request,{cache:'no-store'}).then(res=>{const c=res.clone();caches.open(CACHE).then(cache=>cache.put(e.request,c));return res;}).catch(()=>caches.match(e.request)));});
