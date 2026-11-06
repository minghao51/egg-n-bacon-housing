/**
 * Payload and hydration report for the built root site (S10).
 *
 * Run after `bun run build`:
 *
 *   bun run measure:payload
 *
 * For each shipped route it reports gzipped HTML, the unique gzipped JS/CSS
 * chunks the HTML references, how many Astro islands hydrate and with which
 * directive, and the size of the SSR island props embedded in the HTML. This is
 * a measurement, not a budget: it records what the release ships so a later
 * slice can compare, and it never fetches data assets at runtime.
 */

import { readFileSync, existsSync } from "node:fs";
import { gzipSync } from "node:zlib";
import path from "node:path";

const DIST = path.resolve(process.cwd(), "dist");

const ROUTES = [
  ["/", "index.html"],
  ["/dashboard/", "dashboard/index.html"],
  ["/dashboard/map/", "dashboard/map/index.html"],
  ["/dashboard/trends/", "dashboard/trends/index.html"],
  ["/dashboard/segments/", "dashboard/segments/index.html"],
  ["/dashboard/leaderboard/", "dashboard/leaderboard/index.html"],
  ["/explore/", "explore/index.html"],
  ["/research/trends/", "research/trends/index.html"],
  ["/research/map/", "research/map/index.html"],
  ["/research/tools/", "research/tools/index.html"],
  ["/research/segments/", "research/segments/index.html"],
  ["/analytics/", "analytics/index.html"],
  ["/analytics/lease-decay/", "analytics/lease-decay/index.html"],
  ["/catalog/", "catalog/index.html"],
  [
    "/catalog/platinum/unified_dataset/",
    "catalog/platinum/unified_dataset/index.html",
  ],
  ["/areas/bishan/", "areas/bishan/index.html"],
];

function resolveSpecifier(importer, spec) {
  if (!spec || spec.startsWith("http")) return null;
  return spec.startsWith("/")
    ? spec
    : path.posix.join(path.posix.dirname(importer), spec);
}

function gzipBytes(buffer) {
  return gzipSync(buffer).length;
}

