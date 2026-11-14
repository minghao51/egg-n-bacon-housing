import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

/**
 * Frontmatter shared by the current series text and its frozen editions.
 *
 * One schema for both keeps the frozen bytes renderable by the same page shell;
 * edition *identity* and evidence status live in the registry
 * (`src/components/studies/lib/edition-registry.ts`), not in the frozen files,
 * so RF00's originals are never rewritten to carry new metadata.
 */
const analyticsSchema = z.object({
  title: z.string().optional(),
  date: z.coerce.date().optional(),
  status: z.string().optional(),
  category: z
    .enum([
      "investment-guides",
      "market-analysis",
      "technical-reports",
      "quick-reference",
    ])
    .optional(),
  description: z.string().optional(),
  personas: z
    .array(z.enum(["first-time-buyer", "investor", "upgrader"]))
    .optional(),
  readingTime: z.string().optional(),
  technicalLevel: z.enum(["beginner", "intermediate", "advanced"]).optional(),
});

/**
 * Current series text. `*.md` is single-segment on purpose: the frozen
 * `editions/**` tree must never be globbed into the series collection, or an
 * edition would be emitted at `/analytics/<slug>` and the archive identity would
 * collapse into the live series route (RF07 §2).
 */
const analytics = defineCollection({
  loader: glob({ pattern: "*.md", base: "../docs/analytics" }),
  schema: analyticsSchema,
});

/**
 * Frozen edition sources (RF00). Ids look like
 * `legacy/2026-11-12/mrt-impact`; the archive route derives its three segments
 * from that path, and the registry decides status and currentness.
 */
const analyticsEditions = defineCollection({
  loader: glob({ pattern: "editions/*/*/*.md", base: "../docs/analytics" }),
  schema: analyticsSchema,
});

export const collections = {
  analytics,
  analyticsEditions,
};
