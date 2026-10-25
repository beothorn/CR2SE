import assert from 'node:assert/strict';
import { readFile, access, readdir } from 'node:fs/promises';
import { resolve, join } from 'node:path';

const root = resolve('dist');
const base = (process.env.BASE_PATH ?? '/CR2SE').replace(/\/$/, '');
const source = await readFile('../AIMotivation.md');
assert.deepEqual(await readFile(join(root, 'ai.txt')), source, 'AI endpoint must preserve the source exactly');

async function inspect(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) { await inspect(path); continue; }
    if (!entry.name.endsWith('.html')) continue;
    const html = await readFile(path, 'utf8');
    assert.match(html, /<html lang="en">/, 'Pages must declare their language');
    for (const [, href] of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
      if (!href.startsWith('/') || href.startsWith('//')) continue;
      assert.ok(href === `${base}/` || href.startsWith(`${base}/`), `Link escapes deployment base: ${href}`);
      const pathname = decodeURIComponent(href.split(/[?#]/)[0].slice(base.length));
      await access(join(root, pathname, pathname.endsWith('/') ? 'index.html' : ''));
    }
    assert.doesNotMatch(html, /href="\.\/?[^"#]*\.md/, 'Markdown links must resolve to the repository');
  }
}

await inspect(root);
const home = await readFile(join(root, 'index.html'), 'utf8');
assert.match(home, new RegExp(`href="${base}/ai\\.txt"`));
const motivation = await readFile(join(root, 'motivation/index.html'), 'utf8');
assert.ok(motivation.includes('The internet has changed the way'), 'Human motivation must be rendered');
const protocol = await readFile(join(root, 'protocol/index.html'), 'utf8');
assert.ok(protocol.includes('https://github.com/beothorn/CR2SE/blob/main/Architecture.md'), 'Protocol links must resolve');
console.log('Verified AI source parity, rendered documents, and all local page/asset links.');