function decodeAttribute(value) {
  return value
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&amp;", "&");
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} kB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function assetSize(reference) {
  const clean = reference.split("?")[0].replace(/^\//, "");
  const file = path.join(DIST, clean);
  if (!existsSync(file)) return null;
  const bytes = readFileSync(file);
  return { raw: bytes.length, gzip: gzipBytes(bytes) };
}

const rows = [];

for (const [route, relative] of ROUTES) {
  const file = path.join(DIST, relative);
  if (!existsSync(file)) {
    rows.push({ route, missing: true });
    continue;
  }
  const html = readFileSync(file);
  const text = html.toString("utf8");

  // Collect every `_astro` reference in the HTML (script src, modulepreload,
  // island component/renderer URLs), then follow static imports. Dynamic
  // imports are code-split on purpose and are counted separately.
  const references = new Set(
    [...text.matchAll(/\/_astro\/[A-Za-z0-9._-]+\.(?:js|css)/g)].map(
      (match) => match[0],
    ),
  );
  const entryScripts = [...references].filter((ref) => ref.endsWith(".js"));
  const styles = [...references].filter((ref) => ref.endsWith(".css"));

  // Static graph: every `_astro` script referenced by the HTML plus its
  // static imports. Dynamic imports are code-split on purpose; resolve their
  // closure separately and subtract anything already in the static set so the
  // two payload columns are disjoint.
  const staticSeen = new Set();
  const staticQueue = [...entryScripts];
  while (staticQueue.length > 0) {
    const ref = staticQueue.shift();
    if (!ref || staticSeen.has(ref)) continue;
    const clean = ref.split("?")[0];
    const file = path.join(DIST, clean.replace(/^\//, ""));
    if (!existsSync(file)) continue;
    staticSeen.add(ref);
    const source = readFileSync(file, "utf8");
    for (const match of source.matchAll(
      /(?:from|import)\s*["']([^"']+\.js)["']/g,
    )) {
      const spec = resolveSpecifier(clean, match[1]);
      if (spec) staticQueue.push(spec);
    }
  }

  const lazySeen = new Set();
  const lazyQueue = [];
  const enqueueDynamic = (clean, source) => {
    for (const match of source.matchAll(/import\(\s*["']([^"']+\.js)["']/g)) {
      const spec = resolveSpecifier(clean, match[1]);
      if (spec && !staticSeen.has(spec)) lazyQueue.push(spec);
    }
  };
  for (const ref of staticSeen) {
    const clean = ref.split("?")[0];
    enqueueDynamic(
      clean,
      readFileSync(path.join(DIST, clean.replace(/^\//, "")), "utf8"),
    );
  }
  while (lazyQueue.length > 0) {
    const ref = lazyQueue.shift();
    if (!ref || lazySeen.has(ref) || staticSeen.has(ref)) continue;
    const clean = ref.split("?")[0];
    const file = path.join(DIST, clean.replace(/^\//, ""));
    if (!existsSync(file)) continue;
    lazySeen.add(ref);
    const source = readFileSync(file, "utf8");
    enqueueDynamic(clean, source);
    // Lazy chunks may also statically import modules not in the entry graph.
    for (const match of source.matchAll(
      /(?:from|import)\s*["']([^"']+\.js)["']/g,
    )) {
      const spec = resolveSpecifier(clean, match[1]);
      if (spec) lazyQueue.push(spec);
    }
  }
  const lazyOnly = [...lazySeen].filter((ref) => !staticSeen.has(ref));

  const scripts = [...staticSeen];

  const js = scripts.reduce(
    (total, ref) => total + (assetSize(ref)?.gzip ?? 0),
    0,
  );
  const css = styles.reduce(
    (total, ref) => total + (assetSize(ref)?.gzip ?? 0),
    0,
  );
  const dynamicGzip = lazyOnly.reduce(
    (total, ref) => total + (assetSize(ref)?.gzip ?? 0),
    0,
  );

  const islands = [...text.matchAll(/<astro-island\b([^>]*)>/g)].map(
    (match) => {
      const attributes = match[1];
      const client = /client="([^"]+)"/.exec(attributes)?.[1] ?? "none";
      const props = /props="([^"]*)"/.exec(attributes)?.[1] ?? "";
      return {
        client,
        propsBytes: Buffer.byteLength(decodeAttribute(props), "utf8"),
      };
    },
  );

  const clientCounts = {};
  for (const island of islands) {
    clientCounts[island.client] = (clientCounts[island.client] ?? 0) + 1;
  }

  rows.push({
    route,
    htmlRaw: html.length,
    htmlGzip: gzipBytes(html),
    jsGzip: js,
    cssGzip: css,
    jsChunks: scripts.length,
    cssChunks: styles.length,
    lazyChunks: lazyOnly.length,
    lazyGzip: dynamicGzip,
    islands: islands.length,
    clientCounts,
    propsBytes: islands.reduce((total, island) => total + island.propsBytes, 0),
  });
}

const headers = [
  "route",
  "HTML gz",
  "JS gz",
  "CSS gz",
  "JS chunks",
  "lazy extra",
  "islands (load/only/visible/idle)",
  "SSR props",
];

console.log(`\nPayload report — ${ROUTES.length} routes, gzip sizes\n`);
const widths = [30, 9, 9, 9, 10, 10, 30, 10];
console.log(
  headers.map((header, index) => header.padEnd(widths[index])).join(" "),
);
console.log(widths.map((width) => "-".repeat(width)).join(" "));

for (const row of rows) {
  if (row.missing) {
    console.log(`${row.route.padEnd(widths[0])} MISSING`);
    continue;
  }
  const clients = ["load", "only", "visible", "idle"]
    .map((key) =>
      row.clientCounts[key] ? `${key}:${row.clientCounts[key]}` : null,
    )
    .filter(Boolean)
    .join(" ");
  console.log(
    [
      row.route.padEnd(widths[0]),
      formatBytes(row.htmlGzip).padEnd(widths[1]),
      formatBytes(row.jsGzip).padEnd(widths[2]),
      formatBytes(row.cssGzip).padEnd(widths[3]),
      String(row.jsChunks).padEnd(widths[4]),
      `${row.lazyChunks} / ${formatBytes(row.lazyGzip)}`.padEnd(widths[5]),
      `${row.islands} (${clients || "none"})`.padEnd(widths[6]),
      formatBytes(row.propsBytes).padEnd(widths[7]),
    ].join(" "),
  );
}

if (process.argv.includes("--json")) {
  console.log(JSON.stringify(rows, null, 2));
}
