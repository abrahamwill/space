import { getCollection } from 'astro:content';
import type { HouseContent } from '../house/content';
import { site, lab, about, records } from './site';

/** What the house shows, built from the same sources as the fast view. */
export async function getHouseContent(): Promise<HouseContent> {
  const work = (await getCollection('work')).sort((a, b) => a.data.order - b.data.order).slice(0, 3);
  return {
    site: { name: site.name, email: site.email, emailHref: site.emailHref, linkedin: site.linkedin, cv: site.cv },
    featured: work.map((w) => ({
      slug: w.id,
      title: w.data.title,
      summary: w.data.summary,
      company: w.data.company,
      role: w.data.role,
      year: w.data.year,
      published: w.data.published,
      cover: w.data.cover,
      tldr: w.data.tldr,
      metrics: w.data.metrics,
      prototypeUrl: w.data.prototypeUrl,
    })),
    lab,
    about,
    records,
  };
}

/** JSON safe to inline in a <script type="application/json">. */
export const inlineJson = (v: unknown) => JSON.stringify(v).replace(/</g, '\\u003c');
