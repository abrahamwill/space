/**
 * The house as data. A 1:1 port of design/assets/house/house-art-generator.py `build()`,
 * so the 3D scene matches the 2D reference art. Change the layout here, not in components.
 *
 * Coordinates are plan units: x runs screen down-right, y runs screen down-left, z is up.
 * (In three.js world space that's X = x, Y = z, Z = y; see geometry.ts.)
 */

export type RoomId = 'studio' | 'main' | 'lab';
export type V3 = readonly [number, number, number];

/** Which way a wall faces, outward from its room: '-x' is the wall at the room's low-x side, etc. */
export type Face = '-x' | '+x' | '-y' | '+y';
export const FACE_NORMAL: Record<Face, readonly [number, number]> = { '-x': [-1, 0], '+x': [1, 0], '-y': [0, -1], '+y': [0, 1] };

export type Prim = (
  /** Box: top and four sides. Sides take `left` or `right` depending on which side of the screen they face. */
  | { t: 'box'; x: number; y: number; z: number; w: number; d: number; h: number; top: string; left: string; right: string; ol: boolean }
  /** Flat convex polygon (decals, floors, screens, ellipses). */
  | { t: 'poly'; pts: V3[]; fill: string; ol: boolean }
  /** Upright cylinder. */
  | { t: 'cyl'; cx: number; cy: number; z: number; r: number; h: number; top: string; side: string; ol: boolean }
  /** Sphere; `hi` adds the toon highlight the 2D art draws as a small inner circle. */
  | { t: 'ball'; cx: number; cy: number; z: number; r: number; fill: string; hi?: string; ol: boolean }
) & {
  /** Set on walls and anything hung on them. When the camera rotates so that wall is nearest, it's cut away. */
  face?: Face;
};

export const H = 4.2; // wall height
export const HP = 1.3; // partition height
export const T = 0.5; // wall thickness
/** The art draws heights at 2.2/2.449 of true dimetric, so the scene squashes Y to match. */
export const Z_SQUASH = (2.2 * Math.sin(Math.PI / 6) * Math.SQRT1_2) / Math.cos(Math.PI / 6); // ≈ 0.898

/** Camera: 2:1 dimetric, the same angle the 2D art uses. */
export const ELEVATION = Math.PI / 6;
export const AZIMUTH = Math.PI / 4;

export const INK = '#1a1a1a';
export const NIGHT = '#1f2433';
export const GLOW = '#f6c86a';

const P = {
  floor: '#cf9c64', plank: '#b98652', lab: '#bdb6a8', wallX: '#dccbb0', wallY: '#ece0ca', top: '#fff4e6',
  wal: '#8f4f26', walT: '#a8622f', walD: '#6f3a1a',
  oli: '#5a6330', oliT: '#717c3d', oliD: '#434a22',
  chr: '#cfcfca', chrD: '#9b9b96', red: '#c8442b', cob: '#2b4fa8', mus: '#e0a72e', pink: '#e9a3a0', char: '#3a3a3c',
  leaf: '#4f7a35', leaf2: '#86ad57', glass: '#cfe2c0', glass2: '#7fa35e', cream: '#fbf3e6', creamS: '#ece0cc', creamD: '#d4c4aa',
  chkA: '#5e5a54', chkB: '#807a70',
} as const;

export const RIM: ReadonlyArray<readonly [number, number]> = [
  [0, 0], [14, 0], [14, 9], [18, 9], [18, 4], [31, 4], [31, 20], [18, 20], [18, 28], [0, 28],
];

/** Light spilling through the doorway into a room while it's still dark. */
export const SPILL: Partial<Record<RoomId, V3[]>> = {
  studio: [[5, 9, 0], [9, 9, 0], [10.2, 5.4, 0], [3.8, 5.4, 0]],
  lab: [[18, 12, 0], [18, 16, 0], [21.8, 17.2, 0], [21.8, 10.8, 0]],
};

const shade = (hex: string, f: number) => {
  const n = parseInt(hex.slice(1), 16);
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => Math.max(0, Math.min(255, Math.round(v * f))));
  return '#' + c.map((v) => v.toString(16).padStart(2, '0')).join('');
};

