import { defineConfig } from "astro/config";
import { fileURLToPath } from "url";
import path from "path";
import react from "@astrojs/react";

import { unified } from "@astrojs/markdown-remark";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

const isPagesDeploy = process.env.ASTRO_PAGES === "true";
const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Remove the document's leading level-1 heading.
 *
 * Every study in `docs/analytics` starts with `# Title`, and the article shell
 * already renders the title as the page's only `<h1>`. Leaving both produced
 * two H1s on every study page (S9). The heading is stripped from the rendered
 * body — not hidden with CSS — so the accessibility tree and the TOC agree.
 */
function remarkStripLeadingH1() {
  return function (tree) {
    // Only a genuinely leading H1 is removed. A later depth-1 heading is part
    // of the document body and keeps its anchor and TOC entry.
    const first = tree.children[0];
    if (first?.type === "heading" && first.depth === 1) {
      tree.children.shift();
    }
  };
}

function remarkFixImagePaths() {
  return function (tree) {
    const visit = (node) => {
      if (node.type === "image") {
        if (!isPagesDeploy && node.url.startsWith("/egg-n-bacon-housing/")) {
          node.url = node.url.replace("/egg-n-bacon-housing/", "/");
        }
      }
      if (node.children) {
        node.children.forEach(visit);
      }
    };
    visit(tree);
  };
}

/**
 * Bound every rendered markdown table.
 *
 * A GFM table renders inline at full height — on `/analytics/findings` two of
 * them were 1,000 px and 1,496 px, a fifth of the page between them. Each
 * `<table>` is wrapped here, at build time, in a scroll container instead: the
 * table keeps all of its rows (nothing is hidden or disclosed behind a click),
 * but the container caps its height and scrolls (S11).
 *
 * `role="region"` + `tabindex="0"` is the accessible way to make a scroll
 * container reachable: a keyboard user cannot scroll a plain `<div>`, so the
 * region is focusable and announces itself with the table's own first header
 * cell as its name. The presentation (height cap, sticky header, focus ring)
 * lives in `src/styles/globals.css` because the archive route renders the same
 * markdown and must get the same treatment.
 *
 * One note travels with the wrapper. A study opts a table into a chart by
 * writing a hidden `<div data-chart-metadata="true">` immediately before it;
 * `InlineChartRenderer` finds that marker through
 * `table.previousElementSibling`, so the marker moves inside the wrapper
 * together with its table — the lookup still finds it. The chart itself is
 * appended *after the wrapper*, not after the table, so it is a sibling of the
 * scroll region and the height cap applies to the table alone. Without that,
 * a cap would hide the chart the author asked for.
 */
function rehypeWrapTables() {
  return function (tree) {
    tree.children = wrapTablesIn(tree.children ?? []);
  };
}

/**
 * Replace every `<table>` in a children array with its scroll region. A chart
 * marker sitting immediately before a table is carried into the same wrapper;
 * everything else is walked recursively (a table inside a list item or a
 * blockquote is wrapped too), while a table nested in a table cell is not —
 * a scroll region inside another would trap the wheel.
 */
function wrapTablesIn(children) {
  const wrapped = [];
  for (const child of children) {
    if (isElement(child, "table")) {
      const markerIndex = chartMarkerIndex(wrapped);
      const [marker] =
        markerIndex === -1 ? [null] : wrapped.splice(markerIndex, 1);
      wrapped.push(tableRegion(child, marker));
      continue;
    }
    if (child.children) {
      child.children = wrapTablesIn(child.children);
    }
    wrapped.push(child);
  }
  return wrapped;
}

const isBlankText = (node) => node?.type === "text" && node.value.trim() === "";

/**
 * Index of the chart marker sitting immediately before the current position.
 * The newline the markdown block separator leaves behind is not content, so it
 * is looked through rather than treated as an intervening sibling.
 */
function chartMarkerIndex(wrapped) {
  let index = wrapped.length - 1;
  while (index >= 0 && isBlankText(wrapped[index])) index--;
  return index >= 0 && isChartMarker(wrapped[index]) ? index : -1;
}

