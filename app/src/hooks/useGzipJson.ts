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
  cacheEnabled: boolean = true,
  initialData?: T | null
): UseGzipJsonResult<T> {
  const [data, setData] = useState<T | null>(initialData ?? null);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const dataRef = useRef<T | null>(initialData ?? null);

  const key = cacheKey || url;

  const loadData = useCallback(async (background: boolean = false) => {
    // Check cache first
    if (cacheEnabled) {
      const cached = globalCache.get(key);
      if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        setData(cached.data as T);
        dataRef.current = cached.data as T;
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

    if (!background) {
      setLoading(true);
    }
    setError(null);

    try {
      const result = await fetchGzipJson<T>(url, abortControllerRef.current.signal);
      
      if (cacheEnabled) {
        globalCache.set(key, { data: result, timestamp: Date.now() });
      }
      
      setData(result);
      dataRef.current = result;
    } catch (err) {
      const hasExistingData = dataRef.current !== null;

      if (err instanceof Error) {
        if (err.name === 'AbortError') return;
        if (!background || !hasExistingData) {
          setError(err.message);
        }
      } else {
        if (!background || !hasExistingData) {
          setError('Failed to load data');
        }
      }

      if (!background || !hasExistingData) {
        setData(null);
        dataRef.current = null;
      }
    } finally {
      setLoading(false);
    }
  }, [url, key, cacheEnabled]);

  useEffect(() => {
    if (initialData) {
      loadData(true);
    } else {
      loadData();
    }

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [loadData, initialData]);

  return { data, loading, error, reload: loadData };
}

/**
 * Clear global cache (useful for testing or force refresh)
 */
export function clearGzipCache(): void {
  globalCache.clear();
}
