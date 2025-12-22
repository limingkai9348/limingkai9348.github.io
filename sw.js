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
    const forceUpdate = event.data.forceUpdate || false;  // 获取强制更新标志
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
    cacheResources(resources, clientId, forceUpdate);
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

// 尝试获取资源（支持大小写兼容）
async function fetchResourceWithCaseFallback(url) {
  // 检测是否是在线URL（http:// 或 https:// 开头）
  if (url.startsWith('http://') || url.startsWith('https://')) {
    // 在线URL：直接fetch，不进行大小写变体处理
    const res = await fetch(url);
    if (res && res.ok) {
      return { response: res, actualUrl: url };
    }
    throw new Error(`无法获取在线资源: ${url} (状态码: ${res?.status})`);
  }
  
  // 相对路径：进行大小写兼容处理
  // 获取当前页面的 origin（从客户端获取）
  let origin = '';
  try {
    const clients = await self.clients.matchAll();
    if (clients.length > 0 && clients[0].url) {
      const clientUrl = new URL(clients[0].url);
      origin = clientUrl.origin;
    }
  } catch (e) {
    // 如果无法获取，尝试使用 self.location（某些浏览器支持）
    try {
      origin = self.location.origin;
    } catch (e2) {
      // 如果都失败，使用相对路径（浏览器会自动使用当前 origin）
      origin = '';
    }
  }
  
  const fullUrl = url.startsWith('/') ? url : '/' + url;
  const baseUrl = origin ? `${origin}${fullUrl}` : fullUrl;
  const urlObj = new URL(baseUrl);
  const pathname = urlObj.pathname;
  const variants = getCaseVariants(pathname);
  
  // 尝试所有大小写变体
  for (const variant of variants) {
    const variantUrl = new URL(variant, urlObj.origin);
    try {
      const res = await fetch(variantUrl);
      if (res && res.ok) {
        return { response: res, actualUrl: fullUrl }; // 返回原始URL用于缓存键
      }
    } catch (e) {
      // 继续尝试下一个变体
      continue;
    }
  }
  
  // 所有变体都失败
  throw new Error(`无法找到资源: ${fullUrl} (已尝试所有大小写变体)`);
}

// 检查资源是否已缓存（支持大小写兼容）
async function isResourceCached(cache, url) {
  // 检测是否是在线URL（http:// 或 https:// 开头）
  if (url.startsWith('http://') || url.startsWith('https://')) {
    // 在线URL：直接使用完整URL检查缓存
    const cached = await cache.match(url);
    return !!cached;
  }
  
  // 相对路径：进行大小写兼容检查
  const cacheUrl = url.startsWith('/') ? url : '/' + url;
  const variants = getCaseVariants(cacheUrl);
  
  // 检查所有大小写变体
  for (const variant of variants) {
    const cached = await cache.match(variant);
    if (cached) {
      return true;
    }
  }
  return false;
}

// 手动缓存资源函数
async function cacheResources(resources, clientId, forceUpdate = false) {
  const cache = await caches.open(CACHE_NAME);
  const total = resources.length;
  let success = 0;
  let failed = 0;
  let skipped = 0; // 已缓存的数量
  let updated = 0; // 强制更新的数量
  
  // 批量缓存资源（避免一次性请求过多）
  const batchSize = 10;
  for (let i = 0; i < resources.length; i += batchSize) {
    const batch = resources.slice(i, i + batchSize);
    const results = await Promise.allSettled(
      batch.map(async url => {
        // 检测是否是在线URL（http:// 或 https:// 开头）
        const isOnlineUrl = url.startsWith('http://') || url.startsWith('https://');
        const cacheUrl = isOnlineUrl ? url : (url.startsWith('/') ? url : '/' + url);
        
        // 如果强制更新，跳过缓存检查
        const wasCached = await isResourceCached(cache, url);
        if (!forceUpdate && wasCached) {
          return { skipped: true, updated: false, url: cacheUrl };
        }
        
        try {
          let response;
          if (isOnlineUrl) {
            // 在线URL：直接fetch，不进行大小写变体处理
            response = await fetch(url);
            if (!response || !response.ok) {
              throw new Error(`无法获取在线资源: ${url} (状态码: ${response?.status})`);
            }
          } else {
            // 相对路径：使用大小写兼容的方式获取资源
            const result = await fetchResourceWithCaseFallback(url);
            response = result.response;
          }
          // 使用原始URL作为缓存键，保持一致性
          await cache.put(cacheUrl, response);
          return { 
            skipped: false, 
            updated: forceUpdate && wasCached,  // 如果是强制更新且之前已缓存，则标记为已更新
            url: cacheUrl 
          };
        } catch (error) {
          throw error;
        }
      })
    );
    
    // 统计本批次的结果
    results.forEach((result, index) => {
      const url = batch[index];
      const isOnlineUrl = url.startsWith('http://') || url.startsWith('https://');
      const fullUrl = isOnlineUrl ? url : (url.startsWith('/') ? url : '/' + url);
      
      if (result.status === 'fulfilled') {
        if (result.value.skipped) {
          skipped++;
        } else {
          success++;
          if (result.value.updated) {
            updated++;
          }
        }
      } else {
        failed++;
        console.warn(`缓存失败: ${fullUrl}`, result.reason);
      }
      
      // 发送进度更新
      sendToClient(clientId, {
        type: 'cacheProgress',
        current: success + failed + skipped,
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
    skipped: skipped,
    updated: updated,
    total: total
  });
  
  console.log(`缓存完成: 成功 ${success}, 失败 ${failed}, 已跳过 ${skipped}, 已更新 ${updated}, 总计 ${total}`);
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
  const isOnlineUrl = url.protocol === 'http:' || url.protocol === 'https:';
  
  // 检测是否是在线URL
  if (isOnlineUrl) {
    // 在线URL：先尝试从缓存查找
    const cachedResp = await caches.match(request.url);
    if (cachedResp) {
      return cachedResp;
    }
    
    // 缓存中没有，尝试从网络获取
    try {
      const netResp = await fetch(request.url);
      if (netResp && netResp.status === 200) {
        // 成功获取，缓存在线URL（跨域资源也可以缓存）
        const clone = netResp.clone();
        const cache = await caches.open(CACHE_NAME);
        await cache.put(request.url, clone);
        return netResp;
      }
    } catch (e) {
      // 网络请求失败
      return null;
    }
    return null;
  }
  
  // 相对路径：进行大小写兼容处理
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
  const isJson = url.pathname.match(/\.json$/i);
  
  // 对于图片、音频和JSON，根据缓存策略处理
  if ((isImageOrAudio || isJson) && cacheFirstMode) {
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
  } else if (isImageOrAudio || isJson) {
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