const isElement = (node, tagName) =>
  node?.type === "element" && node.tagName === tagName;

/**
 * A study opts a table into a chart with a hidden
 * `<div data-chart-metadata="true">` written immediately before it. Raw HTML is
 * still an unparsed `raw` node at this stage — `rehype-raw` runs after the user
 * rehype plugins — so the marker arrives as text and an element branch is kept
 * for the case where it was authored as an element instead.
 */
const isChartMarker = (node) =>
  (isElement(node, "div") && node.properties?.dataChartMetadata === "true") ||
  (node?.type === "raw" &&
    /data-chart-metadata\s*=\s*["']true["']/.test(node.value));

/** The text of a header cell, used as the region's accessible name. */
function textOf(node) {
  if (node.type === "text") return node.value;
  if (!node.children) return "";
  return node.children.map(textOf).join("");
}

/**
 * The name comes from the header row, which is what the reader uses to tell
 * one evidence table from another in a screen-reader region list.
 */
function tableLabel(table) {
  const head = table.children?.find((child) => isElement(child, "thead"));
  const firstRow = head?.children?.find((child) => isElement(child, "tr"));
  const firstCell =
    firstRow?.children?.find((child) => isElement(child, "th")) ??
    firstRow?.children?.[0];
  const label = firstCell ? textOf(firstCell).trim() : "";
  return label === "" ? "Data table" : label;
}

function tableRegion(table, marker) {
  return {
    type: "element",
    tagName: "div",
    properties: {
      className: ["table-scroll"],
      role: "region",
      tabIndex: 0,
      ariaLabel: tableLabel(table),
    },
    children: marker === null ? [table] : [marker, table],
  };
}

export default defineConfig({
  // One env file for the whole repository: the Python pipeline reads `.env` at
  // the repo root (pydantic-settings), so Vite's env dir is pointed at the
  // parent and the map values live in that same file instead of a second,
  // easily-forgotten `app/.env`. This is a **Vite** option, not an Astro one —
  // a top-level `envDir` is silently ignored, which is how this was first
  // wired wrong. Only `PUBLIC_`-prefixed variables reach the client bundle, so
  // the pipeline's secrets in that file are never exposed by this.
  // Tailwind v3 is compiled by the project-local `postcss.config.mjs`.
  // Astro 6 dropped the deprecated `@astrojs/tailwind` integration, so the
  // same chain runs through Vite's PostCSS pipeline with no behaviour change.
  integrations: [react()],
  markdown: {
    // Astro 7 made the `unified` processor explicit: `markdown.remarkPlugins`
    // and `markdown.rehypePlugins` are deprecated top-level keys. The factory
    // below is the same pipeline they were folded into (GFM and SmartyPants
    // defaults included), so rendering is unchanged.
    processor: unified({
      remarkPlugins: [remarkMath, remarkStripLeadingH1, remarkFixImagePaths],
      rehypePlugins: [rehypeKatex, rehypeWrapTables],
    }),
  },
  site: isPagesDeploy
    ? "https://minghao51.github.io/egg-n-bacon-housing"
    : "http://localhost:4321",
  base: isPagesDeploy ? "/egg-n-bacon-housing/" : "/",
  trailingSlash: "ignore",
  build: {
    format: "directory",
  },
  prefetch: {
    prefetchAll: true,
    defaultStrategy: "viewport",
  },
  cacheDir: "./.astro-cache",
  vite: {
    // Read `PUBLIC_*` from the repository-root `.env` (see the note above).
    envDir: "..",
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
        "@components": path.resolve(__dirname, "./src/components"),
        "@layouts": path.resolve(__dirname, "./src/layouts"),
        "@hooks": path.resolve(__dirname, "./src/hooks"),
        "@types": path.resolve(__dirname, "./src/types"),
        "@utils": path.resolve(__dirname, "./src/utils"),
        "@data": path.resolve(__dirname, "./src/data"),
      },
    },
    build: {
      cssMinify: true,
    },
  },
});
