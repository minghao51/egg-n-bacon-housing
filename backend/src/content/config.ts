import { defineCollection, z } from 'astro:content';

const analyticsCollection = defineCollection({
    type: 'content', // v2.5.0+: 'content' or 'data'
    schema: z.object({
        title: z.string().optional(),
        date: z.string().optional(),
        status: z.string().optional(),
    }),
});

export const collections = {
    'analytics': analyticsCollection,
};
