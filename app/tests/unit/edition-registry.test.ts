/**
 * Unit tests for the analytics edition registry (RF07).
 *
 * The registry is the only place edition identity, evidence status and archive
 * paths come from, so these tests pin it against the frozen sources on disk: a
 * renamed or missing frozen file, a duplicated edition or a reserved slug must
 * fail here rather than produce a wrong archive route.
 */

import { describe, expect, test } from "bun:test";
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import {
  ANALYTICS_EDITIONS,
  LEGACY_EDITION_ID,
  RESERVED_ANALYTICS_SLUGS,
  approvedEditionFor,
  archivePath,
  archiveYearSegment,
  editionsForSeries,
  signoffFor,
  validateEditionRegistry,
  verifyEditionArtifacts,
  type AnalyticsEdition,
  type EditionSignoff,
} from "../../src/components/studies/lib/edition-registry";

const FROZEN_DIR = join(
  process.cwd(),
  "..",
  "docs",
  "analytics",
  "editions",
  "legacy",
  "2026-11-12",
);

describe("edition registry matches the frozen sources", () => {
  test("every frozen study has exactly one registered identity", () => {
    const frozen = readdirSync(FROZEN_DIR)
      .filter((name) => name.endsWith(".md"))
      .map((name) => name.replace(/\.md$/, ""))
      .sort();
    const registered = ANALYTICS_EDITIONS.filter(
      (edition) => edition.editionId === LEGACY_EDITION_ID,
    )
      .map((edition) => edition.seriesSlug)
      .sort();

    expect(registered).toEqual(frozen);
    expect(new Set(registered).size).toBe(registered.length);
  });

  test("every frozen edition file on disk has exactly one identity", () => {
    // The archive route throws for a frozen file with no register entry, so this
    // pins the same invariant earlier and names every offender at once.
    const editionsRoot = join(
      process.cwd(),
      "..",
      "docs",
      "analytics",
      "editions",
    );
    const onDisk: string[] = [];
    for (const editionDir of readdirSync(editionsRoot, {
      withFileTypes: true,
    })) {
      if (!editionDir.isDirectory()) continue;
      const dirPath = join(editionsRoot, editionDir.name);
      for (const dateDir of readdirSync(dirPath, { withFileTypes: true })) {
        if (!dateDir.isDirectory()) continue;
        for (const file of readdirSync(join(dirPath, dateDir.name))) {
          if (!file.endsWith(".md")) continue;
          onDisk.push(
            `${editionDir.name}-${dateDir.name}|${file.replace(/\.md$/, "")}`,
          );
        }
      }
    }
    const registered = ANALYTICS_EDITIONS.map(
      (edition) => `${edition.editionId}|${edition.seriesSlug}`,
    );

    expect(onDisk.sort()).toEqual([...registered].sort());
    expect(new Set(registered).size).toBe(registered.length);
  });

  test("every registered edition points at a file that exists", () => {
    for (const edition of ANALYTICS_EDITIONS) {
      expect(existsSync(join(process.cwd(), "..", edition.frozenSource))).toBe(
        true,
      );
    }
  });

  test("the register validates and uses one legacy edition identity", () => {
    expect(validateEditionRegistry(ANALYTICS_EDITIONS)).toEqual([]);
    const legacy = ANALYTICS_EDITIONS.filter(
      (edition) => edition.editionId === LEGACY_EDITION_ID,
    );
    expect(legacy).toHaveLength(15);
    for (const edition of legacy) {
      expect(edition.publicationYear).toBe(2026);
      expect(edition.evidenceStatus).toBe("historical");
      expect(edition.editorialStatus).toBe("archived");
    }

    // A refreshed edition carries its own identity and is never the legacy id.
    for (const edition of ANALYTICS_EDITIONS) {
      if (edition.editionId === LEGACY_EDITION_ID) continue;
      expect(edition.editionId).toBe(
        `${edition.frozenSource.split("/").at(-3)}-${edition.frozenSource.split("/").at(-2)}`,
      );
    }
  });
});

