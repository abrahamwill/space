/**
 * The live house in the home-page hero. Mounted by the loader in index.astro only after the page
 * is idle and the hero is visible (or on intent). No framework: three.js + our engine only.
 */
import { HouseEngine } from './engine';
import { fitPoster } from './camera';

const MAX_TILT = (5 * Math.PI) / 180;
export const HERO_FPS = 30;
export const HERO_DPR = 1.5;

export function mountHero(host: HTMLElement, onReady: () => void) {
  const engine = new HouseEngine(host, {
    maxDpr: HERO_DPR, // reduced resolution in the hero; full quality inside
    frame: fitPoster, // identical framing to the poster image underneath
    onFirstFrame: () => {
      engine.setInstant(false);
      onReady();
    },
  });
  engine.setLit({ main: true, studio: true, lab: true }, true);
  engine.setAmbient(HERO_FPS);

  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
    // A small tilt toward the mouse, so the house reads as a place rather than a picture.
    host.addEventListener('pointermove', (e) => {
      if (e.pointerType !== 'mouse') return;
      const r = host.getBoundingClientRect();
      const nx = ((e.clientX - r.left) / r.width) * 2 - 1;
      engine.setTilt(Math.max(-1, Math.min(1, nx)) * MAX_TILT);
    });
    host.addEventListener('pointerleave', () => engine.setTilt(0));
  }
  return engine;
}
