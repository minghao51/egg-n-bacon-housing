/**
 * Static server for the GitHub Pages build (S10).
 *
 * `ASTRO_PAGES=true bun run build` emits `dist/` with every URL and asset
 * prefixed by `/egg-n-bacon-housing/`. `astro preview` cannot serve that layout,
 * so release verification mounts `dist/` under the same prefix:
 *
 *   PLAYWRIGHT_PAGES_PORT=4402 node scripts/serve-pages-base.mjs
 *
 * Paths outside the prefix 404 (a root-relative link is therefore a real
 * failure, not something the server papers over). `.gz` assets are served as
 * raw `application/gzip` bytes, matching the host contract `fetchGzipJson`
 * expects; the server never sets `Content-Encoding`.
 */

import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import path from "node:path";

const BASE = "/egg-n-bacon-housing";
const PORT = Number(process.env.PLAYWRIGHT_PAGES_PORT ?? 4402);
const ROOT = path.resolve(process.cwd(), "dist");

const MIME = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".jsonl", "application/json; charset=utf-8"],
  [".geojson", "application/geo+json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".webp", "image/webp"],
  [".ico", "image/x-icon"],
  [".woff2", "font/woff2"],
  [".woff", "font/woff"],
  [".gz", "application/gzip"],
  [".webm", "video/webm"],
  [".txt", "text/plain; charset=utf-8"],
]);

function resolveFile(relativePath) {
  const withoutPrefix = relativePath.replace(new RegExp(`^${BASE}`), "");
  const candidates =
    withoutPrefix.endsWith("/") || withoutPrefix === ""
      ? [`${withoutPrefix}index.html`]
      : [withoutPrefix, `${withoutPrefix}/index.html`, `${withoutPrefix}.html`];

  for (const candidate of candidates) {
    const full = path.resolve(ROOT, `.${candidate}`);
    const relative = path.relative(ROOT, full);
    // A path boundary, not a string prefix: a sibling such as `dist-secret`
    // must not pass the containment check.
    if (relative.startsWith("..") || path.isAbsolute(relative)) continue;
    if (existsSync(full) && statSync(full).isFile()) return full;
  }
  return null;
}

const server = createServer((request, response) => {
  const url = new URL(request.url ?? "/", `http://${request.headers.host}`);
  let pathname;
  try {
    pathname = decodeURIComponent(url.pathname);
  } catch {
    response.writeHead(400).end("Bad request");
    return;
  }

  if (pathname === "/" || pathname === BASE) {
    response.writeHead(302, { Location: `${BASE}/` });
    response.end();
    return;
  }

  if (!pathname.startsWith(`${BASE}/`)) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end(
      `Not found: ${pathname}. The Pages build only serves ${BASE}/.`,
    );
    return;
  }

  const file = resolveFile(pathname);
  if (!file) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end(`Not found: ${pathname}`);
    return;
  }

  const type = MIME.get(path.extname(file)) ?? "application/octet-stream";
  response.writeHead(200, {
    "Content-Type": type,
    "Cache-Control": "no-store",
  });
  createReadStream(file).pipe(response);
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[pages] serving ${ROOT} at http://127.0.0.1:${PORT}${BASE}/`);
});
