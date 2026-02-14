import { defineCollection, z } from 'astro:content';

const analyticsCollection = defineCollection({
    type: 'content', // v2.5.0+: 'content' or 'data'
    schema: z.object({
        title: z.string().optional(),
        date: z.coerce.date().optional(),
        status: z.string().optional(), // Allow any status value (Complete, draft, published, etc.)
        category: z.enum([
            'investment-guides',
            'market-analysis',
            'technical-reports',
            'quick-reference'
        ]).optional(),
        description: z.string().optional(),
    }),
});

export const collections = {
    'analytics': analyticsCollection,
};
