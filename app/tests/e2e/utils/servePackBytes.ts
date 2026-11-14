import { readFileSync } from "node:fs";
import path from "node:path";

import type { Page } from "@playwright/test";

/**
 * Serve the v2 pack payloads from disk for the published-window tests.
 *
 * `astro preview` runs Vite's static server, which labels every `.gz` response
 * with `Content-Encoding: gzip`; Chromium then inflates the file before the
 * loader can hash it, so a pinned sha256 can never match in preview. The
 * deployed static host (and `scripts/serve-pages-base.mjs`) serves the same
 * files as opaque bytes. This route fulfils exactly the bytes on disk, so the
 * manifest, size, sha256 and parser checks all stay in the path under test.
 */
export async function servePackBytesFromDisk(page: Page): Promise<void> {
  const dataDir = path.resolve("public/data");
  await page.route("**/data/observed/**", async (route) => {
    const { pathname } = new URL(route.request().url());
    const marker = "/data/";
    const relative = pathname.slice(pathname.indexOf(marker) + marker.length);
    await route.fulfill({
      status: 200,
      body: readFileSync(path.join(dataDir, relative)),
      headers: {
        "content-type": "application/gzip",
        "cache-control": "no-store",
      },
    });
  });
}
