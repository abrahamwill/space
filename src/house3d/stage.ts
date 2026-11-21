/**
 * The camera for the full house view (/house), on top of viewer.ts in control mode.
 *
 * Camera: orthographic at the HeroCamera's angle (read from the GLB, so it stays in step with Blender).
 * The frustum is the canvas in px, so `zoom` is px per metre. Views:
 *   - overview, default angle: framed exactly like the poster (src/assets/house/hero-p2.png), so the
 *     3D fades in over the still without a jump;
 *   - overview, turned: the whole house fitted in the free space;
 *   - a room: zoomed in on the room's centre, centred in the space the HUD and the window leave.
 * Turning goes in quarter turns (`rot`), plus a small drag tilt.
 *
 * The house stays sunk into the page at every angle: the page surface (the holdout) is always on, and
 * once turned, viewer.ts's cut_walls line the whole cut, so whichever side is far there is a wall, and
 * the near side's walls hide under the page's edge like the front ones do in the hero. (At the hero
 * angle they're off, so the view matches the poster exactly.) Hotspots hung on a perimeter wall that
 * faces the camera are hidden (their wall's art faces away).
 */
import * as THREE from 'three';
import type { HouseView } from './viewer';
import { ROOMS, HOTSPOTS, onFootprint, inRect, roomAt, type RoomId, type Anchor } from './rooms';

export type Face = '-x' | '+x' | '-z' | '+z';
const NORMAL: Record<Face, readonly [number, number]> = { '-x': [-1, 0], '+x': [1, 0], '-z': [0, -1], '+z': [0, 1] };

export interface Insets { top: number; right: number; bottom: number; left: number }

/**
 * The poster is the HeroCamera frame cropped to the house. These are the crop's margins as a fraction
 * of the poster (the same numbers as .house-live in src/pages/index.astro, printed by
 * scripts/render-house3d-poster.mjs).
 */
export const POSTER = { w: 3320, h: 1793, top: 0.25098, right: 0.01807, bottom: 0.22142, left: 0.01807 };

/** Where the poster sits: contained and centred in the viewport minus insets. Same as the CSS on /house. */
export function posterRect(w: number, h: number, ins: Insets) {
  const aw = Math.max(1, w - ins.left - ins.right), ah = Math.max(1, h - ins.top - ins.bottom);
  const a = POSTER.w / POSTER.h;
  const pw = Math.min(aw, ah * a), ph = pw / a;
  return { left: ins.left + (aw - pw) / 2, top: ins.top + (ah - ph) / 2, width: pw, height: ph };
}

const MOVE_RATE = 6; // camera easing, 1/s

interface Pose { target: THREE.Vector3; zoom: number; az: number }

/** Insets for a canvas size: the space the HUD (and the open window) take up. */
export type InsetsFn = (w: number, h: number) => Insets;

export type Goal =
  | { kind: 'overview'; rot: number; tilt: number; insets: InsetsFn; phoneRoom?: RoomId }
  | { kind: 'room'; room: RoomId; rot: number; tilt: number; insets: InsetsFn; overviewInsets: InsetsFn };

export class Stage {
  view: HouseView | null = null;
  /** World positions for pins (hotspot ids, 'me', 'room:<id>'). Filled when the house loads. */
  readonly anchors = new Map<string, THREE.Vector3>();
  /** Which perimeter wall a hotspot hangs on (hidden when that wall is cut). */
  readonly walls = new Map<string, Face>();
  ready = false;
  onReady: (() => void) | null = null;
  /** Called after each frame with the camera and canvas size (pins). */
  onFrame: ((cam: THREE.OrthographicCamera, w: number, h: number) => void) | null = null;

  private w = 1;
  private h = 1;
  private el = 0; // elevation (rad)
  private az0 = 0; // hero azimuth (rad)
  private posterCentre = new THREE.Vector3();
  private posterWidth = 1; // m
  private corners: THREE.Vector3[] = [];
  private pose: Pose | null = null;
  private goal: Goal | null = null;
  private instant = false;
  private page: THREE.Object3D[] = [];
  private cutWalls: THREE.Object3D | null = null;
  private pageGrid: THREE.Object3D | null = null;
  private pickable: THREE.Object3D[] = [];

