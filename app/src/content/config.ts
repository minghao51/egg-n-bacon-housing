import { defineCollection, z } from 'astro:content';

const analyticsCollection = defineCollection({
    type: 'content', // v2.5.0+: 'content' or 'data'
    schema: z.object({
        title: z.string().optional(),
        date: z.coerce.date().optional(),
        status: z.enum(['draft', 'published']).default('published'),
        category: z.enum(['core', 'market', 'advanced', 'reports', 'reference']).default('reports'),
        description: z.string().optional(),
    }),
});

export const collections = {
    'analytics': analyticsCollection,
};
