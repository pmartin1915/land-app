// Intelligent caching system for API responses
// Provides multi-tier caching with TTL, memory optimization, and invalidation

import localforage from 'localforage'

export interface CacheItem<T = unknown> {
  data: T
  timestamp: number
  ttl: number // Time to live in milliseconds
  key: string
  tags?: string[] // For grouped invalidation
}

export interface CacheConfig {
  namespace: string
  defaultTTL: number
  maxMemoryItems: number
  enablePersistent: boolean
}

export class CacheManager {
  private memoryCache = new Map<string, CacheItem>()
  private persistentStore: LocalForage | null = null
  private config: CacheConfig
  private cleanupInterval: NodeJS.Timeout | null = null

  constructor(config: Partial<CacheConfig> = {}) {
    this.config = {
      namespace: 'aaw-cache',
      defaultTTL: 5 * 60 * 1000, // 5 minutes
      maxMemoryItems: 1000,
      enablePersistent: true,
      ...config
    }

    if (this.config.enablePersistent) {
      this.initPersistentStore()
    }

    // Start cleanup interval
    this.startCleanup()
  }

  private async initPersistentStore() {
    try {
      this.persistentStore = localforage.createInstance({
        name: this.config.namespace,
        storeName: 'cache'
      })
    } catch (error) {
      console.warn('Failed to initialize persistent cache:', error)
      this.persistentStore = null
    }
  }

  private startCleanup() {
    // Clean up expired items every minute
    this.cleanupInterval = setInterval(() => {
      this.cleanup()
    }, 60 * 1000)
  }

  private cleanup() {
    const now = Date.now()
    const keysToDelete: string[] = []

    // Clean memory cache
    for (const [key, item] of this.memoryCache.entries()) {
      if (now > item.timestamp + item.ttl) {
        keysToDelete.push(key)
      }
    }

    keysToDelete.forEach(key => this.memoryCache.delete(key))

    // Limit memory cache size
    if (this.memoryCache.size > this.config.maxMemoryItems) {
      const sortedEntries = Array.from(this.memoryCache.entries())
        .sort(([, a], [, b]) => a.timestamp - b.timestamp)

      const itemsToRemove = this.memoryCache.size - this.config.maxMemoryItems
      for (let i = 0; i < itemsToRemove; i++) {
        this.memoryCache.delete(sortedEntries[i][0])
      }
    }
  }

  private generateKey(prefix: string, params?: Record<string, unknown>): string {
    if (!params) return prefix

    // Create deterministic key from parameters
    const paramString = JSON.stringify(params, Object.keys(params).sort())
    return `${prefix}:${btoa(paramString).replace(/[+=/]/g, '')}`
  }

  // Get item from cache (memory first, then persistent)
  async get<T>(key: string): Promise<T | null> {
    const now = Date.now()

    // Check memory cache first
    const memoryItem = this.memoryCache.get(key)
    if (memoryItem && now <= memoryItem.timestamp + memoryItem.ttl) {
      return memoryItem.data as T
    }

    // Remove expired memory item
    if (memoryItem) {
      this.memoryCache.delete(key)
    }

    // Check persistent cache
    if (this.persistentStore) {
      try {
        const persistentItem = await this.persistentStore.getItem<CacheItem<T>>(key)
        if (persistentItem && now <= persistentItem.timestamp + persistentItem.ttl) {
          // Promote to memory cache
          this.memoryCache.set(key, persistentItem)
          return persistentItem.data
        }

        // Remove expired persistent item
        if (persistentItem) {
          await this.persistentStore.removeItem(key)
        }
      } catch (error) {
        console.warn('Failed to read from persistent cache:', error)
      }
    }

    return null
  }

  // Set item in cache
  async set<T>(key: string, data: T, ttl?: number, tags?: string[]): Promise<void> {
    const item: CacheItem<T> = {
      data,
      timestamp: Date.now(),
      ttl: ttl ?? this.config.defaultTTL,
      key,
      tags
    }

    // Store in memory cache
    this.memoryCache.set(key, item)

    // Store in persistent cache
    if (this.persistentStore) {
      try {
        await this.persistentStore.setItem(key, item)
      } catch (error) {
        console.warn('Failed to write to persistent cache:', error)
      }
    }
  }

  // Remove specific item
  async remove(key: string): Promise<void> {
    this.memoryCache.delete(key)

    if (this.persistentStore) {
      try {
        await this.persistentStore.removeItem(key)
      } catch (error) {
        console.warn('Failed to remove from persistent cache:', error)
      }
    }
  }