  constructor() {
    // created up front so pins can track them before the house loads (they sit off-screen until then)
    for (const h of HOTSPOTS) this.anchors.set(h.id, new THREE.Vector3(0, -999, 0));
    for (const r of Object.keys(ROOMS)) this.anchors.set(`room:${r}`, new THREE.Vector3(0, -999, 0));
    this.anchors.set('me', new THREE.Vector3(0, -999, 0));
  }

  attach(view: HouseView) {
    this.view = view;
    view.step = (dt) => this.step(dt);
    view.onFrame = () => this.frame();
  }

  setInstant(on: boolean) {
    this.instant = on;
  }

  /** Move the camera to a view (eased unless `jump` or reduced motion). */
  go(goal: Goal, jump = false) {
    this.goal = goal;
    if (!this.init()) return;
    if (jump) this.pose = this.solve(goal);
    this.view!.kick();
  }

  resize(w: number, h: number) {
    this.w = w;
    this.h = h;
    if (!this.init() || !this.goal) return;
    this.pose = this.solve(this.goal); // a resize jumps straight to the new framing
    this.apply();
  }

  /** The room under a canvas point (px from the canvas's top-left), or null. */
  roomAt(x: number, y: number): RoomId | null {
    const cam = this.view?.camera();
    if (!cam) return null;
    const ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2((x / this.w) * 2 - 1, -(y / this.h) * 2 + 1), cam);
    for (const hit of ray.intersectObjects(this.pickable, false)) {
      if (!shown(hit.object)) continue;
      const m = hit.object as THREE.Mesh;
      if (this.page.some((p) => p === m || p === m.parent)) return null; // the page around the house
      return roomAt(hit.point.x, hit.point.z);
    }
    return null;
  }

  /** Does this perimeter wall face away from the camera (its art visible) at quarter turn `rot`? */
  wallShown(face: Face | undefined, rot: number) {
    if (!face || !this.ready) return true;
    return !this.facing(face, this.az0 + (rot * Math.PI) / 2);
  }

  // ---------------------------------------------------------------------------------------------

  private facing(face: Face, az: number) {
    const [nx, nz] = NORMAL[face];
    return nx * Math.sin(az) + nz * Math.cos(az) > 0.2;
  }

  private basis(az: number) {
    const ce = Math.cos(this.el), se = Math.sin(this.el);
    return {
      d: new THREE.Vector3(ce * Math.sin(az), se, ce * Math.cos(az)), // toward the camera
      r: new THREE.Vector3(Math.cos(az), 0, -Math.sin(az)), // screen right
      u: new THREE.Vector3(-se * Math.sin(az), ce, -se * Math.cos(az)), // screen up
    };
  }

  /** Camera target that puts world point `p` at canvas px (sx, sy). */
  private place(p: THREE.Vector3, sx: number, sy: number, zoom: number, az: number) {
    const { r, u } = this.basis(az);
    return p.clone().addScaledVector(r, -(sx - this.w / 2) / zoom).addScaledVector(u, (sy - this.h / 2) / zoom);
  }

  private posterZoom(ins: Insets) {
    return posterRect(this.w, this.h, ins).width / this.posterWidth;
  }

  private solve(g: Goal): Pose {
    const az = this.az0 + (g.rot * Math.PI) / 2 + g.tilt;
    const ins = g.insets(this.w, this.h);
    const free = (ins: Insets) => ({ x: ins.left + (this.w - ins.left - ins.right) / 2, y: ins.top + (this.h - ins.top - ins.bottom) / 2 });
    if (g.kind === 'room' || g.phoneRoom) {
      const room = g.kind === 'room' ? g.room : g.phoneRoom!;
      const R = ROOMS[room];
      const zoom = this.posterZoom(g.kind === 'room' ? g.overviewInsets(this.w, this.h) : ins) * (g.kind === 'room' ? R.zoom : 2);
      const c = R.focus ? new THREE.Vector3(...R.focus) : new THREE.Vector3(R.rect[0] + R.rect[2] / 2, 0.5, R.rect[1] + R.rect[3] / 2);
      const f = free(ins);
      return { target: this.place(c, f.x, f.y, zoom, az), zoom, az };
    }
    const quarter = ((g.rot % 4) + 4) % 4;
    const pz = this.posterZoom(ins);
    if (quarter === 0) {
      // the poster's own framing (tilt turns the house around the poster's centre)
      const p = posterRect(this.w, this.h, ins);
      return { target: this.place(this.posterCentre, p.left + p.width / 2, p.top + p.height / 2, pz, az), zoom: pz, az };
    }
    const { r, u } = this.basis(az);
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const c of this.corners) {
      const sx = c.dot(r), sy = c.dot(u);
      x0 = Math.min(x0, sx); x1 = Math.max(x1, sx); y0 = Math.min(y0, sy); y1 = Math.max(y1, sy);
    }
    const aw = this.w - ins.left - ins.right, ah = this.h - ins.top - ins.bottom;
    const zoom = Math.min(pz, aw / (x1 - x0), ah / (y1 - y0));
    const centre = r.clone().multiplyScalar((x0 + x1) / 2).addScaledVector(u, (y0 + y1) / 2);
    const f = free(ins);
    return { target: this.place(centre, f.x, f.y, zoom, az), zoom, az };
  }

  private step(dt: number): boolean {
    if (!this.init() || !this.goal) return false;
    const goal = this.solve(this.goal);
    if (!this.pose || this.instant) this.pose = goal;
    const p = this.pose;
    const k = 1 - Math.exp(-MOVE_RATE * dt);
    p.target.lerp(goal.target, k);
    p.zoom += (goal.zoom - p.zoom) * k;
    p.az += (goal.az - p.az) * k;
    const done = p.target.distanceTo(goal.target) * goal.zoom < 0.3 && Math.abs(goal.zoom / p.zoom - 1) < 0.002 && Math.abs(goal.az - p.az) < 0.002;
    if (done) this.pose = goal;
    this.apply();
    return !done;
  }

  private apply() {
    const cam = this.view?.camera();
    if (!cam || !this.pose) return;
    const { target, zoom, az } = this.pose;
    const { d } = this.basis(az);
    cam.position.copy(target).addScaledVector(d, 60);
    cam.up.set(0, 1, 0);
    cam.lookAt(target);
    cam.zoom = zoom;
    cam.near = 0.1;
    cam.far = 200;
    cam.updateProjectionMatrix();
    cam.updateMatrixWorld();
    // Turned: the cut's own walls on, and the page 1 cm higher, clear of the wall tops that sit just
    // under it (seen from the far side they flicker through it as dots). At the hero angle neither, so
    // the view matches the poster exactly.
    const quarters = (az - this.az0) / (Math.PI / 2);
    const turned = Math.abs(quarters - Math.round(quarters)) > 0.05 || Math.round(quarters) % 4 !== 0;
    if (this.cutWalls) this.cutWalls.visible = turned;
    if (this.pageGrid) this.pageGrid.position.y = turned ? 0.01 : 0;
  }

  private frame() {
    const cam = this.view?.camera();
    if (!cam || !this.ready) return;
    this.view!.headAt(this.anchors.get('me')!);
    const me = this.anchors.get('window');
    if (me) me.copy(this.anchors.get('me')!).y -= 0.95;
    this.onFrame?.(cam, this.w, this.h);
  }

  /** Once the house is in: read the hero camera, place the anchors. */
  private init(): boolean {
    if (this.ready) return true;
    const view = this.view, cam = view?.camera(), house = view?.house();
    if (!view || !cam || !house) return false;
    house.updateMatrixWorld(true);

    // hero angle and the poster's place in it
    const toCam = cam.getWorldDirection(new THREE.Vector3()).negate();
    this.el = Math.asin(toCam.y);
    this.az0 = Math.atan2(toCam.x, toCam.z);
    const { x: xmag, y: ymag } = view.heroFrame();
    const fw = 2 * xmag, fh = 2 * ymag;
    this.posterWidth = fw / (1 + POSTER.left + POSTER.right);
    const cyFromTop = (POSTER.top + 0.5) / (1 + POSTER.top + POSTER.bottom);
    const cxFromLeft = (POSTER.left + 0.5) / (1 + POSTER.left + POSTER.right);
    const { r, u } = this.basis(this.az0);
    const box = new THREE.Box3();

    const meshes: THREE.Mesh[] = [];
    house.traverse((o) => { if ((o as THREE.Mesh).isMesh) meshes.push(o as THREE.Mesh); });
    for (const m of meshes) {
      const isPage = m.name.startsWith('page_surface') || m.parent?.name === 'page_surface';
      if (isPage) {
        this.page.push(m);
        this.pickable.push(m);
        if (m.name === 'page_surface_grid') this.pageGrid = m;
        continue;
      }
      this.pickable.push(m);
      if (m.name === 'cut_walls') { this.cutWalls = m; continue; } // not part of the poster's framing
      if (m.name === 'character_abraham' || m.parent?.name === 'character_abraham') continue;
      box.setFromObject(m);
      for (let i = 0; i < 8; i++) this.corners.push(new THREE.Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z));
    }
    const centre = new THREE.Box3().setFromPoints(this.corners).getCenter(new THREE.Vector3());
    const camPos = cam.getWorldPosition(new THREE.Vector3());
    const axisPoint = camPos.clone().addScaledVector(toCam, -centre.clone().sub(camPos).dot(toCam.clone().negate()));
    this.posterCentre.copy(axisPoint).addScaledVector(r, fw * (cxFromLeft - 0.5)).addScaledVector(u, fh * (0.5 - cyFromTop));

    // anchors
    for (const h of HOTSPOTS) {
      const a = this.anchorFor(house, h.anchor);
      if (!a) {
        console.warn(`house: no anchor for hotspot "${h.id}"`, h.anchor);
        continue;
      }
      this.anchors.get(h.id)!.copy(a.at);
      if (a.face) this.walls.set(h.id, a.face);
    }
    for (const [id, R] of Object.entries(ROOMS)) this.anchors.get(`room:${id}`)!.set(R.rect[0] + R.rect[2] / 2, 1.9, R.rect[1] + R.rect[3] / 2);

    this.ready = true;
    this.onReady?.();
    return true;
  }

  private anchorFor(house: THREE.Object3D, a: Anchor): { at: THREE.Vector3; face?: Face } | null {
    if ('me' in a) return { at: new THREE.Vector3() };
    if ('point' in a) return { at: new THREE.Vector3(...a.point), face: a.wall };
    if ('object' in a) {
      const o = house.getObjectByName(a.object);
      if (!o) return null;
      const b = new THREE.Box3().setFromObject(o);
      const c = b.getCenter(new THREE.Vector3());
      return { at: new THREE.Vector3(c.x, b.max.y + 0.05 - (a.drop ?? 0), c.z), face: a.wall };
    }
    // framed art inside a part of a room
    const art = house.getObjectByName('wall_art');
    if (!art) return null;
    const b = new THREE.Box3();
    const v = new THREE.Vector3();
    art.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const pos = m.geometry.getAttribute('position');
      for (let i = 0; i < pos.count; i++) {
        v.fromBufferAttribute(pos, i).applyMatrix4(m.matrixWorld);
        if (v.y > 0.2 && inRect(a.art, v.x, v.z, 0.05)) b.expandByPoint(v);
      }
    });
    if (b.isEmpty()) return null;
    const c = b.getCenter(new THREE.Vector3());
    return { at: c, face: side(c.x, c.z) ?? undefined };
  }
}

const shown = (o: THREE.Object3D | null) => {
  for (; o; o = o.parent) if (!o.visible) return false;
  return true;
};

/**
 * Which side of the house's outline a point is on: house on one side within 35 cm, open ground on the
 * other. Covers both faces and the top of a perimeter wall, and art hung on it. Points between two
 * rooms (partitions, glass) or deeper inside are null, and so stay put. Corner pieces go with the
 * x-facing wall.
 */
function side(x: number, z: number): Face | null {
  const s = 0.35;
  const xp = onFootprint(x + s, z), xm = onFootprint(x - s, z), zp = onFootprint(x, z + s), zm = onFootprint(x, z - s);
  if (xp && !xm) return '-x';
  if (xm && !xp) return '+x';
  if (zp && !zm) return '-z';
  if (zm && !zp) return '+z';
  if (xp || xm || zp || zm) return null;
  // outside both walls at a corner
  if (onFootprint(x + s, z + s) || onFootprint(x + s, z - s)) return '-x';
  if (onFootprint(x - s, z + s) || onFootprint(x - s, z - s)) return '+x';
  return null;
}
