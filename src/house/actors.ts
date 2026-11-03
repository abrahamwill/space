/**
 * The things that move: the character, the pet and the record on the turntable.
 * Built from the same flat-colour boxes/spheres as the room (so they match the art), as small
 * hierarchies of groups with pivots at the joints. life.ts decides what they're doing; this file
 * turns that into joint angles, blending between postures so nothing snaps.
 */
import { Color, Group, Mesh, MeshBasicMaterial, type Material, type Scene, Vector3 } from 'three';
import { LineSegments2 } from 'three/examples/jsm/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/examples/jsm/lines/LineSegmentsGeometry.js';
import type { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js';
import { buildPart, toWorld } from './geometry';
import { INK, P, PLATTER, Z_SQUASH as S, ANCHORS, type Prim, type RoomId, type V3 } from './layout';
import { CharacterBrain, PetBrain, roomAt, SWAP_TIME, type CharacterPose } from './life';

/** Live hotspot positions (world). The overlay pins read these every frame. */
export const LIVE = {
  me: toWorld(ANCHORS.me),
  pet: toWorld(ANCHORS.pet),
};

const SKIN = '#e9b48a', SKIN_D = '#cf9670';
const box = (x: number, y: number, z: number, w: number, d: number, h: number, top: string, left: string, right: string): Prim =>
  ({ t: 'box', x, y, z, w, d, h, top, left, right, ol: true });
const disc = (cx: number, cy: number, z: number, r: number, fill: string, ol: boolean, n = 28): Prim => ({
  t: 'poly',
  pts: Array.from({ length: n }, (_, i): V3 => [cx + r * Math.cos((i * 2 * Math.PI) / n), cy + r * Math.sin((i * 2 * Math.PI) / n), z]),
  fill,
  ol,
});

interface Ctx {
  materials: Record<RoomId, Material>;
  lineMat: LineMaterial;
  hullMat: MeshBasicMaterial;
  disposables: Array<{ dispose(): void }>;
}

/** A group with one part's mesh, outlines and hull. Meshes are collected so the room material can be swapped. */
function part(ctx: Ctx, prims: Prim[], room: RoomId, meshes: Mesh[]) {
  const g = new Group();
  const { batch, hull } = buildPart(prims);
  const m = new Mesh(batch.mesh, ctx.materials[room]);
  const lg = new LineSegmentsGeometry();
  lg.setPositions(batch.lines);
  g.add(m, new LineSegments2(lg, ctx.lineMat));
  if (hull) g.add(new Mesh(hull, ctx.hullMat));
  ctx.disposables.push(batch.mesh, lg, ...(hull ? [hull] : []));
  meshes.push(m);
  return g;
}

const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const at = (x: number, z: number, y: number) => new Vector3(x, z * S, y); // plan (x, y, z) offsets → world

// ---------------------------------------------------------------- character

const HIP = 1.6; // standing hip height (plan z)
const LEG = 0.8; // thigh and shin length

class Character {
  root = new Group();
  meshes: Mesh[] = [];
  brain = new CharacterBrain();
  private hips = new Group();
  private thigh: Group[] = [];
  private shin: Group[] = [];
  private arm: Group[] = [];
  private head: Group;
  private room: RoomId = 'main';
  /** Current joint values, eased toward each frame's targets. */
  private j = { hip: HIP, thigh: [0, 0], shin: [0, 0], arm: [0, 0], head: 0 };

  constructor(private ctx: Ctx) {
    const legPrims = [box(-0.4, -0.19, -LEG, 0.8, 0.38, LEG, P.char, P.char, '#262628')];
    for (const side of [-1, 1]) {
      const t = part(ctx, legPrims, 'main', this.meshes);
      t.position.copy(at(0, 0, side * 0.21));
      const s = part(ctx, legPrims, 'main', this.meshes);
      s.position.copy(at(0, -LEG, 0));
      t.add(s);
      this.hips.add(t);
      this.thigh.push(t);
      this.shin.push(s);
    }
    this.hips.add(part(ctx, [box(-0.58, -0.58, 0, 1.16, 1.16, 1.3, P.mus, P.mus, '#b8861f')], 'main', this.meshes));
    for (const side of [-1, 1]) {
      const a = part(ctx, [
        box(-0.17, -0.13, -0.62, 0.34, 0.26, 0.62, P.mus, P.mus, '#b8861f'),
        box(-0.15, -0.11, -1.08, 0.3, 0.22, 0.46, SKIN, SKIN, SKIN_D),
      ], 'main', this.meshes);
      a.position.copy(at(0, 1.18, side * 0.71));
      this.hips.add(a);
      this.arm.push(a);
    }
    this.head = part(ctx, [
      box(-0.44, -0.44, 0, 0.88, 0.88, 0.8, SKIN, SKIN, SKIN_D),
      box(-0.54, -0.54, 0.65, 1.08, 1.08, 0.32, INK, INK, INK),
      // eyes, so you can tell which way they're facing
      box(0.44, -0.27, 0.3, 0.03, 0.12, 0.16, INK, INK, INK),
      box(0.44, 0.15, 0.3, 0.03, 0.12, 0.16, INK, INK, INK),
    ], 'main', this.meshes);
    this.head.position.copy(at(0, 1.3, 0));
    this.hips.add(this.head);
    this.root.add(this.hips);
    this.apply(0, true);
  }

  /** Joint targets for a pose (angles in radians; + swings a limb forward). */
  private targets(p: CharacterPose) {
    const s = p.settle, t = p.t, ph = p.phase;
    const breathe = Math.sin(t * 1.7) * 0.012;
    switch (p.clip) {
      case 'walk': {
        const sw = Math.sin(ph);
        return {
          hip: HIP + Math.abs(Math.cos(ph)) * 0.05,
          thigh: [sw * 0.5, -sw * 0.5],
          shin: [-Math.max(0, -sw) * 0.6, -Math.max(0, sw) * 0.6],
          arm: [-sw * 0.45, sw * 0.45],
          head: 0,
        };
      }
      case 'sit':
      case 'type': {
        const typing = p.clip === 'type';
        const tap = typing ? Math.sin(t * 13) * 0.07 : 0;
        return {
          hip: lerp(HIP, p.seat, s) + breathe,
          thigh: [s * Math.PI / 2, s * Math.PI / 2],
          shin: [-s * Math.PI / 2, -s * Math.PI / 2],
          arm: typing ? [s * 1.1 + tap, s * 1.1 - tap] : [s * 0.4, s * 0.4],
          head: typing ? 0 : Math.sin(t * 0.4) * 0.25,
        };
      }
      case 'crouch': {
        // a gentle knee bend and a reach down toward the pet (deep squats fold badly with box legs)
        const a = 0.42 * s;
        const pat = Math.sin(t * 5) * 0.15 * s;
        return {
          hip: 2 * LEG * Math.cos(a),
          thigh: [a, a],
          shin: [-2 * a, -2 * a],
          arm: [s * 0.75 + pat, s * 0.45],
          head: 0,
        };
      }
      case 'swap': {
        // reach for the record, lift it while it's off the platter, put the new one down
        const up = smooth(0.25, 0.6, t) * (1 - smooth(1.0, 1.4, t));
        return { hip: HIP + breathe, thigh: [0, 0], shin: [0, 0], arm: [s * (0.9 + up * 0.55), s * (0.8 + up * 0.55)], head: 0 };
      }
      case 'play': {
        const mash = Math.sin(t * 17) * 0.09;
        return { hip: HIP + breathe, thigh: [0, 0], shin: [0, 0], arm: [s * 0.85 + mash, s * 0.85 - mash], head: Math.sin(t * 3) * 0.05 };
      }
      case 'interact': {
        const reach = 0.95 + Math.sin(t * 2.2) * 0.2;
        return { hip: HIP + breathe, thigh: [0, 0], shin: [0, 0], arm: [s * reach, s * (reach - 0.25)], head: Math.sin(t * 1.1) * 0.08 };
      }
      default:
        return { hip: HIP + breathe, thigh: [0, 0], shin: [0, 0], arm: [0.04 + breathe * 2, 0.04 - breathe * 2], head: Math.sin(t * 0.5) * 0.3 };
    }
  }

  private apply(dt: number, snap = false) {
    const p = this.brain.pose;
    const g = this.targets(p);
    const k = snap ? 1 : 1 - Math.exp(-dt * 12);
    const j = this.j;
    j.hip = lerp(j.hip, g.hip, k);
    j.head = lerp(j.head, g.head, k);
    for (const i of [0, 1]) {
      j.thigh[i] = lerp(j.thigh[i], g.thigh[i], k);
      j.shin[i] = lerp(j.shin[i], g.shin[i], k);
      j.arm[i] = lerp(j.arm[i], g.arm[i], k);
      this.thigh[i].rotation.z = j.thigh[i];
      this.shin[i].rotation.z = j.shin[i];
      this.arm[i].rotation.z = j.arm[i];
    }
    this.head.rotation.y = j.head;
    this.hips.position.y = j.hip * S;
    this.root.position.set(p.x, 0, p.y);
    this.root.rotation.y = -p.heading;
    // take on the light of whichever room they're standing in
    const room = roomAt(p.x, p.y);
    if (room !== this.room) {
      this.room = room;
      for (const m of this.meshes) m.material = this.ctx.materials[room];
    }
    LIVE.me.set(p.x, (j.hip + 2.3) * S, p.y);
  }

  update(dt: number) {
    this.brain.update(dt);
    this.apply(dt);
  }
}

// ---------------------------------------------------------------- pet

const PET_R = 0.78;

class Pet {
  root = new Group();
  brain = new PetBrain();
  private body = new Group();
  private eyes: Group;

  constructor(ctx: Ctx) {
    const meshes: Mesh[] = [];
    this.body.add(part(ctx, [
      { t: 'ball', cx: 0, cy: 0, z: 0, r: PET_R, fill: P.cream, ol: true },
      box(-0.25, -0.43, 0.5, 0.26, 0.26, 0.6, P.cream, P.cream, P.creamD),
      box(-0.25, 0.17, 0.5, 0.26, 0.26, 0.6, P.cream, P.cream, P.creamD),
    ], 'lab', meshes));
    // eyes on the front of the sphere, a little up and apart (balls aren't squashed, so undo it for z)
    const eye = (side: number): Prim => {
      const d = new Vector3(1, 0.3, side * 0.36).normalize().multiplyScalar(PET_R);
      return { t: 'ball', cx: d.x, cy: d.z, z: d.y / S, r: 0.1, fill: INK, ol: false };
    };
    this.eyes = part(ctx, [eye(-1), eye(1)], 'lab', meshes);
    this.body.add(this.eyes);
    this.root.add(this.body);
    this.apply();
  }

  private apply() {
    const p = this.brain.pose;
    this.root.position.set(p.x, 0, p.y);
    this.root.rotation.y = -p.heading;
    this.body.position.y = p.lift;
    const w = 1 / Math.sqrt(p.squash);
    this.body.scale.set(w, p.squash, w);
    // blink now and then; shut while asleep
    const blink = (performance.now() / 1000) % 4.3 < 0.12 ? 1 : 0;
    const shut = Math.max(p.sleepy, blink);
    this.eyes.scale.y = Math.max(0.12, 1 - shut);
    this.eyes.position.y = -0.03 * shut;
    LIVE.pet.set(p.x, p.lift + 0.95, p.y);
  }

  update(dt: number) {
    this.brain.update(dt);
    this.apply();
  }
}

// ---------------------------------------------------------------- record

/**
 * The record on the turntable. Spins at 33⅓; a swap lifts it off, tips it, changes the label at the
 * halfway point (that's when the song changes), and drops it back on. Same timing as the character's
 * 'swap' clip, so their hands meet it.
 */
class Vinyl {
  root = new Group();
  private lift = new Group();
  private spin = new Group();
  private label: MeshBasicMaterial;
  private t = -1;
  private swapped = false;
  onSwap?: () => void;
  onEnd?: () => void;

  constructor(ctx: Ctx) {
    this.spin.add(part(ctx, [
      disc(0, 0, 0, PLATTER.r, INK, true, 32),
      // a sheen across the grooves, so you can see it turn
      { t: 'poly', pts: [[0.28, -0.03, 0.012], [0.52, -0.05, 0.012], [0.52, 0.05, 0.012], [0.28, 0.03, 0.012]], fill: '#4a4a4e', ol: false },
      disc(0.11, 0, 0.022, 0.045, P.cream, false, 12),
    ], 'main', []));
    // the label is its own mesh so its colour can change with the record
    const { batch } = buildPart([disc(0, 0, 0.01, 0.2, P.red, false)]);
    this.label = new MeshBasicMaterial({ color: new Color(P.red) });
    ctx.disposables.push(batch.mesh, this.label);
    this.spin.add(new Mesh(batch.mesh, this.label));
    this.lift.add(this.spin);
    this.root.add(this.lift);
    this.root.position.copy(toWorld([PLATTER.cx, PLATTER.cy, PLATTER.z]));
  }

  get swapping() {
    return this.t >= 0;
  }
  /** Past the moment the record changes (a new request now needs another swap). */
  get pastSwap() {
    return this.swapped;
  }

  setLabel(hex: string) {
    this.label.color.set(hex);
  }

  startSwap() {
    this.t = 0;
    this.swapped = false;
  }

  update(dt: number) {
    let up = 0;
    if (this.t >= 0) {
      this.t += dt;
      up = smooth(0.3, 0.65, this.t) * (1 - smooth(1.05, 1.45, this.t));
      if (!this.swapped && this.t >= SWAP_TIME / 2) {
        this.swapped = true;
        this.onSwap?.();
      }
      if (this.t >= SWAP_TIME) {
        this.t = -1;
        this.onEnd?.();
      }
    }
    this.lift.position.y = up * 0.55;
    this.lift.rotation.z = up * 0.45;
    // slows to a stop while it's off the platter
    this.spin.rotation.y -= dt * ((33.33 / 60) * 2 * Math.PI) * (1 - Math.min(1, up * 3));
  }
}

// ---------------------------------------------------------------- all together

export type RecordState = 'playing' | 'coming' | 'swapping';
/** How far (in seconds) the character will come to change a record; any further and it swaps itself. */
export const SWAP_WALK_CAP = 2;

export class Actors {
  private character: Character;
  private pet: Pet;
  private record: Vinyl;
  private labels: string[] = [P.red];
  private want = 0;
  private onDeck = 0;
  /** The character is on the way to change the record. */
  private coming = false;
  private comingFor = 0;
  /** (record on the platter, what's happening) — for "now playing" in the UI. */
  onRecord?: (onDeck: number, state: RecordState) => void;

  constructor(scene: Scene, ctx: Ctx) {
    this.character = new Character(ctx);
    this.pet = new Pet(ctx);
    this.record = new Vinyl(ctx);
    scene.add(this.character.root, this.pet.root, this.record.root);
    this.character.brain.onActivity = (name, active) => {
      // the pet notices when the character comes over
      if (name === 'pet') {
        const p = this.character.brain.pose;
        if (active) this.pet.brain.greet({ x: p.x, y: p.y });
        else this.pet.brain.bye();
      }
      // their hands are on the record: swap it
      if (name === 'swap' && active) {
        this.coming = false;
        this.swap();
      }
    };
    // the song changes the moment the new record is on
    this.record.onSwap = () => {
      this.onDeck = this.want;
      this.record.setLabel(this.labels[this.onDeck % this.labels.length]);
      this.emit();
    };
    // clicked again after the swap moment: only the latest counts, so swap once more
    this.record.onEnd = () => (this.want !== this.onDeck ? this.swap() : this.emit());
  }

  private emit() {
    this.onRecord?.(this.onDeck, this.record.swapping ? 'swapping' : this.coming ? 'coming' : 'playing');
  }

  private swap() {
    this.record.startSwap();
    this.emit();
  }

  /** Label colours, one per record in the playlist. */
  setRecords(labels: string[]) {
    this.labels = labels.length ? labels : [P.red];
    this.record.setLabel(this.labels[this.onDeck % this.labels.length]);
  }

  /**
   * Put on record `i`. The character comes over if they can get there within SWAP_WALK_CAP seconds,
   * otherwise the record swaps itself. Rapid requests: only the latest is played.
   * `alive` = false (reduced motion, paused): change it straight away, no animation.
   */
  playRecord(i: number, alive: boolean) {
    this.want = i;
    if (!alive) {
      this.coming = false;
      this.onDeck = i;
      this.record.setLabel(this.labels[i % this.labels.length]);
      return this.emit();
    }
    if (this.record.swapping || this.coming) return; // already on it; the latest request wins
    if (i === this.onDeck) return this.emit();
    if (this.character.brain.eta('swap') <= SWAP_WALK_CAP) {
      this.coming = true;
      this.comingFor = 0;
      this.character.brain.ask('swap');
      this.emit();
    } else this.swap();
  }

  /** Ask the character to go and do something (click-to-task). */
  ask(task: 'sofa' | 'arcade' | 'pet') {
    if (this.coming) {
      // they were on their way to the record: it swaps itself instead
      this.coming = false;
      this.swap();
    }
    if (task === 'pet') this.pet.brain.greet();
    this.character.brain.ask(task);
  }

  /** A click on "Pet me". */
  greetPet() {
    this.pet.brain.greet();
  }

  /** The character is at the arcade, playing (the screen shows a game in progress). */
  get playingArcade() {
    return this.character.brain.current === 'arcade' && this.character.brain.pose.clip === 'play';
  }

  update(dt: number) {
    this.character.update(dt);
    this.pet.update(dt);
    this.record.update(dt);
    // safety net: if they don't make it in time, don't keep the listener waiting
    if (this.coming && (this.comingFor += dt) > SWAP_WALK_CAP + 2) {
      this.coming = false;
      this.swap();
    }
  }
}
