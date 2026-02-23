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

      const compressed = await response.arrayBuffer();
      const decompressed = new Uint8Array(compressed);

      // Decompress using gzip
      const text = new Response(
        new Blob([decompressed], { type: 'application/gzip' })
      ).text();

      const textStr = await text;
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
