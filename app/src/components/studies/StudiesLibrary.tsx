/**
 * Studies library filter island (slice S9, SVG 14).
 *
 * Filters the published studies by free text, topic and audience. It is a pure
 * presentation layer over the static study list the Astro page already renders
 * — no fetch, no tracking, no readership scores.
 */

import { useMemo, useState } from "react";
import {
  DEFAULT_STUDY_FILTERS,
  filterStudies,
  filtersAreActive,
  STUDY_CATEGORIES,
  STUDY_CATEGORY_LABELS,
  STUDY_PERSONA_LABELS,
  STUDY_PERSONAS,
  type StudyAudience,
  type StudyCardData,
  type StudyCategory,
} from "./lib/studies";

interface StudiesLibraryProps {
  studies: StudyCardData[];
  baseUrl: string;
}

function formatDate(value: string | null): string {
  if (value === null) return "Date not supplied";
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return "Date not supplied";
  return parsed.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

export default function StudiesLibrary({
  studies,
  baseUrl,
}: StudiesLibraryProps) {
  const [filters, setFilters] = useState(DEFAULT_STUDY_FILTERS);

  const visible = useMemo(
    () => filterStudies(studies, filters),
    [studies, filters],
  );

  return (
    <div className="mt-8">
      <div className="rounded-2xl border border-border bg-card p-4 sm:p-5">
        <h2 className="text-lg font-bold text-foreground">Search studies</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Filter by title, description or topic. Audience uses each
          study&rsquo;s published persona entry point; a study without one is
          listed only under “All audiences”.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_auto] lg:items-end">
          <div>
            <label
              htmlFor="study-search"
              className="block text-sm font-bold text-foreground"
            >
              Free text
            </label>
            <input
              id="study-search"
              type="search"
              autoComplete="off"
              value={filters.query}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  query: event.target.value,
                }))
              }
              placeholder="Lease, transport, schools, yields…"
              className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
            />
          </div>
          <div>
            <label
              htmlFor="study-category"
              className="block text-sm font-bold text-foreground"
            >
              Topic
            </label>
            <select
              id="study-category"
              value={filters.category}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  category: event.target.value as StudyCategory | "all",
                }))
              }
              className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
            >
              <option value="all">All topics</option>
              {STUDY_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {STUDY_CATEGORY_LABELS[category]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label
              htmlFor="study-audience"
              className="block text-sm font-bold text-foreground"
            >
              Reading for
            </label>
            <select
              id="study-audience"
              value={filters.audience}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  audience: event.target.value as StudyAudience,
                }))
              }
              className="mt-1 w-full rounded border border-input bg-background px-3 py-2 text-sm text-foreground"
            >
              <option value="all">All audiences</option>
              {STUDY_PERSONAS.map((persona) => (
                <option key={persona} value={persona}>
                  {STUDY_PERSONA_LABELS[persona]}
                </option>
              ))}
              <option value="all-personas">Studies with a persona entry</option>
            </select>
          </div>
          <button
            type="button"
            onClick={() => setFilters(DEFAULT_STUDY_FILTERS)}
            disabled={!filtersAreActive(filters)}
            className="rounded border border-input px-3 py-2 text-sm font-bold text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
          >
            Reset filters
          </button>
        </div>
        <p
          role="status"
          aria-live="polite"
          className="mt-3 text-sm text-muted-foreground"
        >
          {visible.length} of {studies.length} studies
          {filtersAreActive(filters) ? " match these filters" : ""}.
        </p>
      </div>

      {visible.length === 0 ? (
        <div className="mt-6 rounded-xl border border-border bg-muted/20 p-5 text-sm text-muted-foreground">
          <p className="font-bold text-foreground">No study matches.</p>
          <p className="mt-1">
            Clear the filters to see all {studies.length} published studies.
            Filtering never fetches a different dataset.
          </p>
        </div>
      ) : (
        <ul className="mt-6 grid gap-4 md:grid-cols-2">
          {visible.map((study) => (
            <li key={study.slug}>
              <a
                href={`${baseUrl}analytics/${study.slug}`}
                className="flex h-full flex-col rounded-2xl border border-border bg-card p-5 transition-colors hover:bg-muted/30"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-sm bg-[hsl(var(--secondary))] px-2 py-0.5 text-xs font-bold text-foreground">
                    {STUDY_CATEGORY_LABELS[study.category]}
                  </span>
                  {study.evidenceReview ? (
                    <span className="rounded-sm border border-amber-600 px-2 py-0.5 text-xs font-bold text-amber-700 dark:text-amber-300">
                      Unit review
                    </span>
                  ) : null}
                </div>
                <h3 className="mt-3 text-lg font-bold text-foreground">
                  {study.title}
                </h3>
                <p className="mt-2 flex-1 text-sm text-muted-foreground">
                  {study.description || "No description supplied."}
                </p>
                <p className="mt-4 text-xs text-muted-foreground">
                  {formatDate(study.date)}
                  {study.readingTime ? ` · ${study.readingTime}` : ""}
                  {study.technicalLevel ? ` · ${study.technicalLevel}` : ""}
                </p>
                <p className="mt-2 text-sm font-bold text-foreground">
                  Read study &rarr;
                </p>
              </a>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-6 rounded-xl border border-border bg-muted/20 p-4 text-sm text-muted-foreground">
        Studies are published research, not current transaction medians. Each
        study states its own observation period and units; where those are under
        review the study says so and its chart is withheld. No readership or
        coverage score is published here.
      </p>
    </div>
  );
}
