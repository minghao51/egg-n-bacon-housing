// app/src/hooks/useSegmentsData.ts
import { useState, useEffect } from 'react';
import { SegmentsData } from '@/types/segments';
import { fetchGzipJson } from '@/utils/gzip';

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
      const dataUrl = `${import.meta.env.BASE_URL}data/segments_enhanced.json.gz`;
      const parsed = await fetchGzipJson<SegmentsData>(dataUrl);
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
