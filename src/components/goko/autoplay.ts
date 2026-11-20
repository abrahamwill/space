/**
 * Shared autoplay for the coded GokoMart demos (same rules as the NusaFinance and gm.xyz demos):
 * - runs only while the demo is on screen and the tab is visible;
 * - any real pointer, key or focus inside it hands control to the visitor for good;
 * - under prefers-reduced-motion it never starts (each demo shows a finished still instead).
 */
export type Step = [fn: () => void, delayAfter: number];

export const reduceMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

export function autoplay(root: HTMLElement, steps: Step[], opts: { onStop?: () => void; startDelay?: number } = {}) {
  let stopped = false, visible = false, timer = 0, k = 0;
  const stop = () => {
    if (stopped) return;
    stopped = true;
    clearTimeout(timer);
    root.classList.add('is-yours');
    opts.onStop?.();
  };
  ['pointerdown', 'keydown', 'focusin'].forEach((ev) =>
    root.addEventListener(ev, (e) => { if ((e as Event).isTrusted) stop(); }, { capture: true }),
  );
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }, { threshold: 0.3 }).observe(root);
  const run = () => {
    if (stopped) return;
    if (!visible || document.hidden) { timer = window.setTimeout(run, 400); return; }
    const [fn, delay] = steps[k];
    fn();
    k = (k + 1) % steps.length;
    timer = window.setTimeout(run, delay);
  };
  timer = window.setTimeout(run, opts.startDelay ?? 700);
  return { stop, get stopped() { return stopped; } };
}

/** A soft ring at the centre of `el`, for scripted clicks. `tap` is a .gk-tap element inside `root`. */
export function tapAt(root: HTMLElement, tap: HTMLElement, el: Element) {
  const r0 = root.getBoundingClientRect();
  const r = el.getBoundingClientRect();
  tap.style.left = `${r.left - r0.left + r.width / 2}px`;
  tap.style.top = `${r.top - r0.top + r.height / 2}px`;
  tap.classList.remove('go');
  void tap.offsetWidth;
  tap.classList.add('go');
}

/** Steps that type `text` into an input one character at a time. */
export function typeSteps(input: HTMLInputElement, text: string, every = 90, after?: () => void): Step[] {
  const out: Step[] = [];
  for (let i = 1; i <= text.length; i++) {
    out.push([() => { input.value = text.slice(0, i); if (i === text.length) after?.(); }, every]);
  }
  return out;
}

export const fmt = (n: number) => n.toLocaleString('id-ID');