describe("selection and paths", () => {
  test("only the signed series claim an approved current edition", () => {
    // RF08: data-sources, rental-yields and temporal-evolution are signed; the
    // other twelve studies stay historical until each has its own evidence pack
    // and three sign-offs.
    const approved = ANALYTICS_EDITIONS.filter(
      (edition) => edition.evidenceStatus === "approved",
    ).map((edition) => `${edition.seriesSlug}:${edition.editionId}`);

    expect(approved.sort()).toEqual([
      "data-sources:data-sources-2026-11-14",
      "rental-yields:rental-yields-2026-11-14",
      "temporal-evolution:temporal-evolution-2026-11-15",
    ]);
    for (const seriesSlug of ["mrt-impact", "lease-decay", "price-forecasts"]) {
      expect(approvedEditionFor(seriesSlug)).toBeNull();
    }
  });

  test("an approved edition is chosen over a newer unapproved one", () => {
    const series = "mrt-impact";
    const editions: AnalyticsEdition[] = [
      {
        seriesSlug: series,
        editionId: "2027-01-01",
        publicationYear: 2027,
        evidenceStatus: "historical",
        editorialStatus: "archived",
        frozenSource: "docs/analytics/editions/2027/mrt-impact.md",
        assetsPinned: 1,
        preparedBy: null,
        editionSha256: null,
        signoffs: [],
        note: "newer but unapproved",
      },
      {
        seriesSlug: series,
        editionId: "2026-06-01",
        publicationYear: 2026,
        evidenceStatus: "approved",
        editorialStatus: "published",
        frozenSource: "docs/analytics/editions/2026/mrt-impact.md",
        assetsPinned: 1,
        preparedBy: null,
        editionSha256: "c".repeat(64),
        signoffs: [],
        note: "approved",
      },
    ];

    expect(approvedEditionFor(series, editions)?.editionId).toBe("2026-06-01");
    expect(editionsForSeries(series, editions)[0]?.editionId).toBe(
      "2027-01-01",
    );
  });

  test("archive paths carry year, edition and series", () => {
    const legacy = ANALYTICS_EDITIONS[0]!;
    expect(archiveYearSegment(legacy)).toBe("2026");
    expect(archivePath(legacy)).toBe(
      `/analytics/archive/2026/${LEGACY_EDITION_ID}/${legacy.seriesSlug}`,
    );
    expect(archiveYearSegment({ publicationYear: null })).toBe("undated");
  });
});

describe("registry validation rejects bad identities", () => {
  const base: AnalyticsEdition = {
    seriesSlug: "mrt-impact",
    editionId: "legacy-2026-11-12",
    publicationYear: 2026,
    evidenceStatus: "historical",
    editorialStatus: "archived",
    frozenSource: "docs/analytics/editions/legacy/2026-11-12/mrt-impact.md",
    assetsPinned: 72,
    preparedBy: null,
    editionSha256: null,
    signoffs: [],
    note: "test",
  };

  test("rejects a reserved analytics segment", () => {
    const errors = validateEditionRegistry([
      { ...base, seriesSlug: RESERVED_ANALYTICS_SLUGS[0] },
    ]);
    expect(errors.join(" ")).toContain("reserved analytics segment");
  });

  test("rejects duplicate series + edition pairs", () => {
    const errors = validateEditionRegistry([base, { ...base }]);
    expect(errors.join(" ")).toContain("duplicate edition");
  });

  test("rejects malformed identifiers and years", () => {
    const errors = validateEditionRegistry([
      { ...base, seriesSlug: "MRT Impact" },
      {
        ...base,
        seriesSlug: "price-forecasts",
        editionId: " ",
        publicationYear: 1800,
      },
    ]).join(" ");

    expect(errors).toContain("is not a series slug");
    expect(errors).toContain("empty edition id");
    expect(errors).toContain("is not a publication year");
  });
});

/**
 * D12 approval record. An edition may only read `approved` when the register
 * carries three distinct attestations on one artifact hash: source/cutoff by a
 * non-preparer, scientific validity by a reviewer who is not the publication
 * approver, and publication by the release authority.
 */