// ---------- primitive helpers (same signatures as the generator) ----------
const box = (x: number, y: number, z: number, w: number, d: number, h: number, top: string, left: string, right: string, ol = true): Prim =>
  ({ t: 'box', x, y, z, w, d, h, top, left, right, ol });
const q = (pts: V3[], fill: string, ol = true): Prim => ({ t: 'poly', pts, fill, ol });
const circlePts = (n: number, f: (a: number) => V3) => Array.from({ length: n }, (_, i) => f((i * 2 * Math.PI) / n));
const ell = (cx: number, cy: number, z: number, rx: number, ry: number, fill: string, ol = true) =>
  q(circlePts(32, (a) => [cx + rx * Math.cos(a), cy + ry * Math.sin(a), z]), fill, ol);
const cyl = (cx: number, cy: number, z: number, r: number, h: number, top: string, side: string, ol = true): Prim =>
  ({ t: 'cyl', cx, cy, z, r, h, top, side, ol });
const blob = (cx: number, cy: number, z: number, r: number, fill: string, hi: string): Prim =>
  ({ t: 'ball', cx, cy, z, r, fill, hi, ol: true });
const tube = (x: number, y: number, z: number, w: number, d: number, h: number) => box(x, y, z, w, d, h, P.chr, P.chr, P.chrD);
const decoX = (X: number, y0: number, y1: number, z0: number, z1: number, fill: string, ol = true) =>
  q([[X + 0.01, y0, z0], [X + 0.01, y1, z0], [X + 0.01, y1, z1], [X + 0.01, y0, z1]], fill, ol);
const decoY = (Y: number, x0: number, x1: number, z0: number, z1: number, fill: string, ol = true) =>
  q([[x0, Y + 0.01, z0], [x1, Y + 0.01, z0], [x1, Y + 0.01, z1], [x0, Y + 0.01, z1]], fill, ol);
/** Walls are single quads on the plan outline. Near walls are cut away (see engine.ts). */
const wallX = (X: number, y0: number, y1: number) => q([[X, y0, 0], [X, y1, 0], [X, y1, H], [X, y0, H]], P.wallX);
const wallY = (Y: number, x0: number, x1: number) => q([[x0, Y, 0], [x1, Y, 0], [x1, Y, H], [x0, Y, H]], P.wallY);
const partY = (Y: number, x0: number, x1: number, gap: [number, number]) =>
  [[x0, gap[0]], [gap[1], x1]].filter(([a, b]) => b > a).map(([a, b]) => box(a, Y - T, 0, b - a, T, HP, P.top, P.wallY, P.wallY));
const partX = (X: number, y0: number, y1: number, gap: [number, number]) =>
  [[y0, gap[0]], [gap[1], y1]].filter(([a, b]) => b > a).map(([a, b]) => box(X - T, a, 0, T, b - a, HP, P.top, P.wallX, P.wallX));
/** Tag prims as belonging to the wall facing `face`. */
const on = (face: Face, ...prims: Prim[]): Prim[] => prims.map((p) => ({ ...p, face }));
const floorRect = (x0: number, y0: number, x1: number, y1: number, color: string, z = 0, ol = true) =>
  q([[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]], color, ol);
const oakFloor = (x0: number, y0: number, x1: number, y1: number) => {
  const out: Prim[] = [floorRect(x0, y0, x1, y1, P.floor)];
  for (let x = x0 + 1.1; x < x1; x += 1.1) out.push(floorRect(x, y0, x + 0.06, y1, P.plank, 0.005, false));
  return out;
};
const fiddle = (cx: number, cy: number): Prim[] => [
  cyl(cx, cy, 0, 0.55, 0.9, P.char, '#2a2a2c'),
  box(cx - 0.06, cy - 0.06, 0.9, 0.12, 0.12, 2.6, P.walD, P.walD, P.walD),
  ...([[0.35, 0.1, 1.9, 0.5], [-0.3, 0.25, 2.4, 0.55], [0.25, -0.3, 2.9, 0.5], [-0.15, 0.1, 3.35, 0.48], [0.2, 0.25, 3.7, 0.38]] as const)
    .map(([dx, dy, dz, r]) => blob(cx + dx, cy + dy, dz, r, P.leaf, P.leaf2)),
];
const person = (x: number, y: number): Prim[] => [
  box(x, y, 0, 0.8, 0.8, 1.6, P.char, P.char, '#262628'),
  box(x - 0.18, y - 0.18, 1.6, 1.16, 1.16, 1.3, P.mus, P.mus, '#b8861f'),
  box(x - 0.04, y - 0.04, 2.9, 0.88, 0.88, 0.8, '#e9b48a', '#e9b48a', '#cf9670'),
  box(x - 0.1, y - 0.1, 3.55, 1.08, 1.08, 0.32, INK, INK, INK),
];

