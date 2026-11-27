/**
 * DOM overlay for hotspots and labels. Elements register a world position; after each rendered
 * frame we project them to screen pixels and move them with a transform. Labels never scale with
 * the camera zoom, which is the "counter-scale" the brief asks for.
 */
import * as THREE from 'three';

const items = new Map<HTMLElement, THREE.Vector3>();
const v = new THREE.Vector3();
/** Where labels must stop on the right (px): the open window's left edge, or the screen's. */
let rightEdge = Infinity;
export function setFlipEdge(px: number) {
  rightEdge = px;
}
/** A pin's label width (px), measured once it's laid out (the text never changes). */
const widths = new WeakMap<HTMLElement, number>();
function labelWidth(el: HTMLElement) {
  let w = widths.get(el);
  if (!w) {
    w = (el.querySelector('.hx-hotspot-label') as HTMLElement | null)?.scrollWidth ?? 0; // natural width, even when trimmed
    if (w) widths.set(el, w);
  }
  return w;
}
/** Pins outside this vertical band (px) are hidden: they'd sit under the HUD or the bottom sheet. */
let band = { top: -Infinity, bottom: Infinity };
export function setVisibleBand(top: number, bottom: number) {
  band = { top, bottom };
}

export function track(el: HTMLElement, world: THREE.Vector3) {
  items.set(el, world);
  return () => void items.delete(el);
}

export function updateOverlay(camera: THREE.Camera, width: number, height: number) {
  for (const [el, world] of items) {
    v.copy(world).project(camera);
    let x = (v.x * 0.5 + 0.5) * width;
    const y = (-v.y * 0.5 + 0.5) * height;
    // room labels stay on screen (they're how you get to a room you can't see yet)
    if (el.dataset.clamp) x = Math.max(84, Math.min(width - 84, x));
    el.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
    // off screen, or under the HUD, the bottom sheet or (desktop) the window: can't be clicked, so hidden
    const off = y < band.top || y > band.bottom || x < 4 || x > Math.min(width - 4, rightEdge + 8);
    if ((el.dataset.off === '1') !== off) el.dataset.off = off ? '1' : '';
    // a label opens to the right of its dot if it fits, else to the left, else toward the roomier side
    const lw = labelWidth(el) + 24; // the dot and the gap
    const edge = Math.min(rightEdge, width) - 8;
    const fits = x + lw <= edge ? 'right' : x - lw >= 8 ? 'left' : null;
    const side = fits ?? (x > edge / 2 ? 'left' : 'right');
    if (el.dataset.side !== side) el.dataset.side = side;
    // too long for either side (a long label on a phone): trim it to the room there is
    const max = fits ? '' : `${Math.max(60, Math.round(side === 'right' ? edge - x - 24 : x - 8 - 24))}px`;
    if (el.style.getPropertyValue('--label-max') !== max) el.style.setProperty('--label-max', max);
  }
}
