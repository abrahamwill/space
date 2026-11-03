/**
 * Turns the layout (layout.ts) into GPU buffers. Per room: one flat-coloured mesh and one batch
 * of ink outlines for the furniture, the same again for each wall (so near walls can be cut away
 * when the view rotates), plus an ink "hull" mesh that outlines the spheres.
 *
 * Colours are written raw (hex / 255) and the canvas runs without colour management, so on screen
 * they match the hex exactly. Box sides carry two colours (the art's lighter "left" and darker
 * "right"); the shader picks one by which side of the screen the face points to, so the light
 * stays consistent from every angle.
 */
import * as THREE from 'three';
import { buildHouse, H, RIM, SPILL, Z_SQUASH as S, FACE_NORMAL, type Face, type Prim, type RoomId, type V3 } from './layout';

/** Plan (x, y, z) → world (x, z·S, y). */
export const toWorld = (p: V3): THREE.Vector3 => new THREE.Vector3(p[0], p[2] * S, p[1]);

const rgb = (hex: string) => {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255] as const;
};
type RGB = readonly [number, number, number];

export interface Batch {
  mesh: THREE.BufferGeometry;
  lines: Float32Array;
}
export interface RoomBuffers {
  base: Batch;
  /** Cylinder silhouette edges: A for views along the x=y diagonal (default), B for the other diagonal. */
  silA: Float32Array;
  silB: Float32Array;
  hull: THREE.BufferGeometry | null;
  walls: Partial<Record<Face, Batch>>;
}

/** Ink outline width in world units. The 2D art's 1.5px line at its render scale works out to ~0.03. */
export const LINE_WORLD = 0.03;
const HULL = LINE_WORLD * 0.9;

/** Sphere highlight: a cap on top, so it reads the same from every side. */
const HI_DIR = new THREE.Vector3(0, 1, 0);
const HI_COS = 0.905;
const NO_SIDE: readonly [number, number] = [0, 0];

class Builder {
  pos: number[] = [];
  col: number[] = [];
  col2: number[] = [];
  side: number[] = [];
  lines: number[] = [];

  tri(a: THREE.Vector3, b: THREE.Vector3, c: THREE.Vector3, color: RGB, color2: RGB = color, n: readonly [number, number] = NO_SIDE) {
    this.pos.push(a.x, a.y, a.z, b.x, b.y, b.z, c.x, c.y, c.z);
    for (let i = 0; i < 3; i++) {
      this.col.push(color[0], color[1], color[2]);
      this.col2.push(color2[0], color2[1], color2[2]);
      this.side.push(n[0], n[1]);
    }
  }
  /** Convex polygon, optionally outlined. */
  poly(pts: THREE.Vector3[], fill: RGB, ol: boolean, fill2: RGB = fill, n: readonly [number, number] = NO_SIDE) {
    if (pts.length <= 4) {
      for (let i = 1; i < pts.length - 1; i++) this.tri(pts[0], pts[i], pts[i + 1], fill, fill2, n);
    } else {
      // circles: fan from the centre (no slivers)
      const m = pts.reduce((a, p) => a.add(p), new THREE.Vector3()).divideScalar(pts.length);
      for (let i = 0; i < pts.length; i++) this.tri(m, pts[i], pts[(i + 1) % pts.length], fill, fill2, n);
    }
    if (ol) this.loop(pts);
  }
  seg(a: THREE.Vector3, b: THREE.Vector3, out = this.lines) {
    out.push(a.x, a.y, a.z, b.x, b.y, b.z);
  }
  loop(pts: THREE.Vector3[]) {
    for (let i = 0; i < pts.length; i++) this.seg(pts[i], pts[(i + 1) % pts.length]);
  }
  batch(): Batch {
    const mesh = new THREE.BufferGeometry();
    mesh.setAttribute('position', new THREE.Float32BufferAttribute(this.pos, 3));
    mesh.setAttribute('color', new THREE.Float32BufferAttribute(this.col, 3));
    mesh.setAttribute('color2', new THREE.Float32BufferAttribute(this.col2, 3));
    mesh.setAttribute('sideN', new THREE.Float32BufferAttribute(this.side, 2));
    mesh.computeBoundingSphere();
    return { mesh, lines: new Float32Array(this.lines) };
  }
}

class RoomBuilder {
  base = new Builder();
  walls = new Map<Face, Builder>();
  silA: number[] = [];
  silB: number[] = [];
  hulls: THREE.BufferGeometry[] = [];

