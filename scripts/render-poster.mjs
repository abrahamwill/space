/**
 * Renders the hero poster(s) from the 3D scene so the still image and the live scene line up exactly.
 *   npm run build && npm run poster
 * Writes src/assets/house/poster-lit.png (hero) and poster-dim.png (house page first paint).
 */
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { chromium } from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PORT = 4329;
const WIDTH = 1200; // CSS px; rendered at 2x → 2400px wide
const server = spawn('npx', ['astro', 'preview', '--port', String(PORT)], { cwd: root, stdio: 'ignore' });

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function up() {
  for (let i = 0; i < 60; i++) {
    try { if ((await fetch(`http://localhost:${PORT}/poster`)).ok) return; } catch {}
    await wait(500);
  }
  throw new Error('preview server did not start');
}

try {
  await up();
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  for (const state of ['lit', 'dim']) {
    const page = await browser.newPage({ viewport: { width: WIDTH, height: 600 }, deviceScaleFactor: 2 });
    await page.goto(`http://localhost:${PORT}/poster?state=${state}`);
    await page.waitForFunction(() => window.__posterAspect);
    const aspect = await page.evaluate(() => window.__posterAspect);
    await page.waitForFunction(() => window.__posterReady, null, { timeout: 30000 });
    await page.setViewportSize({ width: WIDTH, height: Math.round(WIDTH / aspect) });
    await wait(800); // the engine re-renders on resize
    const out = path.join(root, `src/assets/house/poster-${state}.png`);
    await page.screenshot({ path: out, omitBackground: true });
    console.log('wrote', path.relative(root, out), WIDTH * 2, 'x', Math.round(WIDTH / aspect) * 2);
    await page.close();
  }
  await browser.close();
} finally {
  server.kill();
}
