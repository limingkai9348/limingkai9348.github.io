const CACHE_NAME = 'baby-cards-v2';

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
});

// 激活：清理旧缓存（以后你版本升级用）
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
});

// 拦截请求：优先缓存，失败再网络
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(resp =>
      resp ||
      fetch(event.request).then(netResp => {
        // 音频 & 图片 & json 都缓存
        if (event.request.url.startsWith(self.location.origin)) {
          const clone = netResp.clone();
          caches.open(CACHE_NAME).then(cache =>
            cache.put(event.request, clone)
          );
        }
        return netResp;
      })
    )
  );
});