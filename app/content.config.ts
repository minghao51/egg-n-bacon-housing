import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const analyticsCollection = defineCollection({
  loader: glob({ pattern: '**/*.mdx', base: './src/content/analytics' }),
  schema: z.object({
    title: z.string().optional(),
    date: z.coerce.date().optional(),
    status: z.string().optional(),
    category: z.enum([
      'investment-guides',
      'market-analysis',
      'technical-reports',
      'quick-reference'
    ]).optional(),
    description: z.string().optional(),
    personas: z.array(z.enum(['first-time-buyer', 'investor', 'upgrader'])).optional(),
    readingTime: z.string().optional(),
    technicalLevel: z.enum(['beginner', 'intermediate', 'advanced']).optional(),
  }),
});

export const collections = {
  'analytics': analyticsCollection,
};
