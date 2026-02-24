/**
 * Generic Gzip JSON Data Hook
 *
 * Reusable hook for loading gzipped JSON data with caching and error handling.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchGzipJson } from '@/utils/gzip';

interface UseGzipJsonResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

interface GzipJsonCache {
  data: unknown;
  timestamp: number;
}

const globalCache = new Map<string, GzipJsonCache>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

/**
 * Generic hook for loading gzipped JSON data
 *
 * @param url - URL of the gzipped JSON file
 * @param cacheKey - Optional cache key (defaults to URL)
 * @param cacheEnabled - Whether to enable caching (default: true)
 */
export function useGzipJson<T>(
  url: string,
  cacheKey?: string,
  cacheEnabled: boolean = true
): UseGzipJsonResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const key = cacheKey || url;

  const loadData = useCallback(async () => {
    // Check cache first
    if (cacheEnabled) {
      const cached = globalCache.get(key);
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        setData(cached.data as T);
        setLoading(false);
        setError(null);
        return;
      }
    }

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();

    setLoading(true);
    setError(null);

    try {
      const result = await fetchGzipJson<T>(url, abortControllerRef.current.signal);
      
      if (cacheEnabled) {
        globalCache.set(key, { data: result, timestamp: Date.now() });
      }
      
      setData(result);
    } catch (err) {
      if (err instanceof Error) {
        if (err.name === 'AbortError') return;
        setError(err.message);
      } else {
        setError('Failed to load data');
      }
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [url, key, cacheEnabled]);

  useEffect(() => {
    loadData();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadData]);

  return { data, loading, error, reload: loadData };
}

/**
 * Clear global cache (useful for testing or force refresh)
 */
export function clearGzipCache(): void {
  globalCache.clear();
}
