/**
 * DOM overlay for hotspots and labels. Elements register a world position; after each rendered
 * frame we project them to screen pixels and move them with a transform. Labels never scale with
 * the camera zoom, which is the "counter-scale" the brief asks for.
 */
import * as THREE from 'three';

const items = new Map<HTMLElement, THREE.Vector3>();
const v = new THREE.Vector3();
/** Labels right of this x (px) open to the left of their dot, so they don't run under the window. */
let flipX = Infinity;
export function setFlipEdge(px: number) {
  flipX = px;
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
    const off = y < band.top || y > band.bottom || x < 4 || x > width - 4;
    if ((el.dataset.off === '1') !== off) el.dataset.off = off ? '1' : '';
    const side = x > flipX ? 'left' : 'right';
    if (el.dataset.side !== side) el.dataset.side = side;
  }
}
