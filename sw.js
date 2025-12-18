const CACHE_NAME = 'baby-cards-v5';

const CORE_FILES = [
  '/',
  '/index.html',
  '/view.html',
];

// 安装阶段：缓存核心页面
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      cache.addAll(CORE_FILES)
    )
  );
  // 立即激活新的 Service Worker
  self.skipWaiting();
});

// 激活：清理旧缓存
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_NAME)
          .map(k => caches.delete(k))
      )
    )
  );
  // 立即控制所有客户端
  return self.clients.claim();
});

// 拦截请求：网络优先，失败再使用缓存
self.addEventListener('fetch', event => {
  // 只处理 GET 请求
  if (event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then(netResp => {
        // 网络请求成功，更新缓存并返回
        if (netResp && netResp.status === 200) {
          const clone = netResp.clone();
          // 只缓存同源资源
          if (event.request.url.startsWith(self.location.origin)) {
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, clone);
            });
          }
        }
        return netResp;
      })
      .catch(() => {
        // 网络请求失败，尝试从缓存获取
        return caches.match(event.request).then(cachedResp => {
          if (cachedResp) {
            return cachedResp;
          }
          // 如果缓存也没有，返回一个基本的错误响应
          return new Response('网络不可用，且缓存中无此资源', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: new Headers({
              'Content-Type': 'text/plain'
            })
          });
        });
      })
  );
});