/**
 * Turns the layout (layout.ts) into GPU buffers: per room, one flat-coloured mesh, one batch of
 * ink outline segments, and one ink "hull" mesh that outlines the spheres. Colours are written raw
 * (hex / 255) and the canvas runs without colour management, so on screen they match the hex exactly.
 */
import * as THREE from 'three';
import { buildHouse, H, RIM, SPILL, Z_SQUASH as S, ELEVATION, AZIMUTH, type Prim, type RoomId, type V3 } from './layout';

/** Plan (x, y, z) → world (x, z·S, y). */
export const toWorld = (p: V3): THREE.Vector3 => new THREE.Vector3(p[0], p[2] * S, p[1]);

const rgb = (hex: string) => {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255] as const;
};

export interface RoomBuffers {
  mesh: THREE.BufferGeometry;
  lines: Float32Array;
  hull: THREE.BufferGeometry | null;
}

/** Ink outline width in world units. The 2D art's 1.5px line at its render scale works out to ~0.03. */
export const LINE_WORLD = 0.03;
const HULL = LINE_WORLD * 0.9;

/** Highlight direction for spheres: the art puts it just above centre, toward the camera. */
const VIEW = new THREE.Vector3(Math.cos(ELEVATION) * Math.sin(AZIMUTH), Math.sin(ELEVATION), Math.cos(ELEVATION) * Math.cos(AZIMUTH));
const UP = new THREE.Vector3(-Math.sin(ELEVATION) * Math.sin(AZIMUTH), Math.cos(ELEVATION), -Math.sin(ELEVATION) * Math.cos(AZIMUTH));
const HI_DIR = VIEW.clone().addScaledVector(UP, 0.95).normalize();
const HI_COS = 0.905;

class Builder {
  pos: number[] = [];
  col: number[] = [];
  lines: number[] = [];
  hulls: THREE.BufferGeometry[] = [];

  tri(a: THREE.Vector3, b: THREE.Vector3, c: THREE.Vector3, color: readonly number[]) {
    this.pos.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z);
    for (let i = 0; i < 3; i++) this.col.push(color[0], color[1], color[2]);
  }
  /** Convex polygon as a triangle fan, optionally outlined. */
  poly(pts: THREE.Vector3[], fill: string, ol: boolean) {
    const c = rgb(fill);
    if (pts.length <= 4) {
      for (let i = 1; i < pts.length - 1; i++) this.tri(pts[0], pts[i], pts[i + 1], c);
    } else {
      // Circles: fan from the centre. A fan from a rim vertex makes slivers whose polygon-offset
      // depth is unstable on some GPUs, which shows up as a starburst on wall decals.
      const m = pts.reduce((a, p) => a.add(p), new THREE.Vector3()).divideScalar(pts.length);
      for (let i = 0; i < pts.length; i++) this.tri(m, pts[i], pts[(i + 1) % pts.length], c);
    }
    if (ol) this.loop(pts);
  }
  seg(a: THREE.Vector3, b: THREE.Vector3) {
    this.lines.push(a.x, a.y, a.z, b.x, b.y, b.z);
  }
  loop(pts: THREE.Vector3[], closed = true) {
    for (let i = 0; i < pts.length - (closed ? 0 : 1); i++) this.seg(pts[i], pts[(i + 1) % pts.length]);
  }

  add(p: Prim) {
    switch (p.t) {
      case 'poly':
        return this.poly(p.pts.map(toWorld), p.fill, p.ol);
      case 'box': {
        const { x, y, z, w, d, h } = p;
        const W = (a: number, b: number, c: number) => toWorld([a, b, c]);
        this.poly([W(x, y, z + h), W(x + w, y, z + h), W(x + w, y + d, z + h), W(x, y + d, z + h)], p.top, p.ol);
        this.poly([W(x, y + d, z), W(x + w, y + d, z), W(x + w, y + d, z + h), W(x, y + d, z + h)], p.left, p.ol);
        this.poly([W(x + w, y, z), W(x + w, y + d, z), W(x + w, y + d, z + h), W(x + w, y, z + h)], p.right, p.ol);
        return;
      }
      case 'cyl': {
        const n = 24;
        const ring = (zz: number) =>
          Array.from({ length: n }, (_, i) => {
            const a = (i * 2 * Math.PI) / n;
            return toWorld([p.cx + p.r * Math.cos(a), p.cy + p.r * Math.sin(a), zz]);
          });
        const b = ring(p.z), t = ring(p.z + p.h);
        const side = rgb(p.side);
        for (let i = 0; i < n; i++) {
          const j = (i + 1) % n;
          this.tri(b[i], b[j], t[j], side);
          this.tri(b[i], t[j], t[i], side);
        }
        this.poly(t, p.top, false);
        if (p.ol) {
          this.loop(t);
          // front half of the base, and the two silhouette edges for the default camera angle
          for (let i = 0; i < n; i++) {
            const a = (i * 2 * Math.PI) / n, a2 = ((i + 1) * 2 * Math.PI) / n;
            if (Math.sin(a + Math.PI / 4) > -0.05 && Math.sin(a2 + Math.PI / 4) > -0.05) this.seg(b[i], b[(i + 1) % n]);
          }
          for (const a of [(3 * Math.PI) / 4, -Math.PI / 4]) {
            const pt = (zz: number) => toWorld([p.cx + p.r * Math.cos(a), p.cy + p.r * Math.sin(a), zz]);
            this.seg(pt(p.z), pt(p.z + p.h));
          }
        }
        return;
      }
      case 'ball': {
        // Spheres stay round on screen: offsets are not squashed, only the centre is.
        const c = new THREE.Vector3(p.cx, p.z * S, p.cy);
        const g = new THREE.SphereGeometry(p.r, 20, 14).toNonIndexed();
        const a = g.getAttribute('position');
        const fill = rgb(p.fill), hi = p.hi ? rgb(p.hi) : fill;
        const v = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()];
        const n = new THREE.Vector3();
        for (let i = 0; i < a.count; i += 3) {
          for (let k = 0; k < 3; k++) v[k].fromBufferAttribute(a, i + k);
          n.copy(v[0]).add(v[1]).add(v[2]).normalize();
          const color = p.hi && n.dot(HI_DIR) > HI_COS ? hi : fill;
          this.tri(v[0].clone().add(c), v[1].clone().add(c), v[2].clone().add(c), color);
        }
        g.dispose();
        if (p.ol) this.hulls.push(new THREE.SphereGeometry(p.r + HULL, 20, 14).translate(c.x, c.y, c.z));
        return;
      }
    }
  }

  finish(): RoomBuffers {
    const mesh = new THREE.BufferGeometry();
    mesh.setAttribute('position', new THREE.Float32BufferAttribute(this.pos, 3));
    mesh.setAttribute('color', new THREE.Float32BufferAttribute(this.col, 3));
    mesh.computeBoundingSphere();
    let hull: THREE.BufferGeometry | null = null;
    if (this.hulls.length) {
      // merge by hand (avoids pulling in BufferGeometryUtils)
      const all: number[] = [];
      for (const h of this.hulls) {
        const nh = h.toNonIndexed();
        all.push(...(nh.getAttribute('position').array as Float32Array));
        h.dispose();
        nh.dispose();
      }
      hull = new THREE.BufferGeometry();
      hull.setAttribute('position', new THREE.Float32BufferAttribute(all, 3));
      hull.computeBoundingSphere();
    }
    return { mesh, lines: new Float32Array(this.lines), hull };
  }
}

