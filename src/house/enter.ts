/**
 * Entering the house from the home page, without a page load.
 *
 * The hero's live canvas is lifted into a full-screen layer, framed so the house sits exactly where
 * it was on the page (no visible jump), then the camera eases into the house view while the house
 * UI fades in over the landing page. The URL becomes /house (pushState), so back/forward and sharing
 * work. Leaving runs the same move in reverse and puts the canvas back in the hero.
 */
import { createElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import HouseApp from './HouseApp';
import { useHouse } from './store';
import { fitPoster, fitRect, posterAspect } from './camera';
import type { HouseEngine } from './engine';
import type { HouseContent } from './content';

interface Session {
  engine: HouseEngine;
  heroHost: HTMLElement;
  content: HouseContent;
  layer: HTMLElement;
  root: Root;
  leaving: boolean;
}
let session: Session | null = null;

const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Where the house sits on screen in the hero. If the hero is scrolled away, use a centred stand-in. */
function heroRect(host: HTMLElement) {
  const r = host.getBoundingClientRect();
  if (r.bottom > 0 && r.top < innerHeight && r.width > 0) return { left: r.left, top: r.top, width: r.width, height: r.height };
  const width = Math.min(innerWidth * 0.8, 1000);
  const height = width / posterAspect();
  return { left: (innerWidth - width) / 2, top: (innerHeight - height) / 2, width, height };
}

function render(s: Session) {
  s.root.render(
    createElement(HouseApp, { content: s.content, engine: s.engine, leaving: s.leaving, onExit: () => history.back() }),
  );
}

export function isInside() {
  return !!session && !session.leaving;
}

export function enter(engine: HouseEngine, heroHost: HTMLElement, content: HouseContent, push = true) {
  if (session) return;
  document.documentElement.classList.add('in-house');

  const layer = document.createElement('div');
  layer.className = 'house-layer';
  const stage = document.createElement('div');
  stage.className = 'house-layer-stage';
  const mount = document.createElement('div');
  layer.append(stage, mount);
  document.body.append(layer);

  // The poster holds the picture while the canvas moves (no blank frame), then gets out of the way
  // so it doesn't ghost behind the zoom.
  const hero = heroHost.closest('.house');
  hero?.classList.add('is-handoff');

  // Same picture, bigger canvas: frame the house on the hero's spot, then move the canvas full-screen.
  const rect = heroRect(heroHost);
  engine.setTilt(0);
  engine.setFrame((w, h) => fitRect(w, h, rect), true);
  engine.setHost(stage);
  engine.nextFrame().then(() => {
    hero?.classList.remove('is-handoff');
    hero?.classList.add('is-away');
  });

  session = { engine, heroHost, content, layer, root: createRoot(mount), leaving: false };
  useHouse.getState().reset();
  render(session);
  if (push) history.pushState({ house: true }, '', '/house');
}

export function leave() {
  const s = session;
  if (!s || s.leaving) return;
  s.leaving = true;
  render(s); // fades the UI out; HouseApp stops driving the camera
  useHouse.getState().reset();

  const rect = heroRect(s.heroHost);
  s.engine.setLit({ main: true, studio: true, lab: true });
  s.engine.setFrame((w, h) => fitRect(w, h, rect), reduced(), 5);

  const done = () => {
    // Swap back into the hero: same framing, so nothing moves.
    s.engine.setFrame(fitPoster, true);
    const hero = s.heroHost.closest('.house');
    hero?.classList.replace('is-away', 'is-handoff');
    s.engine.setHost(s.heroHost);
    s.engine.nextFrame().then(() => hero?.classList.remove('is-handoff'));
    s.root.unmount();
    s.layer.remove();
    document.documentElement.classList.remove('in-house');
    session = null;
  };
  setTimeout(done, reduced() ? 0 : 750);
}

// Browser back/forward: the history entry decides whether we're inside.
let pending: (() => void) | null = null;
export function onHistory(reenter: () => void) {
  pending = reenter;
}
addEventListener('popstate', (e) => {
  if (e.state?.house) {
    if (!session) pending?.();
  } else if (session) leave();
});
