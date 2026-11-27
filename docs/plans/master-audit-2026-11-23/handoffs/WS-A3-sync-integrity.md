# WS-A3 — R2 sync integrity and containment (CORE-3, CORE-4)

**Severity:** HIGH (4×4 = 16) + MEDIUM (4×2 = 8). **Effort:** M. **Wave:** 1.

## Problem

`scripts/00_sync_data.py` compares only file sizes with a 100-byte tolerance in every direction, and maps remote object keys straight onto local paths.

- `:42` `_SIZE_TOLERANCE_BYTES = 100`.
- `:121-127` upload skips when sizes are within tolerance; `:170-179` download skips likewise; `:232-239` `verify` counts within-tolerance differences as `OK`.
- `:167`, `:216` `rel = key.removeprefix(prefix + "/")`; `:191-194` writes `MANUAL_DATA_DIR / rel` or `CACHE_DIR / rel` with no containment check.
- Probe: `../evidence/core-poc-results.json` → `size_integrity` (8 vs 10 bytes → 0 transfers, "1 OK") and `containment` (`manual/../escaped.txt` escaped the root; `geocache/hamilton/injected.json` wrote into the excluded subtree).

## Required change

1. **Containment (do this first — small and safe).** Add one resolver used by both download and verify:
   - require the key to start with `prefix + "/"` and the remainder to be non-empty;
   - reject `..` segments, absolute remainders, empty segments and (for `geocache/`) anything with a directory component;
   - resolve the candidate path and require it to stay under the resolved root, following symlinks;
   - reject before any transfer is submitted, and log the rejected key.
2. **Content verification without a mass re-transfer.** Keep size as a fast pre-filter, but stop calling size equality "OK":
   - `verify` prints `SIZE-OK / CONTENT-UNVERIFIED` (or equivalent) rather than `OK`, and a new `--verify-content` (or `--check-content`) downloads and compares bytes (or compares a recorded SHA-256 when present) for the selected scope;
   - upload records a per-object content hash where the provider supports metadata; if not supported, document that limitation rather than implying content equality.
3. **Never silently skip a known difference.** A difference ≥ 1 byte must be reported by `verify`; only `--apply`/normal sync keeps the size skip for speed, and it must say so in its summary line.
4. **Correct the summary semantics.** `0 size mismatches` must not be printable when unverified content exists.

Keep `_TRANSFER_CONCURRENCY`, retry-free semantics and the idempotent "skip what matches" behaviour — this is a correctness change, not a redesign.

## Tests (`tests/test_sync_data.py`, mocked transport only)

- Different-size changes of 1, 99, 100 bytes and equal-size differing content: none classified unchanged in content mode; size mode reports the ≥1-byte ones.
- Traversal key, absolute remainder, prefix sibling, nested `geocache/hamilton/...`, escaping symlink: all rejected with no `download_file` call.
- Successful scoped sync unchanged (existing 8 tests stay green).

## Verification

```bash
uv run pytest tests/test_sync_data.py --no-cov -q
uv run ruff check . && uv run ruff format --check .
```

## Owns

`scripts/00_sync_data.py`, `tests/test_sync_data.py`, `docs/guides/r2-sync-guide.md` (document the new modes).

## Do not touch

`data/` contents, credentials, `utils/bronze.py`, `utils/cache.py`.

## Done when

A key can never write outside its root, `verify` cannot report unverified content as OK, content mode detects all four divergence classes, and the mocked suite is green.
