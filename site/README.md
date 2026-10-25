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

The workflow enables Pages when needed and selects **GitHub Actions** as the
source, replacing any older branch-based Jekyll build. If repository policy
prevents initial setup, an administrator can select **GitHub Actions** in
**Settings → Pages → Build and deployment**.

Default address: <https://beothorn.github.io/CR2SE/>.

## A future custom domain

1. Configure the custom domain in repository Settings → Pages and point its
   DNS to GitHub Pages following GitHub's custom domain instructions.
2. Set the repository Actions variable `SITE_URL` to the full origin, such as
   `https://example.org`.
3. Set the Actions variable `BASE_PATH` to `/` for a site at the domain root.
4. Run the deployment workflow again and enable HTTPS in Pages settings when
   the certificate is ready.

Both variables can also be supplied locally for a build. Assets and navigation
use the configured base; no URL edits in page templates are required.
