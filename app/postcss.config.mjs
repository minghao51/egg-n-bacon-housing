/**
 * Tailwind v3 PostCSS pipeline.
 *
 * Astro 6 removed support for the deprecated `@astrojs/tailwind` integration
 * (its peer range stops at Astro 5), so the Tailwind v3 engine is wired the
 * documented way: a plain PostCSS config that Vite inlines for both `astro dev`
 * and `astro build`. `globals.css` keeps its `@tailwind base/components/
 * utilities` directives and `tailwind.config.mjs` is unchanged.
 */
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