  // Clear all cache items
  async clear(): Promise<void> {
    this.memoryCache.clear()

    if (this.persistentStore) {
      try {
        await this.persistentStore.clear()
      } catch (error) {
        console.warn('Failed to clear persistent cache:', error)
      }
    }
  }

  // Invalidate by tags
  async invalidateByTags(tags: string[]): Promise<void> {
    const keysToDelete: string[] = []

    // Check memory cache
    for (const [key, item] of this.memoryCache.entries()) {
      if (item.tags && item.tags.some(tag => tags.includes(tag))) {
        keysToDelete.push(key)
      }
    }

    // Remove from memory
    keysToDelete.forEach(key => this.memoryCache.delete(key))

    // Check persistent cache
    if (this.persistentStore) {
      try {
        const keys = await this.persistentStore.keys()
        for (const key of keys) {
          const item = await this.persistentStore.getItem<CacheItem>(key)
          if (item?.tags && item.tags.some(tag => tags.includes(tag))) {
            await this.persistentStore.removeItem(key)
          }
        }
      } catch (error) {
        console.warn('Failed to invalidate persistent cache by tags:', error)
      }
    }
  }

  // Get cache statistics
  async getStats(): Promise<{
    memorySize: number
    persistentSize: number
    hitRatio: number
    totalItems: number
  }> {
    let persistentSize = 0

    if (this.persistentStore) {
      try {
        const keys = await this.persistentStore.keys()
        persistentSize = keys.length
      } catch (error) {
        console.warn('Failed to get persistent cache size:', error)
      }
    }

    return {
      memorySize: this.memoryCache.size,
      persistentSize,
      hitRatio: 0, // TODO: Implement hit ratio tracking
      totalItems: this.memoryCache.size + persistentSize
    }
  }

  // Wrapper methods for common caching patterns
  async cached<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl?: number,
    tags?: string[]
  ): Promise<T> {
    // Try to get from cache first
    const cached = await this.get<T>(key)
    if (cached !== null) {
      return cached
    }

    // Fetch and cache the data
    const data = await fetcher()
    await this.set(key, data, ttl, tags)
    return data
  }

  // Create a memoized version of an async function
  memoize<T extends unknown[], R>(
    fn: (...args: T) => Promise<R>,
    keyGenerator: (...args: T) => string,
    ttl?: number,
    tags?: string[]
  ) {
    return async (...args: T): Promise<R> => {
      const key = keyGenerator(...args)
      return this.cached(key, () => fn(...args), ttl, tags)
    }
  }

  // Destroy cache manager
  destroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval)
      this.cleanupInterval = null
    }
    this.memoryCache.clear()
  }
}

// Global cache instance
export const globalCache = new CacheManager({
  namespace: 'alabama-auction-watcher',
  defaultTTL: 5 * 60 * 1000, // 5 minutes
  maxMemoryItems: 1000,
  enablePersistent: true
})

// Specialized cache instances for different data types
export const propertyCache = new CacheManager({
  namespace: 'aaw-properties',
  defaultTTL: 10 * 60 * 1000, // 10 minutes for property data
  maxMemoryItems: 500,
  enablePersistent: true
})

export const uiCache = new CacheManager({
  namespace: 'aaw-ui',
  defaultTTL: 30 * 60 * 1000, // 30 minutes for UI data
  maxMemoryItems: 200,
  enablePersistent: false // UI data doesn't need persistence
})

// Cache utility functions
export const createCacheKey = (prefix: string, params?: Record<string, unknown>): string => {
  if (!params) return prefix

  const paramString = JSON.stringify(params, Object.keys(params).sort())
  return `${prefix}:${btoa(paramString).replace(/[+=/]/g, '')}`
}

export const invalidatePropertyCache = async (): Promise<void> => {
  await propertyCache.invalidateByTags(['properties'])
}

export const invalidateCountyCache = async (): Promise<void> => {
  await globalCache.invalidateByTags(['counties'])
}

// Hook for cache invalidation on filter changes
export const useFilterCache = () => {
  const invalidateOnFilterChange = async (filters: Record<string, unknown>) => {
    // Invalidate cached results when filters change
    const filterTags = Object.keys(filters).map(key => `filter:${key}`)
    await propertyCache.invalidateByTags(filterTags)
  }

  return { invalidateOnFilterChange }
}

// Performance monitoring
export const trackCachePerformance = () => {
  let hits = 0
  let misses = 0

  return {
    recordHit: () => hits++,
    recordMiss: () => misses++,
    getStats: () => ({
      hits,
      misses,
      hitRatio: hits + misses > 0 ? hits / (hits + misses) : 0
    }),
    reset: () => {
      hits = 0
      misses = 0
    }
  }
}