describe("D12 sign-off record", () => {
  const HASH = "a".repeat(64);

  function signoff(
    role: "source" | "scientific" | "publication",
    overrides: Partial<EditionSignoff> = {},
  ): EditionSignoff {
    return {
      role,
      name:
        role === "scientific"
          ? "openai-codex/gpt-6-luna (xhigh)"
          : `owner-${role}`,
      date: "2026-11-14",
      artifactSha256: HASH,
      statement: `${role} attestation`,
      automated: role === "scientific",
      evidencePath: "docs/implementation/rs01-source-inventory.md",
      ...overrides,
    };
  }

  function approvedEdition(
    overrides: Partial<AnalyticsEdition> = {},
  ): AnalyticsEdition {
    return {
      seriesSlug: "data-sources",
      editionId: "rs01-2026-11-14",
      publicationYear: 2026,
      evidenceStatus: "approved",
      editorialStatus: "published",
      frozenSource: "docs/analytics/editions/rs01/2026-11-14/data-sources.md",
      assetsPinned: 4,
      preparedBy: "repo-agent/session-2026-11-14",
      editionSha256: "c".repeat(64),
      signoffs: [
        signoff("source"),
        signoff("scientific"),
        signoff("publication"),
      ],
      note: "RS01 inventory reviewed against the measured source ledger.",
      ...overrides,
    };
  }

  test("accepts a complete, distinct three-way record", () => {
    const edition = approvedEdition();
    expect(validateEditionRegistry([edition])).toEqual([]);
    expect(signoffFor(edition, "scientific")?.automated).toBe(true);
    expect(signoffFor(edition, "source")).not.toBeNull();
  });

  test("an approved edition is promoted by the series entry", () => {
    const approved = approvedEdition();
    expect(approvedEditionFor("data-sources", [approved])?.editionId).toBe(
      "rs01-2026-11-14",
    );
  });

  test("requires all three roles", () => {
    const errors = validateEditionRegistry([
      approvedEdition({
        signoffs: [signoff("source"), signoff("scientific")],
      }),
    ]).join(" ");

    expect(errors).toContain("missing its publication sign-off");
  });

  test("rejects a duplicate role", () => {
    const errors = validateEditionRegistry([
      approvedEdition({
        signoffs: [
          signoff("source"),
          signoff("source", { name: "someone-else" }),
          signoff("scientific"),
          signoff("publication"),
        ],
      }),
    ]).join(" ");

    expect(errors).toContain("duplicate source sign-off");
  });

  test("refuses self-approval by the preparer", () => {
    const errors = validateEditionRegistry([
      approvedEdition({
        signoffs: [
          signoff("source", { name: "repo-agent/session-2026-11-14" }),
          signoff("scientific"),
          signoff("publication"),
        ],
      }),
    ]).join(" ");

    expect(errors).toContain("preparer cannot approve their own evidence");
  });

  test("refuses the scientific reviewer as publication approver", () => {
    const errors = validateEditionRegistry([
      approvedEdition({
        signoffs: [
          signoff("source"),
          signoff("scientific"),
          signoff("publication", { name: "openai-codex/gpt-6-luna (xhigh)" }),
        ],
      }),
    ]).join(" ");

    expect(errors).toContain("may not also approve publication");
  });

  test("refuses signatures on different artifacts", () => {
    const errors = validateEditionRegistry([
      approvedEdition({
        signoffs: [
          signoff("source"),
          signoff("scientific"),
          signoff("publication", { artifactSha256: "b".repeat(64) }),
        ],
      }),
    ]).join(" ");

    expect(errors).toContain("do not all cover the same evidence artifact");
  });

  test("rejects a malformed attestation", () => {
    const errors = validateEditionRegistry([
      approvedEdition({
        signoffs: [
          signoff("source", {
            date: "14/11/2026",
            artifactSha256: "abc",
            statement: "",
          }),
          signoff("scientific"),
          signoff("publication"),
        ],
      }),
    ]).join(" ");

    expect(errors).toContain("is not YYYY-MM-DD");
    expect(errors).toContain("does not pin an evidence sha256");
    expect(errors).toContain("has no statement");
  });

  test("rejects sign-offs on an edition that is not approved", () => {
    const errors = validateEditionRegistry([
      {
        ...approvedEdition(),
        evidenceStatus: "historical",
        editorialStatus: "archived",
        editionSha256: null,
      },
    ]).join(" ");

    expect(errors).toContain(
      "an approval record exists only on an approved edition",
    );
  });

  test("the shipped register's claims match each edition's status", () => {
    for (const edition of ANALYTICS_EDITIONS) {
      if (edition.evidenceStatus === "approved") {
        expect(edition.signoffs).toHaveLength(3);
        expect(edition.editionSha256).not.toBeNull();
        expect(signoffFor(edition, "publication")?.name).toBe("howt");
        continue;
      }
      // Nothing unapproved may look approved: a partial record is a defect.
      expect(edition.signoffs).toEqual([]);
      expect(edition.editionSha256).toBeNull();
    }
    // Only a frozen historical edition may omit a preparer.
    for (const edition of ANALYTICS_EDITIONS) {
      if (edition.editionId === LEGACY_EDITION_ID) {
        expect(edition.preparedBy).toBeNull();
      }
    }
  });
});

/**
 * The approval also pins the reviewed text. The evidence hash says which ledger
 * the signatories read; `editionSha256` says which sentence bytes they published,
 * so an edit to a frozen edition cannot ride on an older approval.
 */
