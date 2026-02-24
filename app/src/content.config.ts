import { defineCollection, z } from 'astro:content';

const analytics = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    category: z.string(),
    description: z.string(),
    status: z.string(),
    date: z.union([z.string(), z.date()]),
    personas: z.array(z.string()).optional(),
    readingTime: z.string().optional(),
    technicalLevel: z.string().optional(),
  }),
});

export const collections = {
  analytics,
};
