"""
四级缓存服务 - 论文3.3.2节缓存架构实现

L1: 内存缓存 (In-Memory) - 进程级，重启丢失
L2: Redis缓存 (Distributed) - 跨进程共享
L3: PostgreSQL (Persistent) - 已有数据库层
冷启动: 按需加载
"""
import json
import pickle
import hashlib
import asyncio
from typing import Optional, Any, Dict, List, Callable
from functools import wraps
import time

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("[Cache] ⚠️ redis-py未安装，L2缓存将不可用")

from app.core.config import settings


class MemoryCache:
    """L1: 进程级内存缓存"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
        self._access_count: Dict[str, int] = {}
        self._hit_count = 0
        self._miss_count = 0
        self._max_size = 1000  # 最大缓存条目数
        self._lock = asyncio.Lock()
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存key"""
        key_data = f"{prefix}:{str(args)}:{str(kwargs)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        async with self._lock:
            # 检查是否过期
            if key in self._ttl and time.time() > self._ttl[key]:
                self._delete(key)
                self._miss_count += 1
                return None
            
            if key in self._cache:
                self._access_count[key] = self._access_count.get(key, 0) + 1
                self._hit_count += 1
                return self._cache[key]
            
            self._miss_count += 1
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = 3600,
        tags: Optional[List[str]] = None
    ):
        """设置缓存值"""
        async with self._lock:
            # LRU淘汰: 如果超过最大大小，删除最少访问的
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = value
            self._ttl[key] = time.time() + ttl
            self._access_count[key] = 0
    
    async def delete(self, key: str):
        """删除缓存"""
        async with self._lock:
            self._delete(key)
    
    def _delete(self, key: str):
        """内部删除（无锁）"""
        self._cache.pop(key, None)
        self._ttl.pop(key, None)
        self._access_count.pop(key, None)
    
    def _evict_lru(self):
        """LRU淘汰策略"""
        if not self._access_count:
            return
        # 找到访问次数最少的key
        lru_key = min(self._access_count, key=self._access_count.get)
        self._delete(lru_key)
        print(f"[MemoryCache] LRU淘汰: {lru_key[:16]}...")
    
    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            self._ttl.clear()
            self._access_count.clear()
    
    async def invalidate_by_tag(self, tag: str):
        """按标签失效缓存"""
        # 简单实现: 清空所有（实际可以维护tag->keys索引）
        async with self._lock:
            self._cache.clear()
            self._ttl.clear()
            self._access_count.clear()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0
        return {
            "level": "L1",
            "type": "memory",
            "size": len(self._cache),
            "max_size": self._max_size,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate": f"{hit_rate:.2%}",
            "hit_rate_value": hit_rate
        }