describe("approved editions pin their frozen text", () => {
  function approvedEdition(
    overrides: Partial<AnalyticsEdition> = {},
  ): AnalyticsEdition {
    return {
      seriesSlug: "data-sources",
      editionId: "data-sources-2026-11-14",
      publicationYear: 2026,
      evidenceStatus: "approved",
      editorialStatus: "published",
      frozenSource:
        "docs/analytics/editions/data-sources/2026-11-14/data-sources.md",
      assetsPinned: 0,
      preparedBy: "repo-agent/session-2026-11-14",
      editionSha256: "c".repeat(64),
      signoffs: ["source", "scientific", "publication"].map((role) => ({
        role: role as EditionSignoff["role"],
        name:
          role === "scientific"
            ? "openai-codex/gpt-6-luna (xhigh)"
            : `owner-${role}`,
        date: "2026-11-14",
        artifactSha256: "a".repeat(64),
        statement: `${role} attestation`,
        automated: role === "scientific",
        evidencePath: "docs/implementation/2026-11-14-rs01-source-inventory.md",
      })),
      note: "test",
      ...overrides,
    };
  }

  test("rejects an approved edition that pins no text", () => {
    const errors = validateEditionRegistry([
      approvedEdition({ editionSha256: null }),
    ]).join(" ");

    expect(errors).toContain("does not pin its frozen text");
  });

  test("rejects a malformed edition sha256", () => {
    const errors = validateEditionRegistry([
      approvedEdition({ editionSha256: "not-a-hash" }),
    ]).join(" ");

    expect(errors).toContain("editionSha256 is not a sha256");
  });

  test("rejects a pin on an edition that claims nothing", () => {
    const errors = validateEditionRegistry([
      approvedEdition({
        evidenceStatus: "historical",
        editorialStatus: "archived",
        signoffs: [],
        preparedBy: null,
      }),
    ]).join(" ");

    expect(errors).toContain("only an approved edition claims reviewed bytes");
  });

  test("accepts a record whose text pin is well formed", () => {
    expect(validateEditionRegistry([approvedEdition()])).toEqual([]);
  });

  test("verifyEditionArtifacts reports a drifted or unreadable text", () => {
    const edition = approvedEdition();
    const drift = verifyEditionArtifacts([edition], () => "d".repeat(64));
    const missing = verifyEditionArtifacts([edition], () => null);
    const match = verifyEditionArtifacts([edition], () => "c".repeat(64));

    expect(drift.join(" ")).toContain("but the approved edition pins");
    expect(missing.join(" ")).toContain("is unreadable");
    expect(match).toEqual([]);
  });

  test("verifyEditionArtifacts ignores editions that claim nothing", () => {
    const historical: AnalyticsEdition = {
      ...approvedEdition(),
      evidenceStatus: "historical",
      editorialStatus: "archived",
      signoffs: [],
      preparedBy: null,
      editionSha256: null,
    };

    expect(verifyEditionArtifacts([historical], () => "d".repeat(64))).toEqual(
      [],
    );
  });

  test("the shipped register's text pins match the files on disk", () => {
    // Vacuous until an edition is approved; keeps the build-time check honest by
    // running the same code path here, against real bytes.
    const errors = verifyEditionArtifacts(ANALYTICS_EDITIONS, (path) => {
      const absolute = join(process.cwd(), "..", path);
      if (!existsSync(absolute)) return null;
      return createHash("sha256").update(readFileSync(absolute)).digest("hex");
    });

    expect(errors).toEqual([]);
  });

  test("detects a real file whose bytes no longer match the pin", () => {
    const legacy = ANALYTICS_EDITIONS[0]!;
    const real = createHash("sha256")
      .update(readFileSync(join(process.cwd(), "..", legacy.frozenSource)))
      .digest("hex");

    expect(
      verifyEditionArtifacts(
        [
          {
            ...legacy,
            evidenceStatus: "approved",
            editorialStatus: "published",
            editionSha256: real,
            preparedBy: "repo-agent/session-2026-11-14",
            signoffs: approvedEdition().signoffs,
          },
        ],
        (path) =>
          createHash("sha256")
            .update(readFileSync(join(process.cwd(), "..", path)))
            .digest("hex"),
      ),
    ).toEqual([]);

    expect(
      verifyEditionArtifacts(
        [
          {
            ...legacy,
            evidenceStatus: "approved",
            editorialStatus: "published",
            editionSha256: "e".repeat(64),
            preparedBy: "repo-agent/session-2026-11-14",
            signoffs: approvedEdition().signoffs,
          },
        ],
        (path) =>
          createHash("sha256")
            .update(readFileSync(join(process.cwd(), "..", path)))
            .digest("hex"),
      ).join(" "),
    ).toContain("but the approved edition pins");
  });
});
