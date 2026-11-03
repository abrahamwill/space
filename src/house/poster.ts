/** Renders the scene exactly as the hero frames it, for scripts/render-poster.mjs to screenshot. */
import { HouseEngine } from './engine';
import { fitPoster, posterAspect } from './camera';

declare global {
  interface Window { __posterReady?: boolean; __posterAspect?: number }
}

export function mountPoster(host: HTMLElement) {
  window.__posterAspect = posterAspect();
  const dim = new URLSearchParams(location.search).get('state') === 'dim';
  const engine = new HouseEngine(host, {
    frame: fitPoster,
    preserveDrawingBuffer: true,
    onFirstFrame: () => setTimeout(() => (window.__posterReady = true), 100),
  });
  engine.setLit({ main: true, studio: !dim, lab: !dim }, true);
}
