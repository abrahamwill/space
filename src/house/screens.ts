/**
 * Looping screens: tiny pixel canvases redrawn ~12 times a second while the scene is alive.
 *  - studio monitor: a layout being designed, block by block
 *  - lab arcade: the cozy pet game (a pet hops after falling snacks)
 *  - lab bench: three coded prototypes, scrolling, with a tap now and then
 * Screens aren't tinted when a room is dark, so they glow through the doorways.
 */
import { BufferGeometry, CanvasTexture, Float32BufferAttribute, Mesh, MeshBasicMaterial, NearestFilter, NoColorSpace, type Scene } from 'three';
import { toWorld } from './geometry';
import { P, SCREENS, type ScreenId } from './layout';

type Draw = (g: CanvasRenderingContext2D, w: number, h: number, t: number) => void;

/** Someone is at the arcade: the game speeds up and shows a player marker. */
let arcadePlaying = false;

const rect = (g: CanvasRenderingContext2D, c: string, x: number, y: number, w: number, h: number) => {
  g.fillStyle = c;
  g.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
};

const monitor: Draw = (g, w, h, t) => {
  rect(g, '#2a2a2c', 0, 0, w, h);
  const loop = t % 8; // seconds
  // window chrome
  rect(g, P.mus, 3, 3, w - 6, 4);
  rect(g, '#3a3a3c', 3, 7, w - 6, h - 10);
  // blocks appear one by one, like a layout being built
  const blocks: Array<[number, number, number, number, string]> = [
    [6, 10, 22, 4, P.cream], [6, 16, 14, 2, '#8a8478'], [6, 20, 16, 2, '#8a8478'],
    [32, 10, 24, 12, P.red], [6, 25, 10, 6, P.cob], [18, 25, 10, 6, P.cob], [30, 25, 10, 6, P.cob], [42, 25, 14, 6, P.mus],
  ];
  const shown = Math.min(blocks.length, Math.floor(loop / 0.75));
  blocks.slice(0, shown).forEach(([x, y, bw, bh, c]) => rect(g, c, x, y, bw, bh));
  // the cursor heads for the next block, blinking while it waits
  const nb = blocks[Math.min(shown, blocks.length - 1)];
  const k = (loop % 0.75) / 0.75;
  const cx = nb[0] + nb[2] * k, cy = nb[1] + nb[3] * 0.5;
  if (Math.floor(t * 4) % 2 === 0 || shown >= blocks.length) rect(g, '#ffffff', cx, cy, 1, 3);
};

const arcade: Draw = (g, w, h, t0) => {
  const t = arcadePlaying ? t0 * 1.8 : t0;
  rect(g, P.leaf2, 0, 0, w, h);
  if (arcadePlaying) {
    // "P1" in the corner
    rect(g, P.red, w - 9, 3, 2, 5); rect(g, P.red, w - 7, 3, 2, 2); rect(g, P.red, w - 4, 3, 1, 5);
  }
  rect(g, '#6e9447', 0, h - 7, w, 7);
  // a snack falls; the pet hops over to catch it
  const cycle = 3.2;
  const n = Math.floor(t / cycle);
  const k = (t % cycle) / cycle;
  const fx = 8 + ((n * 37) % (w - 16));
  const fy = 2 + k * (h - 14);
  if (k < 0.92) rect(g, P.red, fx - 1, fy, 3, 3);
  const prev = 8 + (((n - 1) * 37 + w * 10) % (w - 16));
  const px = prev + (fx - prev) * Math.min(1, k * 1.4);
  const hop = Math.abs(Math.sin(t * 7)) * 4;
  const py = h - 7 - 6 - hop;
  rect(g, P.cream, px - 3, py, 7, 6);
  rect(g, P.cream, px - 2, py - 2, 1, 2);
  rect(g, P.cream, px + 2, py - 2, 1, 2);
  rect(g, '#1a1a1a', px - 1, py + 2, 1, 1);
  rect(g, '#1a1a1a', px + 2, py + 2, 1, 1);
  // score
  for (let i = 0; i < (n % 6) + 1; i++) rect(g, P.mus, 3 + i * 3, 3, 2, 2);
};

const prototype = (accent: string, offset: number): Draw => (g, w, h, t) => {
  rect(g, P.cream, 0, 0, w, h);
  rect(g, accent, 0, 0, w, 5);
  // cards scrolling up
  const scroll = ((t + offset) * 6) % 9;
  for (let i = -1; i < 5; i++) {
    const y = 7 + i * 9 - scroll;
    if (y > h) continue;
    rect(g, '#e2d7c4', 2, y, w - 4, 7);
    rect(g, accent, 3, y + 1, 4, 4);
    rect(g, '#b9ad99', 9, y + 2, w - 12, 1);
    rect(g, '#b9ad99', 9, y + 4, w - 15, 1);
  }
  // a tap, now and then
  const tap = (t + offset) % 2.5;
  if (tap < 0.35) {
    const r = 1 + tap * 8;
    g.strokeStyle = 'rgba(27,26,23,0.6)';
    g.beginPath();
    g.arc(w / 2, h * 0.6, r, 0, Math.PI * 2);
    g.stroke();
  }
};

const DRAW: Record<ScreenId, Draw> = {
  monitor,
  arcade,
  bench0: prototype(P.cob, 0),
  bench1: prototype(P.red, 0.8),
  bench2: prototype(P.mus, 1.6),
};

export class Screens {
  private items: Array<{ ctx: CanvasRenderingContext2D; tex: CanvasTexture; w: number; h: number; draw: Draw }> = [];
  private last = -1;

  constructor(scene: Scene, disposables: Array<{ dispose(): void }>) {
    for (const id of Object.keys(SCREENS) as ScreenId[]) {
      const s = SCREENS[id];
      const [w, h] = s.px;
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d')!;
      const tex = new CanvasTexture(canvas);
      tex.colorSpace = NoColorSpace; // hex in, hex out, like everything else
      tex.magFilter = NearestFilter;
      tex.minFilter = NearestFilter;
      tex.generateMipmaps = false;
      const [bl, br, tr, tl] = s.corners.map((c) => toWorld(c));
      const geo = new BufferGeometry();
      geo.setAttribute('position', new Float32BufferAttribute([...bl.toArray(), ...br.toArray(), ...tr.toArray(), ...bl.toArray(), ...tr.toArray(), ...tl.toArray()], 3));
      geo.setAttribute('uv', new Float32BufferAttribute([0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1], 2));
      const mat = new MeshBasicMaterial({ map: tex, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
      scene.add(new Mesh(geo, mat));
      disposables.push(geo, mat, tex);
      const item = { ctx, tex, w, h, draw: DRAW[id] };
      this.items.push(item);
      item.draw(ctx, w, h, 0);
    }
  }

  /** Redraw at ~12 fps (pixel art doesn't need more). */
  update(t: number, playing = false) {
    arcadePlaying = playing;
    const tick = Math.floor(t * 12);
    if (tick === this.last) return;
    this.last = tick;
    for (const s of this.items) {
      s.draw(s.ctx, s.w, s.h, t);
      s.tex.needsUpdate = true;
    }
  }
}
