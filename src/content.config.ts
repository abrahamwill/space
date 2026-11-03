import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

/**
 * Studio work. One file per project.
 * - `order` sets the position on the home page (1–3 are the featured folders on the desk).
 * - `published: false` keeps the card on the home page as a placeholder, without a page or link.
 */
const work = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/work' }),
  schema: ({ image }) =>
    z.object({
    title: z.string(),
    /** One sentence, outcome first. Shown on the home card. */
    summary: z.string(),
    company: z.string(),
    role: z.string(),
    year: z.string(),
    order: z.number(),
    published: z.boolean().default(true),
    /** Record-sleeve artwork; each variant carries its own colours. */
    cover: z.enum(['sun', 'moon', 'mast']),
    meta: z
      .array(z.object({ label: z.string(), value: z.string() }))
      .default([]),
    tldr: z.string().optional(),
    metrics: z
      .array(z.object({ value: z.string(), label: z.string() }))
      .default([]),
    prototypeUrl: z.string().optional(),
    /** Final screens in context. Until it exists the page shows a placeholder. */
    heroImage: image().optional(),
    heroAlt: z.string().optional(),
  }),
});

export const collections = { work };
