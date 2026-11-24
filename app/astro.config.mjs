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
      rehypePlugins: [rehypeKatex],
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
