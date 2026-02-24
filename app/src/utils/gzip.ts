/**
 * Gzip decompression utility for handling compressed JSON data.
 *
 * This utility handles multiple decompression scenarios:
 * 1. Browser auto-decompression (GitHub Pages, some CDNs)
 * 2. Native DecompressionStream API (modern browsers)
 * 3. Fallback for unexpected formats
 */

/**
 * Decompress a gzip-compressed ArrayBuffer or return decoded text.
 *
 * @param buffer - The ArrayBuffer to decompress or decode
 * @returns Promise resolving to decompressed/decoded string
 * @throws Error if decompression fails completely
 */
export async function decompressGzip(buffer: ArrayBuffer): Promise<string> {
  // First, try to decode as text directly.
  // Some servers/browsers (like GitHub Pages) auto-decompress .gz files.
  try {
    const text = new TextDecoder().decode(buffer);
    // If it looks like valid JSON, return it
    const trimmed = text.trim();
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      return text;
    }
  } catch {
    // Not valid text, continue to decompression
  }

  // Use DecompressionStream if available (modern browsers)
  if ('DecompressionStream' in window) {
    try {
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

      // Combine all chunks into a single Uint8Array
      const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
      const decompressed = new Uint8Array(totalLength);
      let offset = 0;
      for (const chunk of chunks) {
        decompressed.set(chunk, offset);
        offset += chunk.length;
      }

      return new TextDecoder().decode(decompressed);
    } catch {
      // Decompression failed, fall back to text decoder
    }
  }

  // Final fallback: return as text (may be corrupted if gzip was expected)
  return new TextDecoder().decode(buffer);
}

/**
 * Fetch and decompress a gzip-compressed JSON file.
 *
 * @param url - The URL to fetch (should point to a .gz file)
 * @returns Promise resolving to parsed JSON object
 * @throws Error if fetch fails or JSON parsing fails
 */
export async function fetchGzipJson<T>(url: string): Promise<T> {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const buffer = await response.arrayBuffer();
  const text = await decompressGzip(buffer);
  return JSON.parse(text) as T;
}
