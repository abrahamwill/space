/**
 * Hero poster for the Pinwheel house: a still of /house3d, so the image and the live 3D that fades in
 * over it line up exactly. Run with the dev server up (npx astro dev), after changing the GLB or LIGHT:
 *   node scripts/render-house3d-poster.mjs [http://localhost:4321]
 * Writes src/assets/house/hero-p2.png (cropped to the house) and prints the CSS inset that places the
 * live canvas over it; paste that into .house-live in src/pages/index.astro if it changed.
 */
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { chromium } from 'playwright';
import sharp from 'sharp';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = process.argv[2] ?? 'http://localhost:4321';
const W = 1720, H = 1320, DPR = 2; // the Blender HeroCamera frame

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: DPR });
await page.goto(`${base}/house3d?bare`);
await page.waitForFunction(() => window.__houseReady || window.__houseError, null, { timeout: 120000 });
const err = await page.evaluate(() => window.__houseError);
if (err) throw new Error(err);
await page.evaluate(() => document.querySelector('astro-dev-toolbar')?.remove());
await page.waitForTimeout(300);
const shot = await page.screenshot({ omitBackground: true });
await browser.close();

// Crop to the house (anything visibly opaque).
const { data, info } = await sharp(shot).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
let x0 = info.width, y0 = info.height, x1 = -1, y1 = -1;
for (let y = 0; y < info.height; y++)
  for (let x = 0; x < info.width; x++)
    if (data[(y * info.width + x) * 4 + 3] > 8) {
      if (x < x0) x0 = x; if (x > x1) x1 = x;
      if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
const w = x1 - x0 + 1, h = y1 - y0 + 1;
const out = path.join(root, 'src/assets/house/hero-p2.png');
await sharp(shot).extract({ left: x0, top: y0, width: w, height: h }).png({ compressionLevel: 9 }).toFile(out);

const pct = (v, of) => `${((-100 * v) / of).toFixed(3)}%`;
console.log('wrote', path.relative(root, out), w, 'x', h);
console.log(`.house-live inset: ${pct(y0, h)} ${pct(info.width - 1 - x1, w)} ${pct(info.height - 1 - y1, h)} ${pct(x0, w)};`);
