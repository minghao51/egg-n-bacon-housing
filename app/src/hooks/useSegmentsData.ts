// app/src/hooks/useSegmentsData.ts
import { useGzipJson } from './useGzipJson';
import type { SegmentsData } from '@/types/segments';
import { DATA_URLS } from '@/constants/data-urls';

export function useSegmentsData() {
  return useGzipJson<SegmentsData>(DATA_URLS.segments, 'segments');
}
