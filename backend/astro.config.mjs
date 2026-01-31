import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import mdx from '@astrojs/mdx';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  integrations: [
    react(),
    mdx(),
    tailwind({
      applyBaseStyles: false,
    }),
  ],
  site: 'http://localhost:4321',
  base: '/',
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
