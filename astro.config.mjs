// @ts-check
import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';

export default defineConfig({
  // TODO(owner): set to the production URL so canonical/OG links are absolute.
  site: 'https://example.com',
  integrations: [mdx()],
  trailingSlash: 'ignore',
});