/**
 * The 2D art paints the pet's eyes on top of its body. In 3D they'd sit inside the sphere,
 * so slide each one along the view direction until it sits on the surface facing the camera.
 */
function eyeOn(c: V3, r: number, o: V3, er: number): Prim {
  const S = Z_SQUASH;
  const v = [Math.cos(ELEVATION) * Math.sin(AZIMUTH), Math.sin(ELEVATION), Math.cos(ELEVATION) * Math.cos(AZIMUTH)]; // world
  const ow = [o[0], o[2] * S, o[1]];
  const ov = ow[0] * v[0] + ow[1] * v[1] + ow[2] * v[2];
  const oo = ow[0] ** 2 + ow[1] ** 2 + ow[2] ** 2;
  const t = -ov + Math.sqrt(ov * ov - (oo - r * r));
  const e = [ow[0] + t * v[0], ow[1] + t * v[1], ow[2] + t * v[2]];
  // A ball's centre sits at world y = z * S, so convert the world offset back to plan z.
  return { t: 'ball', cx: c[0] + e[0], cy: c[1] + e[2], z: c[2] + e[1] / S, r: er, fill: INK, ol: false };
}

// ---------- anchors: hotspot positions in plan units ----------
export const ANCHORS = {
  archive: [4.7, 1.0, 3.4], pinboard: [0, 4.9, 3.3], folders: [7.0, 5.0, 2.3],
  lbl_studio: [11.6, 7.4, 0], c_studio: [5.0, 4.4, 1.0],
  window: [0, 13.8, 3.4], notice: [0, 21.9, 3.5], door: [0, 25.1, 3.3], photos: [16.0, 9, 3.8],
  turntable: [1.5, 18.2, 2.6], coatrack: [2.7, 22.8, 3.4], me: [6.4, 19.8, 3.9],
  lbl_main: [9.6, 22.4, 0],
  // camera centre for the main room view: nudged toward the door wall so the door and prints stay on screen
  c_main: [6.5, 19.0, 1.0],
  whiteboard: [23.5, 4, 3.6], prototypehub: [23.2, 5.3, 3.1], arcade: [19.6, 7.6, 3.9], voice: [22.8, 10.4, 2.7], pet: [24.4, 12.9, 2.1],
  lbl_lab: [21.6, 15.0, 0], c_lab: [23.0, 9.4, 1.0],
} as const satisfies Record<string, V3>;
export type AnchorId = keyof typeof ANCHORS;

