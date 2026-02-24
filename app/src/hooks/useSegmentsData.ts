// app/src/hooks/useSegmentsData.ts
import { useState, useEffect } from 'react';
import { SegmentsData } from '@/types/segments';

interface UseSegmentsDataResult {
  data: SegmentsData | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

async function decompressGzip(buffer: ArrayBuffer): Promise<string> {
  // Use DecompressionStream if available (modern browsers)
  if ('DecompressionStream' in window) {
    const stream = new Response(buffer).body;
    if (!stream) throw new Error('No stream available');

    const decompressedStream = stream.pipeThrough(
      new DecompressionStream('gzip')
    );

    const reader = decompressedStream.getReader();
    const chunks: Uint8Array[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }

    const decompressed = new Uint8Array(chunks.reduce((acc, chunk) => acc + chunk.length, 0));
    let offset = 0;
    for (const chunk of chunks) {
      decompressed.set(chunk, offset);
      offset += chunk.length;
    }

    return new TextDecoder().decode(decompressed);
  }

  // Fallback: assume response was already decompressed by browser
  return new TextDecoder().decode(buffer);
}

export function useSegmentsData(): UseSegmentsDataResult {
  const [data, setData] = useState<SegmentsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${import.meta.env.BASE_URL}data/segments_enhanced.json.gz`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const buffer = await response.arrayBuffer();
      const textStr = await decompressGzip(buffer);
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
