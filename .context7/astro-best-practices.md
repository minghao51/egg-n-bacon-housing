# Astro Best Practices - Context7 Documentation

Extracted from official Astro documentation (2024-2025)

## Project Configuration

### Basic Configuration Structure
```js
// astro.config.mjs
import { defineConfig } from "astro/config";

export default defineConfig({
  // Configuration options
});
```

### Output Directory (outDir)
Set the directory for build artifacts (default: `./dist`)
```js
{
  outDir: "./my-custom-build-directory"
}
```

### Cache Directory
Set custom cache directory for build artifacts to speed up subsequent builds
```js
{
  cacheDir: './my-custom-cache-directory'
}
```

### Build Concurrency
Set number of pages built in parallel (default: 1). Use sparingly to avoid memory issues.
```js
{
  build: {
    concurrency: 2
  }
}
```

## TypeScript Configuration

### Extend Astro's Strict Config
Astro 5.0+ defaults to strict TypeScript for new projects.
```json
{
  "extends": "astro/tsconfigs/strict",
  "compilerOptions": {
    // Custom options
  }
}
```

### Import Aliases
Define path shortcuts in tsconfig.json:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/components/*": ["src/components/*"],
      "@/layouts/*": ["src/layouts/*"],
      "@/assets/*": ["src/assets/*"]
    }
  }
}
```

## React Integration

### Client Directives
Control when framework components hydrate:

- `client:load` - Hydrate immediately on page load
- `client:visible` - Hydrate when component enters viewport
- `client:idle` - Hydrate when browser is idle
- `client:only="react"` - Skip SSR, render only on client

```astro
<InteractiveButton client:load />
<InteractiveCounter client:visible />
<SomeReactComponent client:only="react" />
```

### Islands Architecture
Only interactive components load JavaScript. Mark components with `client:*` directives for granular control.

## Content Collections

### Define Collection Schemas with Zod
```ts
// src/content.config.ts
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const blog = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/data/blog" }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
  })
});

export const collections = { blog };
```

### Image Validation in Schemas
```ts
import { image } from 'astro:assets';

const blogCollection = defineCollection({
  schema: ({ image }) => z.object({
    title: z.string(),
    cover: image(),
    coverAlt: z.string(),
  }),
});
```

## Image Optimization

### Use Astro's Image Component
Import from `astro:assets` for automatic optimization:
```astro
---
import { Image } from 'astro:assets';
import myImage from '../assets/my_image.png';
---

<Image src={myImage} alt="Description" />
```

Benefits:
- Automatic WebP conversion
- Proper width/height attributes
- Lazy loading by default
- Prevents Cumulative Layout Shift (CLS)

### Layout Options
- `layout='constrained'` - Scale down to fit container, don't scale up
- `layout='full'` - Always fill container
- `layout='fixed'` - Fixed dimensions

## Performance Best Practices

1. **Use client directives strategically** - Only hydrate what's needed
2. **Preload critical resources** - Use `<link rel="preload">` for fonts
3. **Enable prefetching** - Configure prefetch for faster navigation
4. **Optimize images** - Use astro:assets Image component
5. **Minimize client-side JS** - Keep interactive islands small
6. **Use build caching** - Configure cacheDir for faster rebuilds

## Build Commands

```bash
npm run build    # Production build
pnpm build
yarn run build
```

## Migration Notes

- Astro 5.0+ removes `--typescript` flag from create-astro CLI
- All new projects use strict TypeScript by default
- Content collections use new `src/content.config.ts` format with loaders
