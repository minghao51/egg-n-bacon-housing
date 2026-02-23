// app/src/hooks/useSegmentsData.ts
import { useState, useEffect } from 'react';
import { SegmentsData } from '@/types/segments';

interface UseSegmentsDataResult {
  data: SegmentsData | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useSegmentsData(): UseSegmentsDataResult {
  const [data, setData] = useState<SegmentsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/data/segments_enhanced.json.gz');

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Browser will automatically decompress gzip-encoded responses
      const textStr = await response.text();
      const parsed = JSON.parse(textStr);

      setData(parsed);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error('Failed to load segments data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return {
    data,
    loading,
    error,
    reload: loadData,
  };
}