export function buildHouse(): Record<RoomId, Prim[]> {
  const studio: Prim[] = [];
  const main: Prim[] = [];
  const lab: Prim[] = [];

  // ---------- floors ----------
  main.push(...oakFloor(0, 9, 18, 28));
  studio.push(...oakFloor(0, 0, 14, 9));
  lab.push(floorRect(18, 4, 31, 20, P.lab));

  // ================= STUDIO =================
  studio.push(...on('-y', wallY(0, 0, 14)), ...on('-x', wallX(0, 0, 9)), ...on('+x', wallX(14, 0, 9)));
  studio.push(...on('-y', decoY(0, 0.4, 9.6, 0, 4.2, P.wal, false)));
  for (const zs of [2.3, 3.2]) studio.push(...on('-y', box(1.0, 0, zs, 7.6, 0.55, 0.12, P.cream, P.creamS, P.creamD)));
  studio.push(...on('-y',
    box(1.4, 0.05, 2.42, 0.5, 0.4, 0.55, P.oliT, P.oli, P.oliD), cyl(3.1, 0.3, 2.42, 0.22, 0.5, P.cream, P.creamS),
    box(4.6, 0.05, 2.42, 1.2, 0.4, 0.3, P.red, P.red, '#a3361f'), box(6.6, 0.05, 3.32, 0.9, 0.4, 0.55, P.cob, P.cob, '#1f3b80'),
    cyl(2.2, 0.3, 3.32, 0.25, 0.55, P.mus, '#b8861f'),
  ));
  studio.push(box(0.5, 0.2, 0, 8.6, 1.4, 1.5, P.walT, P.wal, P.walD));
  {
    const cols = [P.cream, P.char, P.red, P.creamS, P.cob, P.mus, P.oliT];
    for (let bx = 0.7, k = 0; bx < 8.8; bx += 0.38, k++)
      studio.push(q([[bx, 1.61, 0.2], [bx + 0.3, 1.61, 0.2], [bx + 0.3, 1.61, 1.25], [bx, 1.61, 1.25]], cols[k % 7]));
  }
  studio.push(...on('-x', decoX(0, 2.4, 7.4, 1.5, 3.7, '#d9a066')));
  for (const [a, b, z0, c] of [[2.8, 4.0, 2.6, P.mus], [4.4, 5.6, 2.8, P.pink], [6.0, 7.1, 2.5, P.cream], [3.2, 4.5, 1.7, P.cream], [5.3, 6.6, 1.75, P.mus]] as const)
    studio.push(...on('-x', decoX(0.02, a, b, z0, z0 + 0.75, c)));
  // walnut desk on chrome legs, cream monitor, folders, blue mushroom lamp
  for (const [lx, ly] of [[3.4, 3.5], [8.6, 3.5], [3.4, 5.8], [8.6, 5.8]]) studio.push(tube(lx, ly, 0, 0.16, 0.16, 1.6));
  studio.push(
    box(3.2, 3.3, 1.6, 5.9, 2.9, 0.22, P.walT, P.wal, P.walD),
    box(3.6, 3.5, 1.82, 2.1, 0.55, 1.45, P.cream, P.creamS, P.creamD),
    q([[3.75, 4.06, 1.98], [5.55, 4.06, 1.98], [5.55, 4.06, 3.12], [3.75, 4.06, 3.12]], P.char),
    q([[3.95, 4.07, 2.6], [4.9, 4.07, 2.6], [4.9, 4.07, 2.9], [3.95, 4.07, 2.9]], P.mus, false),
  );
  [P.red, P.cob, P.mus].forEach((c, i) => studio.push(box(5.9 + i * 0.3, 4.2 + i * 0.42, 1.82 + i * 0.12, 2.0, 1.35, 0.12, c, c, shade(c, 0.8))));
  studio.push(box(8.3, 3.6, 1.82, 0.14, 0.14, 0.7, P.chr, P.chr, P.chrD), blob(8.37, 3.67, 2.65, 0.42, '#6fa3d8', '#b9d6f0'));
  // cantilever tube chair with cane seat
  studio.push(
    tube(5.3, 6.8, 0, 0.14, 1.3, 0.14), tube(5.3, 6.8, 0, 0.14, 0.14, 1.0), tube(6.6, 6.8, 0, 0.14, 1.3, 0.14), tube(6.6, 6.8, 0, 0.14, 0.14, 1.0),
    box(5.3, 6.8, 1.0, 1.44, 1.3, 0.14, '#d9b47a', '#c49c60', '#a8844c'), box(5.3, 7.95, 1.14, 1.44, 0.15, 1.1, '#d9b47a', '#c49c60', '#a8844c'),
  );

  // ================= MAIN ROOM =================
  main.push(floorRect(5.25, 12.45, 12.35, 19.15, P.chkA, 0.015));
  for (let i = 0; i < 4; i++)
    for (let j = 0; j < 4; j++) {
      const x0 = 5.4 + i * 1.7, y0 = 12.6 + j * 1.6;
      main.push(floorRect(x0, y0, x0 + 1.7, y0 + 1.6, (i + j) % 2 === 0 ? P.chkA : P.chkB, 0.02, false));
    }
  main.push(floorRect(6.0, 19.6, 8.4, 21.0, P.red, 0.03), floorRect(6.3, 19.85, 8.1, 20.75, P.mus, 0.04, false));
  main.push(...on('-x', wallX(0, 9, 28)), ...on('-y', wallY(9, 14, 18)), ...on('+x', wallX(18, 20, 28)), ...on('+y', wallY(28, 0, 18)));
  main.push(...partY(9, 0, 14, [5, 9]));
  // big black-framed window onto a garden, low walnut bookshelf beneath it
  // (decoX adds 0.01 to x; the leaves sit at 0.03 so they're in front of the glass at 0.02)
  main.push(...on('-x',
    decoX(0, 10.8, 16.6, 1.1, 3.95, P.char), decoX(0.01, 11.0, 16.4, 1.25, 3.8, P.glass), decoX(0.015, 11.0, 16.4, 1.25, 2.3, P.glass2, false),
    q(circlePts(20, (a) => [0.03, 12.0 + 1.0 * Math.cos(a), 2.5 + 0.9 * Math.sin(a)]), P.leaf, false),
    q(circlePts(20, (a) => [0.03, 14.8 + 1.1 * Math.cos(a), 2.7 + 0.85 * Math.sin(a)]), P.leaf, false),
    decoX(0.03, 12.75, 12.85, 1.25, 3.8, P.char, false), decoX(0.03, 14.55, 14.65, 1.25, 3.8, P.char, false),
  ));
  main.push(box(0.2, 11.0, 0, 1.2, 5.4, 1.05, P.walT, P.wal, P.walD));
  {
    const cols = [P.cream, P.red, P.char, P.cob, P.creamS, P.mus, P.oliT];
    for (let by = 11.2, k = 0; by < 16.2; by += 0.36, k++)
      main.push(q([[1.41, by, 0.15], [1.41, by + 0.28, 0.15], [1.41, by + 0.28, 0.9], [1.41, by, 0.9]], cols[k % 7]));
  }
  // framed Bauhaus prints (talks & workshops) + walnut front door
  main.push(...on('-x',
    decoX(0, 20.5, 22.0, 1.7, 3.6, P.walT), decoX(0.01, 20.7, 21.8, 1.9, 3.4, P.cream),
    q(circlePts(20, (a) => [0.03, 21.25 + 0.4 * Math.cos(a), 2.85 + 0.4 * Math.sin(a)]), P.red, false),
    decoX(0.02, 20.9, 21.6, 2.0, 2.2, P.cob, false),
    decoX(0, 22.2, 23.4, 2.0, 3.4, P.walT), decoX(0.01, 22.35, 23.25, 2.15, 3.25, P.mus),
    decoX(0, 23.8, 26.4, 0, 3.3, P.walD), decoX(0.02, 24.1, 26.1, 0.25, 3.05, P.wal), decoX(0.03, 25.7, 25.9, 1.5, 1.8, P.chr, false),
  ));
  // walnut panel + floating record shelves on the short back wall
  main.push(...on('-y', decoY(9, 14.0, 18.0, 0, 4.2, P.wal, false)));
  for (const zs of [1.9, 3.0]) main.push(...on('-y', box(14.2, 9.0, zs, 3.6, 0.45, 0.1, P.walT, P.walT, P.walD)));
  for (const [x0, zs, c, disc] of [[14.4, 2.0, P.red, true], [15.6, 2.0, P.char, true], [16.8, 2.0, P.mus, false], [14.8, 3.1, P.cob, true], [16.2, 3.1, P.pink, false]] as const) {
    main.push(...on('-y', q([[x0, 9.42, zs], [x0 + 0.85, 9.42, zs], [x0 + 0.85, 9.42, zs + 0.85], [x0, 9.42, zs + 0.85]], c)));
    if (disc) main.push(...on('-y', q(circlePts(16, (a) => [x0 + 0.42 + 0.3 * Math.cos(a), 9.43, zs + 0.42 + 0.3 * Math.sin(a)]), INK, false)));
  }
  main.push(...fiddle(1.0, 10.0));
  // long low walnut media console with the turntable, red mushroom lamp
  main.push(
    box(0.2, 16.9, 0, 1.9, 4.6, 1.2, P.walT, P.wal, P.walD),
    q([[2.11, 17.2, 0.2], [2.11, 19.0, 0.2], [2.11, 19.0, 1.0], [2.11, 17.2, 1.0]], P.walD),
    q([[2.11, 19.3, 0.2], [2.11, 21.2, 0.2], [2.11, 21.2, 1.0], [2.11, 19.3, 1.0]], '#4a4440'),
    box(0.45, 17.3, 1.2, 1.5, 1.9, 0.25, P.char, '#2a2a2c', '#1e1e20'),
    ell(1.2, 18.2, 1.46, 0.6, 0.6, INK), ell(1.2, 18.2, 1.47, 0.2, 0.2, P.red, false),
    box(1.6, 18.9, 1.45, 0.14, 0.14, 0.5, P.chr, P.chr, P.chrD),
    cyl(1.1, 20.6, 1.2, 0.1, 0.5, P.red, P.red), blob(1.1, 20.6, 1.85, 0.38, P.red, '#e57a5e'),
  );
  // round walnut coffee table, pink vase, book
  main.push(
    cyl(8.8, 15.8, 0, 0.35, 0.9, P.char, '#2a2a2c'), cyl(8.8, 15.8, 0.9, 1.5, 0.2, P.walT, P.wal),
    cyl(8.4, 15.5, 1.1, 0.22, 0.45, P.pink, '#cf8784'), box(8.9, 15.7, 1.1, 0.9, 0.7, 0.14, P.cob, P.cob, '#1f3b80'),
  );
  // low olive lounge sofa with a knot pillow and a throw
  main.push(
    box(11.8, 12.2, 0, 1.9, 6.6, 0.9, P.oliT, P.oli, P.oliD), box(12.9, 12.2, 0.9, 0.8, 6.6, 0.9, P.oliT, P.oli, P.oliD),
    box(11.8, 11.7, 0, 1.9, 0.55, 1.3, P.oliT, P.oli, P.oliD), box(11.8, 18.8, 0, 1.9, 0.55, 1.3, P.oliT, P.oli, P.oliD),
    box(11.95, 13.2, 0.9, 0.9, 1.6, 0.06, P.mus, P.mus, '#b8861f'), box(11.95, 13.75, 0.96, 0.9, 0.3, 0.02, P.cob, P.cob, P.cob),
  );
  // swivel lounge chair on a chrome star base
  main.push(
    cyl(5.0, 11.7, 0, 0.7, 0.08, P.chr, P.chrD), cyl(5.0, 11.7, 0.08, 0.1, 0.5, P.chr, P.chrD),
    box(4.2, 10.9, 0.58, 1.6, 1.6, 0.5, '#a3a36a', '#8f8f58', '#767646'), box(4.2, 10.9, 1.08, 0.45, 1.6, 0.9, '#a3a36a', '#8f8f58', '#767646'),
  );
  // chrome globe floor lamp by the record wall
  main.push(tube(16.33, 10.33, 0, 0.14, 0.14, 2.9), cyl(16.4, 10.4, 0, 0.45, 0.08, P.chr, P.chrD), blob(16.4, 10.4, 3.25, 0.5, P.cream, '#ffffff'));
  // chrome coat rack by the door
  main.push(
    tube(2.6, 22.6, 0, 0.14, 0.14, 3.3), cyl(2.67, 22.67, 0, 0.6, 0.07, P.chr, P.chrD),
    tube(2.2, 22.62, 2.95, 0.95, 0.1, 0.1), box(2.05, 22.85, 1.9, 0.75, 0.5, 1.05, P.red, P.red, '#a3361f'),
  );
  main.push(...person(6.0, 19.4));

  // ================= LAB =================
  lab.push(...on('-y', wallY(4, 18, 31)), ...on('-x', wallX(18, 4, 9)), ...on('+x', wallX(31, 4, 20)), ...on('+y', wallY(20, 18, 31)));
  lab.push(...partX(18, 9, 20, [12, 20]));
  lab.push(...on('-y',
    q(circlePts(28, (a) => [26.9 + 1.05 * Math.cos(a), 4.02, 2.75 + 1.05 * Math.sin(a)]), P.cob, false),
    decoY(4, 21.2, 25.8, 1.7, 3.9, P.cream),
  ));
  for (const [a, b, z0, z1, c] of [[21.6, 23.2, 3.25, 3.65, P.cob], [23.5, 25.4, 3.4, 3.6, P.red], [21.6, 23.8, 2.4, 2.6, INK], [24.1, 24.8, 2.2, 3.0, P.mus], [25.0, 25.5, 2.2, 3.0, P.pink]] as const)
    lab.push(...on('-y', decoY(4.02, a, b, z0, z1, c, false)));
  for (const [lx, ly] of [[21.2, 4.5], [25.8, 4.5], [21.2, 6.3], [25.8, 6.3]]) lab.push(tube(lx, ly, 0, 0.16, 0.16, 1.6));
  lab.push(box(21.0, 4.3, 1.6, 5.2, 2.3, 0.22, P.cream, P.creamS, P.creamD));
  [P.cob, P.red, P.mus].forEach((c, i) => {
    lab.push(box(21.6 + i * 1.35, 5.1, 1.82, 0.85, 0.22, 1.3, INK, INK, INK));
    lab.push(q([[21.7 + i * 1.35, 5.33, 1.94], [22.35 + i * 1.35, 5.33, 1.94], [22.35 + i * 1.35, 5.33, 3.0], [21.7 + i * 1.35, 5.33, 3.0]], c, false));
  });
  // arcade in Bauhaus red with a mustard control deck
  lab.push(
    box(18.3, 6.4, 0, 2.4, 2.4, 3.8, P.red, P.red, '#a3361f'),
    q([[20.71, 6.65, 2.2], [20.71, 8.55, 2.2], [20.71, 8.55, 3.4], [20.71, 6.65, 3.4]], INK),
    q([[20.72, 6.85, 2.35], [20.72, 8.35, 2.35], [20.72, 8.35, 3.25], [20.72, 6.85, 3.25]], P.leaf2, false),
    box(20.7, 6.4, 1.6, 0.8, 2.4, 0.3, P.mus, P.mus, '#b8861f'),
  );
  // voice gadget on a chrome side table
  lab.push(
    tube(22.15, 9.75, 0, 0.14, 0.14, 1.5), tube(23.3, 9.75, 0, 0.14, 0.14, 1.5), tube(22.15, 10.9, 0, 0.14, 0.14, 1.5), tube(23.3, 10.9, 0, 0.14, 0.14, 1.5),
    box(22.0, 9.6, 1.5, 1.6, 1.6, 0.12, P.char, '#2a2a2c', '#1e1e20'),
    cyl(22.8, 10.4, 1.62, 0.45, 0.8, P.cream, P.creamS),
    ell(22.8, 10.4, 2.43, 0.45, 0.45, P.cob, false), ell(22.8, 10.4, 2.44, 0.24, 0.24, '#b9d6f0', false),
  );
  // pet on its bed, and a bowl
  lab.push(
    ell(24.4, 12.9, 0.04, 1.6, 1.3, P.mus), ell(24.4, 12.9, 0.3, 1.2, 0.95, '#f0c96a'),
    { t: 'ball', cx: 24.4, cy: 12.9, z: 1.0, r: 0.78, fill: P.cream, ol: true },
    box(23.9, 12.45, 1.5, 0.26, 0.26, 0.6, P.cream, P.cream, P.creamD), box(24.65, 12.1, 1.5, 0.26, 0.26, 0.6, P.cream, P.cream, P.creamD),
    eyeOn([24.4, 12.9, 1.0], 0.78, [0.2, 0.2, 0.05], 0.1),
    eyeOn([24.4, 12.9, 1.0], 0.78, [0.5, -0.1, 0.05], 0.1),
    cyl(22.4, 13.8, 0, 0.42, 0.3, P.cob, '#1f3b80'),
  );
  lab.push(...fiddle(25.6, 8.6));

  return { studio, main, lab };
}

/** `zoom` is relative to the whole-house view. The main room is big, so it zooms less. */
export const ROOMS: Record<RoomId, { label: string; centre: AnchorId; labelAnchor: AnchorId; zoom: number }> = {
  main: { label: 'Main room', centre: 'c_main', labelAnchor: 'lbl_main', zoom: 1.15 },
  studio: { label: 'Studio', centre: 'c_studio', labelAnchor: 'lbl_studio', zoom: 2.1 },
  lab: { label: 'Lab', centre: 'c_lab', labelAnchor: 'lbl_lab', zoom: 2.1 },
};
