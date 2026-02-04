import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import mdx from '@astrojs/mdx';
import tailwind from '@astrojs/tailwind';

import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

const isProduction = process.env.CI === 'true';

export default defineConfig({
  integrations: [
    react(),
    mdx({
      remarkPlugins: [remarkMath],
      rehypePlugins: [rehypeKatex],
    }),
    tailwind({
      applyBaseStyles: false,
    }),
  ],
  site: isProduction
    ? 'https://minghao51.github.io/egg-n-bacon-housing'
    : 'http://localhost:4321',
  base: isProduction ? '/egg-n-bacon-housing/' : '/',
  trailingSlash: 'ignore',
  build: {
    format: 'file',
  },
  vite: {
    resolve: {
      alias: {
        '@': new URL('./src', import.meta.url).pathname,
      },
    },
  },
});
