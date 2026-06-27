import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const source = fileURLToPath(
  new URL("../../data/catalog/catalog.jsonl", import.meta.url),
);
const target = fileURLToPath(
  new URL("../public/data/catalog.jsonl.gz", import.meta.url),
);

if (!existsSync(source)) {
  console.error(`[sync-catalog] source catalog not found: ${source}`);
  process.exit(1);
}

mkdirSync(dirname(target), { recursive: true });
const compressed = gzipSync(readFileSync(source));
writeFileSync(target, compressed);
console.log(`[sync-catalog] wrote ${target} (${compressed.length} bytes)`);
