/**
 * Hero poster for the Pinwheel house: a still of /house3d, so the image and the live 3D that fades in
 * over it line up exactly. Run with the dev server up (npx astro dev), after changing the GLB or LIGHT:
 *   node scripts/render-house3d-poster.mjs [http://localhost:4321]
 * Writes src/assets/house/hero-p2.png (cropped to the house) and prints the CSS inset that places the
 * live canvas over it; paste that into .house-live in src/pages/index.astro if it changed.
 *
 * Also writes public/images/iso-grid.svg, the hero's iso grid, drawn through the same HeroCamera on the
 * page plane (the level the house is cut into). One cell is the house's plan module (0.5 m), so every
 * outer wall and notch lands on a grid line. A darker line every 3 cells (1.5 m, the Pinwheel's own
 * module), counted from the plan's origin (the back corner of the house), as in the design
 * (Hero-Sunken-P2). It fades out like the design's grid: scripts/iso-grid-fade.png, taken from it.
 */
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { readFile, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import sharp from 'sharp';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = process.argv[2] ?? 'http://localhost:4321';
const W = 1720, H = 1320, DPR = 2; // the Blender HeroCamera frame
const CELL = 0.5; // m, the plan module (house3d/source/plans.py: every wall and cut is on 0.5 m)
const MAJOR = 3;  // a darker line every 3 cells (1.5 m)
// The .grid box in src/pages/index.astro, in stage widths (the house spans the full stage width).
// top is measured from the house's top edge.
const GRID = { left: -0.65116, width: 1.67442, aspect: 2880 / 1720, top: -0.24186 };

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: DPR });
await page.goto(`${base}/house3d?bare`);
await page.waitForFunction(() => window.__houseReady || window.__houseError, null, { timeout: 120000 });
const err = await page.evaluate(() => window.__houseError);
if (err) throw new Error(err);
await page.evaluate(() => document.querySelector('astro-dev-toolbar')?.remove());
// The page plane in frame px: where plan (0, 0) lands, and one cell along plan x (glTF X) and plan y (glTF Z).
const proj = await page.evaluate((cell) => {
  const h = window.__house, f = h.heroFrame(), cam = h.camera().clone();
  cam.left = -f.x; cam.right = f.x; cam.top = f.y; cam.bottom = -f.y;
  cam.updateProjectionMatrix(); cam.updateMatrixWorld();
  let y = 0;
  h.house().traverse((o) => {
    if (o.isMesh && (o.name.startsWith('page_surface') || o.parent?.name === 'page_surface')) {
      o.geometry.computeBoundingBox();
      y = o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld).min.y;
    }
  });
  const V = cam.position.constructor;
  const P = (x, z) => { const v = new V(x, y, z).project(cam); return [((v.x + 1) / 2) * 1720, ((1 - v.y) / 2) * 1320]; };
  const o = P(0, 0), a = P(cell, 0), b = P(0, cell);
  return { o, a: [a[0] - o[0], a[1] - o[1]], b: [b[0] - o[0], b[1] - o[1]] };
}, CELL);
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

// ---- The iso grid, in poster css px (viewBox = the .grid box)
{
  const pw = w / DPR; // css px per stage width
  const fade = await readFile(path.join(root, 'scripts/iso-grid-fade.png'));
  const ox = proj.o[0] - x0 / DPR, oy = proj.o[1] - y0 / DPR;
  const bx = GRID.left * pw, by = GRID.top * pw, bw = GRID.width * pw, bh = bw / GRID.aspect;
  const clip = (px, py, dx, dy) => { // the part of the line p + t·d inside the box, or null
    let t0 = -Infinity, t1 = Infinity;
    for (const [p, d, lo, hi] of [[px, dx, bx, bx + bw], [py, dy, by, by + bh]]) {
      if (Math.abs(d) < 1e-9) { if (p < lo || p > hi) return null; continue; }
      const u = (lo - p) / d, v = (hi - p) / d;
      t0 = Math.max(t0, Math.min(u, v)); t1 = Math.min(t1, Math.max(u, v));
    }
    return t0 < t1 ? [px + t0 * dx, py + t0 * dy, px + t1 * dx, py + t1 * dy] : null;
  };
  const f = (n) => +n.toFixed(2);
  const minor = [], major = [];
  for (const [step, dir] of [[proj.a, proj.b], [proj.b, proj.a]])
    for (let i = -400; i <= 400; i++) {
      const s = clip(ox + i * step[0], oy + i * step[1], dir[0], dir[1]);
      if (s) (i % MAJOR === 0 ? major : minor).push(`M${f(s[0])} ${f(s[1])}L${f(s[2])} ${f(s[3])}`);
    }
  const box = `x="${f(bx)}" y="${f(by)}" width="${f(bw)}" height="${f(bh)}"`;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${f(bx)} ${f(by)} ${f(bw)} ${f(bh)}" width="2880" height="1720">
<!-- Generated by scripts/render-house3d-poster.mjs: the house's 0.5 m plan grid on the page plane, seen by the HeroCamera. -->
<defs><mask id="m" maskUnits="userSpaceOnUse" ${box}><image ${box} preserveAspectRatio="none" href="data:image/png;base64,${fade.toString('base64')}"/></mask></defs>
<g mask="url(#m)" fill="none" stroke="#1b1a17">
<path stroke-opacity=".11" stroke-width=".5" vector-effect="non-scaling-stroke" d="${minor.join('')}"/>
<path stroke-opacity=".26" stroke-width="1" vector-effect="non-scaling-stroke" d="${major.join('')}"/>
</g></svg>
`;
  const gout = path.join(root, 'public/images/iso-grid.svg');
  await writeFile(gout, svg);
  console.log('wrote', path.relative(root, gout), minor.length + major.length, 'lines; one cell =', proj.a.map(f), proj.b.map(f), 'px');
}

const pct = (v, of) => `${((-100 * v) / of).toFixed(3)}%`;
console.log('wrote', path.relative(root, out), w, 'x', h);
console.log(`.house-live inset: ${pct(y0, h)} ${pct(info.width - 1 - x1, w)} ${pct(info.height - 1 - y1, h)} ${pct(x0, w)};`);
