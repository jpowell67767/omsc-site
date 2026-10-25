// Pre-render each page to static HTML using the same template the browser runs.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const meta = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const tmp = path.join(path.dirname(process.argv[2]), 'tmpjs');
fs.rmSync(tmp, { recursive: true, force: true });
fs.cpSync(path.join(meta.out, 'js'), tmp, { recursive: true });
fs.writeFileSync(path.join(tmp, 'package.json'), '{"type":"module"}');
const { renderToString } = await import(pathToFileURL(path.join(tmp, 'dc.js')).href);
for (const p of meta.pages) {
  const mod = await import(pathToFileURL(path.join(tmp, p.base + '.js')).href);
  const html = renderToString(mod.Component, mod.T, { accent: '#F2A93B' });
  fs.writeFileSync(path.join(meta.out, p.base + '.ssr.html'), html);
  console.log('rendered', p.out, html.length);
}
