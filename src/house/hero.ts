/**
 * The live house in the home-page hero. Mounted by the loader in index.astro only after the page
 * is idle and the hero is visible (or on intent). No framework: three.js + our engine only.
 *
 * The house itself never moves here (the page around it doesn't, so moving it reads as the object
 * sliding about). Instead, things happen inside it when someone looks:
 *  - it rests in the arrival state: main room lit, studio and lab dark with light at the doorways;
 *  - on hover / keyboard focus the character turns, waves and says hello, the pet bounces, and the
 *    other rooms switch on one by one; they go dark again a moment after the pointer leaves;
 *  - on touch screens (no hover) that plays once, the first time the hero is on screen.
 */
import { HouseEngine } from './engine';
import { fitPoster } from './camera';
import { LIVE } from './actors';
import { track } from './overlay';

export const HERO_FPS = 30;
export const HERO_DPR = 1.5;

/** The hero's resting light: the same arrival state as inside the house (and as the poster). */
export const HERO_REST = { main: true, studio: false, lab: false };
const ALL_ON = { main: true, studio: true, lab: true };

export function mountHero(host: HTMLElement, onReady: () => void) {
  let ready = false;
  let looking = false;
  const engine = new HouseEngine(host, {
    maxDpr: HERO_DPR, // reduced resolution in the hero; full quality inside
    frame: fitPoster, // identical framing to the poster image underneath
    onFirstFrame: () => {
      engine.setInstant(false);
      ready = true;
      onReady();
      if (looking) hello();
    },
  });
  engine.setLit(HERO_REST, true);
  engine.setAmbient(HERO_FPS);

  // the talking box, pinned above the character's head
  const bubble = document.createElement('div');
  bubble.className = 'hero-bubble';
  bubble.setAttribute('aria-hidden', 'true');
  bubble.innerHTML = '<p>Hi! Come on in, I’ll show you around.</p>';
  host.appendChild(bubble);
  track(bubble, LIVE.me);

  // While the house is open (enter.ts), this engine belongs to the house: hands off.
  const inHouse = () => document.documentElement.classList.contains('in-house');
  let timers: number[] = [];
  const later = (ms: number, f: () => void) => timers.push(window.setTimeout(() => !inHouse() && f(), ms));
  const clear = () => {
    timers.forEach(clearTimeout);
    timers = [];
  };

  function hello() {
    if (inHouse()) return;
    clear();
    engine.greet(true);
    bubble.classList.add('is-on');
    // lights on, one room at a time
    later(150, () => engine.setLit({ ...HERO_REST, studio: true }));
    later(550, () => engine.setLit(ALL_ON));
  }
  function bye(keepLights = false) {
    clear();
    if (inHouse()) return bubble.classList.remove('is-on');
    later(350, () => {
      engine.greet(false);
      bubble.classList.remove('is-on');
    });
    if (!keepLights) later(1400, () => engine.setLit(HERO_REST));
  }

  const link = host.closest<HTMLElement>('.house') ?? host;
  const enter = () => {
    looking = true;
    if (ready) hello();
  };
  const leave = () => {
    looking = false;
    if (ready) bye();
  };
  link.addEventListener('pointerenter', (e) => e.pointerType === 'mouse' && enter());
  link.addEventListener('pointerleave', (e) => e.pointerType === 'mouse' && leave());
  link.addEventListener('focusin', enter);
  link.addEventListener('focusout', leave);

  // Touch screens can't hover: play it once, the first time the hero is properly in view.
  if (matchMedia('(hover: none)').matches) {
    const io = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting)) return;
        io.disconnect();
        const play = () => {
          hello();
          later(3600, () => bye(true));
        };
        if (ready) setTimeout(play, 500);
        else {
          const wait = setInterval(() => ready && (clearInterval(wait), play()), 200);
        }
      },
      { threshold: 0.6 },
    );
    io.observe(link);
  }

  return engine;
}
