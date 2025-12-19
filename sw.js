const CACHE_NAME = 'baby-cards-v6';

const CORE_FILES = [
  '/',
  '/index.html',
  '/list.html',
  '/view.html',
  '/data/packs.json',
];

// 缓存策略：true = 缓存优先，false = 网络优先
let cacheFirstMode = false;

// 安装阶段：只缓存核心页面
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(CORE_FILES);
    })
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

// 监听来自客户端的消息
self.addEventListener('message', async event => {
  if (event.data.type === 'updateCacheStrategy') {
    cacheFirstMode = event.data.cacheFirst;
    console.log('缓存策略已更新:', cacheFirstMode ? '缓存优先' : '网络优先');
  } else if (event.data.type === 'cacheResources') {
    // 手动缓存资源
    const resources = event.data.resources || [];
    // 获取发送消息的客户端
    let clientId = null;
    if (event.source && event.source.id) {
      clientId = event.source.id;
    } else {
      // 如果没有 client id，获取所有客户端中的第一个
      const clients = await self.clients.matchAll();
      if (clients.length > 0) {
        clientId = clients[0].id;
      }
    }
    cacheResources(resources, clientId);
  }
});

// 向客户端发送消息
async function sendToClient(clientId, message) {
  const clients = await self.clients.matchAll();
  const client = clients.find(c => c.id === clientId);
  if (client) {
    client.postMessage(message);
  } else {
    // 如果找不到特定客户端，发送给所有客户端
    clients.forEach(c => c.postMessage(message));
  }
}

// 手动缓存资源函数
async function cacheResources(resources, clientId) {
  const cache = await caches.open(CACHE_NAME);
  const total = resources.length;
  let success = 0;
  let failed = 0;
  
  // 批量缓存资源（避免一次性请求过多）
  const batchSize = 10;
  for (let i = 0; i < resources.length; i += batchSize) {
    const batch = resources.slice(i, i + batchSize);
    const results = await Promise.allSettled(
      batch.map(url => {
        // 确保路径以 / 开头
        const fullUrl = url.startsWith('/') ? url : '/' + url;
        return fetch(fullUrl).then(res => {
          if (res.ok) {
            return cache.put(fullUrl, res);
          } else {
            throw new Error(`HTTP ${res.status}`);
          }
        });
      })
    );
    
    // 统计本批次的结果
    results.forEach((result, index) => {
      const url = batch[index];
      const fullUrl = url.startsWith('/') ? url : '/' + url;
      
      if (result.status === 'fulfilled') {
        success++;
      } else {
        failed++;
        console.warn(`缓存失败: ${fullUrl}`, result.reason);
      }
      
      // 发送进度更新
      sendToClient(clientId, {
        type: 'cacheProgress',
        current: success + failed,
        total: total,
        url: fullUrl
      });
    });
  }
  
  // 发送完成消息
  sendToClient(clientId, {
    type: 'cacheComplete',
    success: success,
    failed: failed,
    total: total
  });
  
  console.log(`缓存完成: 成功 ${success}, 失败 ${failed}, 总计 ${total}`);
}

// 获取文件路径的大小写变体
function getCaseVariants(path) {
  const variants = [path]; // 原始路径
  const extMatch = path.match(/\.([^.]+)$/);
  if (extMatch) {
    const ext = extMatch[1];
    const basePath = path.substring(0, path.length - ext.length - 1);
    // 添加小写、大写、首字母大写变体
    if (ext.toLowerCase() !== ext) {
      variants.push(basePath + '.' + ext.toLowerCase());
    }
    if (ext.toUpperCase() !== ext) {
      variants.push(basePath + '.' + ext.toUpperCase());
    }
    if (ext.length > 0) {
      const capitalized = ext.charAt(0).toUpperCase() + ext.slice(1).toLowerCase();
      if (capitalized !== ext) {
        variants.push(basePath + '.' + capitalized);
      }
    }
  }
  return [...new Set(variants)]; // 去重
}

// 尝试从缓存或网络获取资源（支持大小写兼容）
async function fetchWithCaseFallback(request) {
  const url = new URL(request.url);
  const pathname = url.pathname;
  const variants = getCaseVariants(pathname);
  
  // 先尝试从缓存查找（包括所有大小写变体）
  for (const variant of variants) {
    const variantUrl = new URL(variant, request.url);
    const cachedResp = await caches.match(variantUrl);
    if (cachedResp) {
      return cachedResp;
    }
  }
  
  // 缓存中没有，尝试从网络获取（包括所有大小写变体）
  for (const variant of variants) {
    const variantUrl = new URL(variant, request.url);
    try {
      const netResp = await fetch(variantUrl);
      if (netResp && netResp.status === 200) {
        // 成功获取，缓存原始请求URL（保持一致性）
        const clone = netResp.clone();
        if (request.url.startsWith(self.location.origin)) {
          const cache = await caches.open(CACHE_NAME);
          await cache.put(request, clone);
        }
        return netResp;
      }
    } catch (e) {
      // 继续尝试下一个变体
      continue;
    }
  }
  
  // 所有变体都失败
  return null;
}

// 拦截请求：根据缓存策略决定使用缓存优先还是网络优先
self.addEventListener('fetch', event => {
  // 只处理 GET 请求
  if (event.request.method !== 'GET') {
    return;
  }

  const url = new URL(event.request.url);
  const isImageOrAudio = url.pathname.match(/\.(jpg|jpeg|png|gif|webp|mp3)$/i);
  
  // 对于图片和音频，根据缓存策略处理
  if (isImageOrAudio && cacheFirstMode) {
    // 缓存优先模式：先查缓存，缓存没有再请求网络（支持大小写兼容）
    event.respondWith(
      fetchWithCaseFallback(event.request).then(resp => {
        if (resp) {
          return resp;
        }
        return new Response('网络不可用，且缓存中无此资源', {
          status: 503,
          statusText: 'Service Unavailable',
          headers: new Headers({
            'Content-Type': 'text/plain'
          })
        });
      })
    );
  } else if (isImageOrAudio) {
    // 网络优先模式：先请求网络，失败再使用缓存（支持大小写兼容）
    event.respondWith(
      fetchWithCaseFallback(event.request).then(resp => {
        if (resp) {
          return resp;
        }
        // 如果网络和缓存都失败，返回错误响应
        return new Response('网络不可用，且缓存中无此资源', {
          status: 503,
          statusText: 'Service Unavailable',
          headers: new Headers({
            'Content-Type': 'text/plain'
          })
        });
      })
    );
  } else {
    // 非图片/音频资源，使用原有逻辑
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
  }
});