/**
 * Camera maths for the orthographic 2:1 dimetric view. Shared by the hero, the house page and the
 * poster renderer, so the poster and the live scene frame the house identically.
 */
import * as THREE from 'three';
import { RIM, H, ELEVATION, AZIMUTH, ANCHORS, type AnchorId } from './layout';
import { toWorld } from './geometry';

export function basis(azimuth = AZIMUTH) {
  const ce = Math.cos(ELEVATION), se = Math.sin(ELEVATION);
  const d = new THREE.Vector3(ce * Math.sin(azimuth), se, ce * Math.cos(azimuth)); // toward the camera
  const r = new THREE.Vector3(Math.cos(azimuth), 0, -Math.sin(azimuth)); // screen right
  const u = new THREE.Vector3(-se * Math.sin(azimuth), ce, -se * Math.cos(azimuth)); // screen up
  return { d, r, u };
}

/** The visible drawing is exactly the rim polygon at wall-top height, so frame that. */
const rimWorld = RIM.map(([x, y]) => toWorld([x, y, H]));

export function houseBounds(azimuth = AZIMUTH) {
  const { r, u } = basis(azimuth);
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const p of rimWorld) {
    const sx = p.dot(r), sy = p.dot(u);
    minX = Math.min(minX, sx); maxX = Math.max(maxX, sx);
    minY = Math.min(minY, sy); maxY = Math.max(maxY, sy);
  }
  return { w: maxX - minX, h: maxY - minY, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 };
}

export interface Insets { top: number; right: number; bottom: number; left: number }

export interface Framing {
  zoom: number; // px per world unit
  target: THREE.Vector3;
}

/** Fit the whole house inside the viewport minus insets (px). */
export function fitHouse(width: number, height: number, inset: Insets): Framing {
  const b = houseBounds();
  const { r, u } = basis();
  const aw = Math.max(1, width - inset.left - inset.right);
  const ah = Math.max(1, height - inset.top - inset.bottom);
  const zoom = Math.min(aw / b.w, ah / b.h);
  // Point whose screen position is the bbox centre, then shift so it lands in the middle of the free area.
  const target = r.clone().multiplyScalar(b.cx).addScaledVector(u, b.cy);
  const ox = (inset.left - inset.right) / 2, oy = (inset.top - inset.bottom) / 2;
  target.addScaledVector(r, -ox / zoom).addScaledVector(u, oy / zoom);
  return { zoom, target };
}

/** Poster/hero framing: equal padding as a fraction of the width. Aspect = poster image aspect. */
export const POSTER_PAD = 0.012;
export function posterAspect() {
  const b = houseBounds();
  return 1 / ((1 - 2 * POSTER_PAD) * (b.h / b.w) + 2 * POSTER_PAD); // width / height
}
export function fitPoster(width: number, height: number): Framing {
  const p = width * POSTER_PAD;
  return fitHouse(width, height, { top: p, right: p, bottom: p, left: p });
}

/** Zoom into a room: ~2.1× the overview, room centre placed in the middle of the free area. */
export const ROOM_ZOOM = 2.1;
export function fitRoom(overview: Framing, centre: AnchorId, inset: Insets, scale = ROOM_ZOOM): Framing {
  const zoom = overview.zoom * scale;
  const { r, u } = basis();
  const c = toWorld(ANCHORS[centre]);
  const ox = (inset.left - inset.right) / 2, oy = (inset.top - inset.bottom) / 2;
  const target = c.addScaledVector(r, -ox / zoom).addScaledVector(u, oy / zoom);
  return { zoom, target };
}

/** Place an orthographic camera looking at `target` from the dimetric angle (plus tilt). */
export function applyCamera(cam: THREE.OrthographicCamera, target: THREE.Vector3, zoom: number, tilt = 0) {
  const { d } = basis(AZIMUTH + tilt);
  cam.position.copy(target).addScaledVector(d, 100);
  cam.up.set(0, 1, 0);
  cam.lookAt(target);
  cam.zoom = zoom;
  cam.near = 0.1;
  cam.far = 400;
  cam.updateProjectionMatrix();
}
