/**
 * Unit tests for the S8 tool URL contract
 * (src/components/tools/lib/tool-url-state.ts).
 *
 * The workspace must read the address bar before its first commit, so parsing
 * is total (unknown values fall back, never throw) and a partial or malformed
 * reference is ignored instead of importing the wrong area's price.
 */

import { describe, expect, test } from "bun:test";

import {
  applyToolQuery,
  DEFAULT_TOOL_STATE,
  parseToolQuery,
  serializeToolQuery,
  TOOL_QUERY_KEYS,
  type ToolQueryState,
} from "../../src/components/tools/lib/tool-url-state";

const LEASE_STATE: ToolQueryState = {
  tool: "lease",
  reference: { area: "TAMPINES", property: "hdb" },
};

describe("parseToolQuery", () => {
  test("an empty query string is the documented default", () => {
    expect(parseToolQuery("")).toEqual(DEFAULT_TOOL_STATE);
    expect(parseToolQuery("?")).toEqual(DEFAULT_TOOL_STATE);
  });

  test("reads a tool and a complete named reference", () => {
    expect(parseToolQuery("?tool=mrt&ref=TAMPINES&rt=condo&rv=1")).toEqual({
      tool: "mrt",
      reference: { area: "TAMPINES", property: "condo" },
    });
  });

  test("an unknown tool falls back to financing without throwing", () => {
    expect(parseToolQuery("?tool=hotspots")).toEqual(DEFAULT_TOOL_STATE);
    expect(parseToolQuery("?tool=")).toEqual(DEFAULT_TOOL_STATE);
  });

  test("a partial or unversioned reference is ignored", () => {
    expect(parseToolQuery("?ref=TAMPINES").reference).toBeNull();
    expect(parseToolQuery("?ref=TAMPINES&rt=hdb").reference).toBeNull();
    expect(parseToolQuery("?ref=&rt=hdb&rv=1").reference).toBeNull();
    expect(parseToolQuery("?ref=TAMPINES&rt=landed&rv=1").reference).toBeNull();
    expect(parseToolQuery("?ref=TAMPINES&rt=hdb&rv=2").reference).toBeNull();
  });

  test("the area is canonicalised to uppercase", () => {
    expect(parseToolQuery("?ref=ang%20mo%20kio&rt=hdb&rv=1").reference).toEqual(
      {
        area: "ANG MO KIO",
        property: "hdb",
      },
    );
  });
});

describe("serializeToolQuery", () => {
  test("omits defaults", () => {
    expect(serializeToolQuery(DEFAULT_TOOL_STATE)).toBe("");
  });

  test("writes the tool and the versioned reference", () => {
    expect(serializeToolQuery(LEASE_STATE)).toBe(
      "tool=lease&ref=TAMPINES&rt=hdb&rv=1",
    );
  });

  test("round-trips", () => {
    const parsed = parseToolQuery(`?${serializeToolQuery(LEASE_STATE)}`);
    expect(parsed).toEqual(LEASE_STATE);
  });
});

describe("applyToolQuery", () => {
  test("replaces its own keys and keeps parameters owned by others", () => {
    const href = applyToolQuery(
      "https://example.test/research/tools?tool=lease&utm_source=news&area=BISHAN",
      LEASE_STATE,
    );
    const url = new URL(href);
    expect(url.searchParams.get("tool")).toBe("lease");
    expect(url.searchParams.get("ref")).toBe("TAMPINES");
    expect(url.searchParams.get("rt")).toBe("hdb");
    expect(url.searchParams.get("rv")).toBe("1");
    // Not ours: left alone.
    expect(url.searchParams.get("utm_source")).toBe("news");
    expect(url.searchParams.get("area")).toBe("BISHAN");
  });

  test("every owned key is removable when the state returns to defaults", () => {
    const href = applyToolQuery(
      "https://example.test/dashboard/trends?tool=spatial&ref=BISHAN&rt=ec&rv=1&keep=1",
      DEFAULT_TOOL_STATE,
    );
    const url = new URL(href);
    for (const key of TOOL_QUERY_KEYS) {
      expect(url.searchParams.has(key)).toBe(false);
    }
    expect(url.searchParams.get("keep")).toBe("1");
  });

  test("an unparseable href is returned untouched", () => {
    expect(applyToolQuery("not a url", LEASE_STATE)).toBe("not a url");
  });
});