  add(p: Prim) {
    let b = this.base;
    if (p.face) {
      if (!this.walls.has(p.face)) this.walls.set(p.face, new Builder());
      b = this.walls.get(p.face)!;
    }
    switch (p.t) {
      case 'poly':
        return b.poly(p.pts.map(toWorld), rgb(p.fill), p.ol);
      case 'box': {
        const { x, y, z, w, d, h } = p;
        const W = (a: number, bb: number, c: number) => toWorld([a, bb, c]);
        const L = rgb(p.left), R = rgb(p.right);
        b.poly([W(x, y, z + h), W(x + w, y, z + h), W(x + w, y + d, z + h), W(x, y + d, z + h)], rgb(p.top), p.ol);
        // sides; sideN is the face normal in world xz (plan x, plan y)
        b.poly([W(x, y + d, z), W(x + w, y + d, z), W(x + w, y + d, z + h), W(x, y + d, z + h)], L, p.ol, R, [0, 1]);
        b.poly([W(x + w, y, z), W(x + w, y + d, z), W(x + w, y + d, z + h), W(x + w, y, z + h)], L, p.ol, R, [1, 0]);
        b.poly([W(x, y, z), W(x + w, y, z), W(x + w, y, z + h), W(x, y, z + h)], L, p.ol, R, [0, -1]);
        b.poly([W(x, y, z), W(x, y + d, z), W(x, y + d, z + h), W(x, y, z + h)], L, p.ol, R, [-1, 0]);
        return;
      }
      case 'cyl': {
        const n = 24;
        const at = (a: number, zz: number) => toWorld([p.cx + p.r * Math.cos(a), p.cy + p.r * Math.sin(a), zz]);
        const ring = (zz: number) => Array.from({ length: n }, (_, i) => at((i * 2 * Math.PI) / n, zz));
        const bot = ring(p.z), top = ring(p.z + p.h);
        const side = rgb(p.side);
        for (let i = 0; i < n; i++) {
          const j = (i + 1) % n;
          b.tri(bot[i], bot[j], top[j], side);
          b.tri(bot[i], top[j], top[i], side);
        }
        b.poly(top, rgb(p.top), false);
        if (p.ol) {
          b.loop(top);
          b.loop(bot); // the back half is hidden by the body
          // silhouette edges depend on the view diagonal
          for (const a of [(3 * Math.PI) / 4, -Math.PI / 4]) b.seg(at(a, p.z), at(a, p.z + p.h), this.silA);
          for (const a of [Math.PI / 4, (5 * Math.PI) / 4]) b.seg(at(a, p.z), at(a, p.z + p.h), this.silB);
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
        const nn = new THREE.Vector3();
        for (let i = 0; i < a.count; i += 3) {
          for (let k = 0; k < 3; k++) v[k].fromBufferAttribute(a, i + k);
          nn.copy(v[0]).add(v[1]).add(v[2]).normalize();
          b.tri(v[0].clone().add(c), v[1].clone().add(c), v[2].clone().add(c), p.hi && nn.dot(HI_DIR) > HI_COS ? hi : fill);
        }
        g.dispose();
        if (p.ol) this.hulls.push(new THREE.SphereGeometry(p.r + HULL, 20, 14).translate(c.x, c.y, c.z));
        return;
      }
    }
  }

  finish(): RoomBuffers {
    let hull: THREE.BufferGeometry | null = null;
    if (this.hulls.length) {
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
    const walls: Partial<Record<Face, Batch>> = {};
    for (const [f, b] of this.walls) walls[f] = b.batch();
    return { base: this.base.batch(), silA: new Float32Array(this.silA), silB: new Float32Array(this.silB), hull, walls };
  }
}

let cache: Record<RoomId, RoomBuffers> | null = null;

/** Built once per page and shared. */
export function getRoomBuffers(): Record<RoomId, RoomBuffers> {
  if (cache) return cache;
  const prims = buildHouse();
  const out = {} as Record<RoomId, RoomBuffers>;
  for (const room of Object.keys(prims) as RoomId[]) {
    const b = new RoomBuilder();
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

/** The ink rim at wall-top height, grouped by which way each edge faces (outward). */
export function rimLines(): Partial<Record<Face, Float32Array>> {
  const out: Partial<Record<Face, number[]>> = {};
  RIM.forEach(([x0, y0], i) => {
    const [x1, y1] = RIM[(i + 1) % RIM.length];
    // RIM runs clockwise on screen, so (dy, -dx) points outward
    const nx = Math.sign(y1 - y0), ny = Math.sign(-(x1 - x0));
    const face = (Object.keys(FACE_NORMAL) as Face[]).find((f) => FACE_NORMAL[f][0] === nx && FACE_NORMAL[f][1] === ny)!;
    const a = toWorld([x0, y0, H + 0.01]), b = toWorld([x1, y1, H + 0.01]);
    (out[face] ??= []).push(a.x, a.y, a.z, b.x, b.y, b.z);
  });
  const res: Partial<Record<Face, Float32Array>> = {};
  for (const f of Object.keys(out) as Face[]) res[f] = new Float32Array(out[f]!);
  return res;
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

/** One moving part (character limb, pet body, record): flat mesh + outlines + sphere hulls, in local coordinates. */
export function buildPart(prims: Prim[]): { batch: Batch; hull: THREE.BufferGeometry | null } {
  const b = new RoomBuilder();
  prims.forEach((p) => b.add(p));
  const r = b.finish();
  // cylinders in parts are short and squat, so the A silhouettes are good enough from every side
  const lines = new Float32Array(r.base.lines.length + r.silA.length);
  lines.set(r.base.lines);
  lines.set(r.silA, r.base.lines.length);
  return { batch: { mesh: r.base.mesh, lines }, hull: r.hull };
}
