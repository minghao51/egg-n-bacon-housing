import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const analytics = defineCollection({
  loader: glob({ pattern: '**/*.md', base: '../docs/analytics' }),
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
  analytics,
};
