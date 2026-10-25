import { defineConfig } from 'astro/config';
import { unified } from '@astrojs/markdown-remark';
import repositoryLinks from './scripts/repository-links.mjs';

export default defineConfig({
  site: process.env.SITE_URL || 'https://beothorn.github.io',
  base: process.env.BASE_PATH ?? '/CR2SE',
  trailingSlash: 'always',
  output: 'static',
  markdown: { processor: unified({ remarkPlugins: [repositoryLinks] }) },
});
