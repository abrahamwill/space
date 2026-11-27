/**
 * Live screens in the Pinwheel house: tiny pixel canvases on the GLB's own screen faces, redrawn about
 * 12 times a second while the house is alive (the old house's src/house/screens.ts, on the new model).
 *
 *  - lab arcade (`lab_arcade_Arcade`, its `glow_#86ad57` face): the cozy pet game. A snack falls and the
 *    pet hops over to catch it. When he's playing (the arcade hotspot sends him there) it speeds up and
 *    shows "P1".
 *
 * The GLB has no UVs, so each screen face gets them here: u along its horizontal edge, v up. The first
 * frame keeps the face's own green as the background, so the hero poster and the live house still match.
 * Until the Blender file names its screens (`screen:<id>`, design/house-v2-blender.md), faces are found
 * by object name and material.
 */
import * as THREE from 'three';

type Draw = (g: CanvasRenderingContext2D, w: number, h: number, t: number, playing: boolean) => void;

const rect = (g: CanvasRenderingContext2D, c: string, x: number, y: number, w: number, h: number) => {
  g.fillStyle = c;
  g.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
};

const C = { bg: '#86ad57', ground: '#6e9447', snack: '#c8442b', pet: '#fbf3e6', ink: '#1b1a17', score: '#e0a72e' };

const arcade: Draw = (g, w, h, t0, playing) => {
  const t = playing ? t0 * 1.8 : t0;
  rect(g, C.bg, 0, 0, w, h);
  rect(g, C.ground, 0, h - 6, w, 6);
  if (playing) {
    // "P1", top right
    const x = w - 10;
    rect(g, C.snack, x, 2, 1, 5); rect(g, C.snack, x + 1, 2, 2, 1); rect(g, C.snack, x + 1, 4, 2, 1); rect(g, C.snack, x + 2, 3, 1, 1);
    rect(g, C.snack, x + 5, 2, 1, 5); rect(g, C.snack, x + 4, 3, 1, 1);
  }
  // a snack falls; the pet hops over to catch it
  const cycle = 3.2;
  const n = Math.floor(t / cycle);
  const k = (t % cycle) / cycle;
  const span = Math.max(1, w - 16);
  const fx = 8 + ((n * 37) % span);
  const fy = 2 + k * (h - 13);
  if (k < 0.92) rect(g, C.snack, fx - 1, fy, 3, 3);
  const prev = 8 + ((((n - 1) * 37) % span) + span) % span;
  const px = prev + (fx - prev) * Math.min(1, k * 1.4);
  const hop = Math.abs(Math.sin(t * 7)) * 3;
  const py = h - 6 - 6 - hop;
  rect(g, C.pet, px - 3, py, 7, 6);
  rect(g, C.pet, px - 2, py - 2, 1, 2);
  rect(g, C.pet, px + 2, py - 2, 1, 2);
  rect(g, C.ink, px - 1, py + 2, 1, 1);
  rect(g, C.ink, px + 2, py + 2, 1, 1);
  // score: one more pip per catch
  for (let i = 0; i < (n % 6) + 1; i++) rect(g, C.score, 2 + i * 3, 2, 2, 2);
};

const SCREENS: Array<{ object: string; material: string; draw: Draw; pxPerM: number }> = [
  { object: 'lab_arcade_Arcade', material: 'glow_#86ad57', draw: arcade, pxPerM: 110 },
];

export interface Screens {
  /** t: seconds since start. playing: he's at the arcade. Redraws at ~12 fps. */
  update(t: number, playing: boolean): void;
  dispose(): void;
}

export function addScreens(house: THREE.Object3D): Screens {
  const items: Array<{ ctx: CanvasRenderingContext2D; tex: THREE.CanvasTexture; w: number; h: number; draw: Draw }> = [];
  const trash: Array<{ dispose(): void }> = [];
  house.updateMatrixWorld(true);

  for (const s of SCREENS) {
    let face: THREE.Mesh | null = null;
    house.getObjectByName(s.object)?.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh && !Array.isArray(m.material) && m.material.name === s.material) face = m;
    });
    if (!face) continue;
    const mesh = face as THREE.Mesh;
    const geo = mesh.geometry.clone();
    const pos = geo.attributes.position as THREE.BufferAttribute;

    // the face's own frame, in world space: normal, up (world Y flattened onto it), right
    const pts = Array.from({ length: pos.count }, (_, i) => new THREE.Vector3().fromBufferAttribute(pos, i).applyMatrix4(mesh.matrixWorld));
    const normal = new THREE.Vector3().crossVectors(pts[1].clone().sub(pts[0]), pts[2].clone().sub(pts[0])).normalize();
    const up = new THREE.Vector3(0, 1, 0).projectOnPlane(normal);
    if (up.lengthSq() < 1e-6) up.set(0, 0, -1).projectOnPlane(normal); // a face lying flat
    up.normalize();
    let right = new THREE.Vector3().crossVectors(up, normal).normalize();
    // read left to right as seen from the camera side (+X +Z)
    if (right.dot(new THREE.Vector3(1, 0, -1)) < 0) right = right.negate();
    const us = pts.map((p) => p.dot(right)), vs = pts.map((p) => p.dot(up));
    const [u0, u1, v0, v1] = [Math.min(...us), Math.max(...us), Math.min(...vs), Math.max(...vs)];
    const uv = new Float32Array(pos.count * 2);
    pts.forEach((_, i) => {
      uv[i * 2] = (us[i] - u0) / (u1 - u0 || 1);
      uv[i * 2 + 1] = (vs[i] - v0) / (v1 - v0 || 1);
    });
    geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));

    const w = Math.max(24, Math.round((u1 - u0) * s.pxPerM));
    const h = Math.max(18, Math.round((v1 - v0) * s.pxPerM));
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d')!;
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.magFilter = THREE.NearestFilter;
    tex.minFilter = THREE.NearestFilter;
    tex.generateMipmaps = false;
    const mat = new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide, toneMapped: false });
    mat.name = `${s.material}_screen`;
    mesh.geometry = geo;
    mesh.material = mat;
    trash.push(geo, mat, tex);
    s.draw(ctx, w, h, 0, false);
    tex.needsUpdate = true;
    items.push({ ctx, tex, w, h, draw: s.draw });
  }

  let last = -1;
  let wasPlaying = false;
  return {
    update(t, playing) {
      const tick = Math.floor(t * 12);
      if (tick === last && playing === wasPlaying) return;
      last = tick;
      wasPlaying = playing;
      for (const it of items) {
        it.draw(it.ctx, it.w, it.h, t, playing);
        it.tex.needsUpdate = true;
      }
    },
    dispose() {
      trash.forEach((d) => d.dispose());
    },
  };
}
