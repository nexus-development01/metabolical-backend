#!/usr/bin/env python3
"""
Cache Manager for Metabolical Backend
Implements in-memory caching with TTL and background refresh to improve performance
"""

import json
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheManager:
    """Thread-safe in-memory cache with TTL and background refresh"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default TTL
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cache-refresh")
        self._background_refresh_tasks: Dict[str, threading.Timer] = {}
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self._cleanup_thread.start()
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key in self._cache:
                cache_entry = self._cache[key]
                
                # Check if expired
                if datetime.now() > cache_entry['expires_at']:
                    del self._cache[key]
                    return None
                
                # Update access time for LRU-like behavior
                cache_entry['last_accessed'] = datetime.now()
                return cache_entry['value']
            
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        if ttl is None:
            ttl = self.default_ttl
            
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.now(),
                'last_accessed': datetime.now(),
                'ttl': ttl
            }
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
    
    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        return self.get(key) is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            now = datetime.now()
            total_entries = len(self._cache)
            expired_entries = sum(1 for entry in self._cache.values() if now > entry['expires_at'])
            
            return {
                'total_entries': total_entries,
                'active_entries': total_entries - expired_entries,
                'expired_entries': expired_entries,
                'cache_keys': list(self._cache.keys())
            }
    
    def set_with_refresh(self, key: str, value: Any, ttl: int, refresh_func: Callable, refresh_interval: int = None):
        """Set value with automatic background refresh"""
        self.set(key, value, ttl)
        
        if refresh_interval is None:
            refresh_interval = max(ttl // 2, 60)  # Refresh at half TTL or minimum 60 seconds
        
        # Cancel existing refresh task if any
        if key in self._background_refresh_tasks:
            self._background_refresh_tasks[key].cancel()
        
        # Schedule background refresh
        def refresh_task():
            try:
                new_value = refresh_func()
                self.set(key, new_value, ttl)
                logger.debug(f"Background refresh completed for cache key: {key}")
                
                # Schedule next refresh
                timer = threading.Timer(refresh_interval, refresh_task)
                timer.daemon = True
                timer.start()
                self._background_refresh_tasks[key] = timer
                
            except Exception as e:
                logger.error(f"Background refresh failed for cache key {key}: {e}")
        
        # Start initial refresh timer
        timer = threading.Timer(refresh_interval, refresh_task)
        timer.daemon = True
        timer.start()
        self._background_refresh_tasks[key] = timer
    
    def _cleanup_expired(self):
        """Background thread to cleanup expired entries"""
        while True:
            try:
                time.sleep(60)  # Run cleanup every minute
                
                with self._lock:
                    now = datetime.now()
                    expired_keys = [
                        key for key, entry in self._cache.items()
                        if now > entry['expires_at']
                    ]
                    
                    for key in expired_keys:
                        del self._cache[key]
                    
                    if expired_keys:
                        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                        
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

# Global cache instance
cache_manager = CacheManager(default_ttl=300)  # 5 minutes default

def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for {func.__name__}, result cached")
            
            return result
        return wrapper
    return decorator

def cached_async(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching async function results"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for {func.__name__}, result cached")
            
            return result
        return wrapper
    return decorator

class DatabaseCache:
    """Specialized cache for database operations"""
    
    def __init__(self):
        self.cache = cache_manager
        
    def get_articles_cache_key(self, page: int, limit: int, category: str = None, 
                              tag: str = None, search_query: str = None, 
                              sort_by: str = "desc") -> str:
        """Generate cache key for articles query"""
        params = {
            'page': page,
            'limit': limit,
            'category': category,
            'tag': tag,
            'search': search_query,
            'sort': sort_by
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return f"articles:{hash(str(sorted(params.items())))}"
    
    def cache_articles_result(self, key: str, result: Dict, ttl: int = 180):
        """Cache articles query result"""
        self.cache.set(key, result, ttl)
    
    def get_cached_articles(self, key: str) -> Optional[Dict]:
        """Get cached articles result"""
        return self.cache.get(key)
    
    def invalidate_articles_cache(self):
        """Invalidate all articles-related cache entries"""
        stats = self.cache.get_stats()
        article_keys = [key for key in stats['cache_keys'] if key.startswith('articles:')]
        
        for key in article_keys:
            self.cache.delete(key)
        
        logger.info(f"Invalidated {len(article_keys)} articles cache entries")

# Global database cache instance
db_cache = DatabaseCache()

# Cache warming functions
def warm_cache():
    """Warm up cache with frequently accessed data"""
    try:
        logger.info("Starting cache warming...")
        
        # Import here to avoid circular imports
        from .utils import get_category_stats_cached, get_cached_stats
        
        # Warm up category stats
        get_category_stats_cached()
        
        # Warm up general stats
        get_cached_stats()
        
        logger.info("Cache warming completed")
        
    except Exception as e:
        logger.error(f"Cache warming failed: {e}")

def setup_cache_refresh():
    """Setup background cache refresh for critical data"""
    try:
        from .utils import get_category_stats_cached, get_cached_stats
        
        # Setup category stats refresh (every 5 minutes)
        cache_manager.set_with_refresh(
            key="category_stats",
            value=get_category_stats_cached(),
            ttl=600,  # 10 minutes
            refresh_func=get_category_stats_cached,
            refresh_interval=300  # Refresh every 5 minutes
        )
        
        # Setup general stats refresh (every 3 minutes)
        cache_manager.set_with_refresh(
            key="general_stats",
            value=get_cached_stats(),
            ttl=300,  # 5 minutes
            refresh_func=get_cached_stats,
            refresh_interval=180  # Refresh every 3 minutes
        )
        
        logger.info("Background cache refresh setup completed")
        
    except Exception as e:
        logger.error(f"Cache refresh setup failed: {e}")