# CR2SE website

An Astro static site deployed to GitHub Pages. Website code lives here; the
repository's Markdown documents remain the source of truth.

## Local development

Use Node 24, then run from this directory:

```sh
npm ci
npm run dev
```

The development site is served under `/CR2SE/`. To verify the production output:

```sh
npm run build
npm run check:build
npm run preview
```

## Content

- `/` introduces the protocol and links to the two motivations.
- `/motivation/` renders the root `Motivation.md` directly.
- `/protocol/` renders the root `README.md`, with document links pointing to
  the complete specification on GitHub.
- `/ai.txt` serves the root `AIMotivation.md` verbatim, as plain text, without HTML.

The landing page is `src/pages/index.astro`; shared styling is in
`src/styles/global.css`. No changes to the original motivations are needed to
publish them.

## GitHub Pages

The `pages.yml` workflow builds and checks pull requests. Pushes to `main` that
change Markdown, website files, or the workflow rebuild and deploy the site.
It can also be run manually through Actions.

In **Settings → Pages → Build and deployment**, select **GitHub Actions** as
the source once. The deployment token cannot change this repository setting.
Leaving an older branch-based source enabled can run a competing Jekyll build
that overwrites the Astro deployment. Pages must be enabled before the workflow
runs.

GitHub address: <https://beothorn.github.io/CR2SE/>. GitHub currently reports an
inherited domain address of <http://www.isageek.com.br/CR2SE/>. The build reads
the actual origin and base path from Pages automatically.

## A future custom domain

1. Configure the custom domain in repository Settings → Pages and point its
   DNS to GitHub Pages following GitHub's custom domain instructions.
2. Run the deployment workflow again; it reads the new origin and base path
   directly from GitHub Pages.
3. Enable HTTPS in Pages settings when
   the certificate is ready.

Optional repository Actions variables `SITE_URL` and `BASE_PATH` override the
detected address. Set them to `https://example.org` and `/` for a domain root,
or supply them locally for a build. Assets and navigation use the configured
base; no URL edits in page templates are required.
