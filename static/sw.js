self.addEventListener('install', () => {
    console.log('SW instalado');
});

self.addEventListener('fetch', function(event) {
    event.respondWith(fetch(event.request));
});