// Simple service worker to enable notification click handling when page is closed
self.addEventListener('install', function(event) {
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
      if (clientList.length > 0) {
        // Focus first client
        return clientList[0].focus();
      }
      // If no window open, open a new one
      return clients.openWindow('/');
    })
  );
});