class RedisCache:
    """L2: Redis分布式缓存"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._connected = False
        self._hit_count = 0
        self._miss_count = 0
        self._error_count = 0
    
    async def connect(self):
        """连接Redis"""
        if not REDIS_AVAILABLE or not settings.REDIS_ENABLED:
            print("[RedisCache] L2缓存已禁用")
            return False
        
        try:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=False,  # 二进制数据
                socket_connect_timeout=2,
                socket_timeout=2,
                max_connections=20
            )
            await self._client.ping()
            self._connected = True
            print(f"[RedisCache] ✅ 已连接到 {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            return True
        except Exception as e:
            self._connected = False
            self._error_count += 1
            print(f"[RedisCache] ❌ 连接失败: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self._connected or not self._client:
            return None
        
        try:
            data = await self._client.get(key)
            if data:
                self._hit_count += 1
                return pickle.loads(data)
            self._miss_count += 1
            return None
        except Exception as e:
            self._error_count += 1
            print(f"[RedisCache] 获取失败: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存"""
        if not self._connected or not self._client:
            return False
        
        try:
            serialized = pickle.dumps(value)
            await self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            self._error_count += 1
            print(f"[RedisCache] 设置失败: {e}")
            return False
    
    async def delete(self, key: str):
        """删除缓存"""
        if not self._connected or not self._client:
            return False
        
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            self._error_count += 1
            print(f"[RedisCache] 删除失败: {e}")
            return False
    
    async def clear(self):
        """清空缓存"""
        if not self._connected or not self._client:
            return False
        
        try:
            await self._client.flushdb()
            print("[RedisCache] 已清空")
            return True
        except Exception as e:
            print(f"[RedisCache] 清空失败: {e}")
            return False
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取"""
        if not self._connected or not self._client:
            return {}
        
        try:
            values = await self._client.mget(keys)
            result = {}
            for k, v in zip(keys, values):
                if v:
                    result[k] = pickle.loads(v)
                    self._hit_count += 1
                else:
                    self._miss_count += 1
            return result
        except Exception as e:
            self._error_count += 1
            print(f"[RedisCache] 批量获取失败: {e}")
            return {}
    
    def get_stats(self) -> Dict:
        """获取统计"""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0
        return {
            "level": "L2",
            "type": "redis",
            "connected": self._connected,
            "host": settings.REDIS_HOST if self._connected else None,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "error_count": self._error_count,
            "hit_rate": f"{hit_rate:.2%}",
            "hit_rate_value": hit_rate
        }


class CacheManager:
    """
    缓存管理器 - 统一入口
    
    缓存策略:
    1. 读: L1 → L2 → DB (逐级回源)
    2. 写: DB → L2 → L1 (级联更新)
    3. 淘汰: L1 LRU, L2 TTL
    """
    
    def __init__(self):
        self.l1 = MemoryCache()
        self.l2 = RedisCache()
        self._initialized = False
    
    async def initialize(self):
        """初始化缓存服务"""
        if self._initialized:
            return
        
        # 连接L2 Redis
        await self.l2.connect()
        self._initialized = True
        print("[CacheManager] 缓存服务初始化完成")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """生成统一缓存key"""
        # 排序kwargs确保一致性
        sorted_kwargs = sorted(kwargs.items()) if kwargs else []
        key_data = f"{prefix}:{str(args)}:{str(sorted_kwargs)}"
        return f"eduqa:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def get(
        self, 
        prefix: str, 
        *args, 
        **kwargs
    ) -> Optional[Any]:
        """
        获取缓存 (L1 → L2)
        
        Args:
            prefix: 缓存前缀，如'expert', 'rag', 'vector'
        """
        if not settings.ENABLE_CACHE:
            return None
        
        key = self._generate_key(prefix, *args, **kwargs)
        
        # 1. 查L1
        value = await self.l1.get(key)
        if value is not None:
            return value
        
        # 2. 查L2
        value = await self.l2.get(key)
        if value is not None:
            # 回填L1
            await self.l1.set(key, value, ttl=settings.CACHE_TTL)
            return value
        
        return None
    
    async def set(
        self, 
        prefix: str, 
        value: Any, 
        *args,
        ttl: Optional[int] = None,
        l1_only: bool = False,
        **kwargs
    ):
        """
        设置缓存
        
        Args:
            prefix: 缓存前缀
            value: 缓存值
            ttl: 过期时间(秒)
            l1_only: 是否只存L1(大对象)
        """
        if not settings.ENABLE_CACHE:
            return
        
        key = self._generate_key(prefix, *args, **kwargs)
        ttl = ttl or settings.CACHE_TTL
        
        # 存L1
        await self.l1.set(key, value, ttl=ttl)
        
        # 存L2 (小对象)
        if not l1_only:
            await self.l2.set(key, value, ttl=ttl)
    
    async def delete(self, prefix: str, *args, **kwargs):
        """删除缓存"""
        key = self._generate_key(prefix, *args, **kwargs)
        await self.l1.delete(key)
        await self.l2.delete(key)
    
    async def invalidate_pattern(self, pattern: str):
        """按模式失效缓存 (仅Redis支持)"""
        if self.l2._connected and self.l2._client:
            try:
                keys = []
                async for key in self.l2._client.scan_iter(match=f"eduqa:*{pattern}*"):
                    keys.append(key)
                if keys:
                    await self.l2._client.delete(*keys)
                    print(f"[CacheManager] 失效 {len(keys)} 个缓存")
            except Exception as e:
                print(f"[CacheManager] 模式失效失败: {e}")
        
        # 清空L1
        await self.l1.clear()
    
    async def clear_all(self):
        """清空所有缓存"""
        await self.l1.clear()
        await self.l2.clear()
        print("[CacheManager] 所有缓存已清空")
    
    def cached(
        self, 
        prefix: str, 
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None
    ):
        """
        缓存装饰器
        
        Usage:
            @cache_manager.cached("expert", ttl=7200)
            async def get_expert(subject: str):
                return await fetch_from_db(subject)
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = (args, tuple(sorted(kwargs.items())))
                
                # 查缓存
                cached_value = await self.get(prefix, *cache_key)
                if cached_value is not None:
                    return cached_value
                
                # 执行函数
                result = await func(*args, **kwargs)
                
                # 写缓存
                await self.set(prefix, result, *cache_key, ttl=ttl)
                
                return result
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict:
        """获取完整统计"""
        return {
            "cache_enabled": settings.ENABLE_CACHE,
            "l1": self.l1.get_stats(),
            "l2": self.l2.get_stats(),
            "overall": self._calculate_overall_stats()
        }
    
    def _calculate_overall_stats(self) -> Dict:
        """计算整体统计"""
        l1_stats = self.l1.get_stats()
        l2_stats = self.l2.get_stats()
        
        total_hits = l1_stats["hit_count"] + l2_stats["hit_count"]
        total_miss = l1_stats["miss_count"] + l2_stats["miss_count"]
        total = total_hits + total_miss
        
        return {
            "total_requests": total,
            "total_hits": total_hits,
            "total_misses": total_miss,
            "overall_hit_rate": f"{total_hits/total:.2%}" if total > 0 else "N/A"
        }


# 全局单例
cache_manager = CacheManager()


# 便捷函数
async def get_cache(key_prefix: str, *args, **kwargs) -> Optional[Any]:
    """便捷获取缓存"""
    return await cache_manager.get(key_prefix, *args, **kwargs)

async def set_cache(key_prefix: str, value: Any, *args, ttl: int = 3600, **kwargs):
    """便捷设置缓存"""
    await cache_manager.set(key_prefix, value, *args, ttl=ttl, **kwargs)

async def delete_cache(key_prefix: str, *args, **kwargs):
    """便捷删除缓存"""
    await cache_manager.delete(key_prefix, *args, **kwargs)
