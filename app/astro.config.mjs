import { defineConfig } from 'astro/config';
import { fileURLToPath } from 'url';
import path from 'path';
import react from '@astrojs/react';
import mdx from '@astrojs/mdx';
import tailwind from '@astrojs/tailwind';

import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

const isProduction = process.env.CI === 'true';
const __dirname = path.dirname(fileURLToPath(import.meta.url));

function remarkFixImagePaths() {
  return function (tree) {
    const visit = (node) => {
      if (node.type === 'image') {
        if (!isProduction && node.url.startsWith('/egg-n-bacon-housing/')) {
          node.url = node.url.replace('/egg-n-bacon-housing/', '/');
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
  integrations: [
    react(),
    mdx({
      remarkPlugins: [remarkMath, remarkFixImagePaths],
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
    format: 'directory',
  },
  prefetch: {
    prefetchAll: true,
    defaultStrategy: 'viewport',
  },
  cacheDir: './.astro-cache',
  vite: {
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@components': path.resolve(__dirname, './src/components'),
        '@layouts': path.resolve(__dirname, './src/layouts'),
        '@hooks': path.resolve(__dirname, './src/hooks'),
        '@types': path.resolve(__dirname, './src/types'),
        '@utils': path.resolve(__dirname, './src/utils'),
        '@data': path.resolve(__dirname, './src/data'),
      },
    },
    build: {
      cssMinify: true,
    },
  },
});