let cache: Record<RoomId, RoomBuffers> | null = null;

/** Built once per page and shared (hero and house never mount at the same time). */
export function getRoomBuffers(): Record<RoomId, RoomBuffers> {
  if (cache) return cache;
  const prims = buildHouse();
  const out = {} as Record<RoomId, RoomBuffers>;
  for (const room of Object.keys(prims) as RoomId[]) {
    const b = new Builder();
    prims[room].forEach((p) => b.add(p));
    out[room] = b.finish();
  }
  return (cache = out);
}

/** Page surface at wall-top height with the floor plan cut out. Rendered depth-only. */
export function surfaceGeometry(): THREE.BufferGeometry {
  const big = 200;
  const shape = new THREE.Shape([
    new THREE.Vector2(-big, -big), new THREE.Vector2(big, -big), new THREE.Vector2(big, big), new THREE.Vector2(-big, big),
  ]);
  shape.holes.push(new THREE.Path(RIM.map(([x, y]) => new THREE.Vector2(x, y))));
  const g = new THREE.ShapeGeometry(shape);
  g.rotateX(Math.PI / 2); // (x, y, 0) → (x, 0, y)
  g.translate(0, H * S, 0);
  return g;
}

export function rimLine(): Float32Array {
  const pts = RIM.map(([x, y]) => toWorld([x, y, H + 0.01]));
  const out: number[] = [];
  pts.forEach((p, i) => {
    const q = pts[(i + 1) % pts.length];
    out.push(p.x, p.y, p.z, q.x, q.y, q.z);
  });
  return new Float32Array(out);
}

export function spillGeometry(room: RoomId): THREE.BufferGeometry | null {
  const pts = SPILL[room];
  if (!pts) return null;
  const w = pts.map((p) => toWorld([p[0], p[1], 0.03]));
  const pos: number[] = [];
  for (let i = 1; i < w.length - 1; i++) pos.push(...w[0].toArray(), ...w[i].toArray(), ...w[i + 1].toArray());
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  return g;
}
