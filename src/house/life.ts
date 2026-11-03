/**
 * Ambient life: small state machines over a hand-placed waypoint graph (no navmesh, no physics).
 * Plain data + logic, no three.js. actors.ts turns the poses into moving models.
 *
 * Coordinates are plan units (see layout.ts). Headings are plan angles: 0 faces +x, π/2 faces +y.
 */
import type { RoomId } from './layout';

export type Clip = 'idle' | 'walk' | 'sit' | 'interact' | 'type' | 'crouch';

export interface CharacterPose {
  x: number;
  y: number;
  heading: number;
  clip: Clip;
  /** Seat height (plan z) while sitting. */
  seat: number;
  /** 0→1 blend into the sit/crouch posture. */
  settle: number;
  /** Seconds in the current clip (drives the procedural cycles). */
  t: number;
  /** Walk cycle phase, advanced by distance so feet don't slide. */
  phase: number;
}

export interface PetPose {
  x: number;
  y: number;
  heading: number;
  /** Height of the body's centre above the floor (plan z). */
  lift: number;
  /** Squash (<1) and stretch (>1) on the vertical axis. */
  squash: number;
  /** 0 = eyes open, 1 = shut. */
  sleepy: number;
  happy: boolean;
}

// ---------------------------------------------------------------- waypoint graph (main room + studio + lab door)

type Node = { x: number; y: number };
const N: Record<string, Node> = {
  start: { x: 6.4, y: 19.8 },
  turntable: { x: 2.9, y: 18.6 },
  window: { x: 2.3, y: 14.0 },
  westAisle: { x: 4.2, y: 15.8 },
  rugNorth: { x: 6.3, y: 13.2 },
  chairFront: { x: 6.7, y: 11.7 },
  studioDoor: { x: 7.0, y: 9.8 },
  studioIn: { x: 7.0, y: 8.4 },
  sofaNorth: { x: 10.6, y: 13.0 },
  sofaFront: { x: 10.8, y: 15.5 },
  south: { x: 10.8, y: 20.6 },
  eastSouth: { x: 15.0, y: 20.3 },
  eastNorth: { x: 15.0, y: 12.2 },
  records: { x: 15.6, y: 10.9 },
  labDoor: { x: 17.2, y: 16.0 },
  labIn: { x: 19.6, y: 16.0 },
  petSpot: { x: 22.6, y: 15.4 },
  hall: { x: 4.4, y: 23.4 },
  door: { x: 1.7, y: 25.2 },
};
const EDGES: Array<[string, string]> = [
  ['start', 'turntable'], ['start', 'westAisle'], ['westAisle', 'window'], ['westAisle', 'rugNorth'],
  ['rugNorth', 'chairFront'], ['rugNorth', 'studioDoor'], ['studioDoor', 'studioIn'], ['rugNorth', 'sofaNorth'],
  ['sofaNorth', 'sofaFront'], ['sofaFront', 'south'], ['start', 'south'], ['south', 'eastSouth'],
  ['eastSouth', 'eastNorth'], ['eastNorth', 'records'], ['eastSouth', 'labDoor'], ['labDoor', 'labIn'],
  ['labIn', 'petSpot'], ['start', 'hall'], ['hall', 'door'],
];
const ADJ: Record<string, string[]> = {};
for (const [a, b] of EDGES) {
  (ADJ[a] ??= []).push(b);
  (ADJ[b] ??= []).push(a);
}
const dist = (a: Node, b: Node) => Math.hypot(a.x - b.x, a.y - b.y);

/** Shortest path by Dijkstra (the graph is tiny). */
function route(from: string, to: string): string[] {
  const d: Record<string, number> = { [from]: 0 };
  const prev: Record<string, string> = {};
  const open = new Set(Object.keys(N));
  while (open.size) {
    let u = '';
    for (const k of open) if (d[k] !== undefined && (u === '' || d[k] < d[u])) u = k;
    if (!u || u === to) break;
    open.delete(u);
    for (const v of ADJ[u] ?? []) {
      const nd = d[u] + dist(N[u], N[v]);
      if (d[v] === undefined || nd < d[v]) {
        d[v] = nd;
        prev[v] = u;
      }
    }
  }
  const path = [to];
  while (path[0] !== from && prev[path[0]]) path.unshift(prev[path[0]]);
  return path[0] === from ? path : [from, to];
}

// ---------------------------------------------------------------- activities

interface Activity {
  name: string;
  node: string;
  /** Where to end up (a seat can sit off the graph, next to its node). */
  at?: Node;
  face: number;
  clip: Clip;
  seat?: number;
  dur: [number, number];
  weight: number;
}
const PI = Math.PI;
export const ACTIVITIES: Activity[] = [
  { name: 'turntable', node: 'turntable', face: PI, clip: 'interact', dur: [4, 6], weight: 3 },
  { name: 'window', node: 'window', face: PI, clip: 'idle', dur: [4, 7], weight: 2 },
  { name: 'lounge', node: 'chairFront', at: { x: 4.95, y: 11.7 }, face: 0, clip: 'sit', seat: 1.08, dur: [7, 11], weight: 2 },
  { name: 'sofa', node: 'sofaFront', at: { x: 12.5, y: 15.6 }, face: PI, clip: 'sit', seat: 0.9, dur: [8, 13], weight: 3 },
  { name: 'desk', node: 'studioIn', at: { x: 6.02, y: 7.6 }, face: -PI / 2, clip: 'type', seat: 1.14, dur: [8, 12], weight: 3 },
  { name: 'records', node: 'records', face: -PI / 2, clip: 'interact', dur: [3, 5], weight: 2 },
  { name: 'door', node: 'door', face: PI, clip: 'idle', dur: [2.5, 4], weight: 1 },
  { name: 'pet', node: 'petSpot', face: -0.95, clip: 'crouch', dur: [4, 6], weight: 2 },
  { name: 'rest', node: 'start', face: PI / 2, clip: 'idle', dur: [3, 5], weight: 1 },
];

const rand = (a: number, b: number) => a + Math.random() * (b - a);
const angleTo = (from: number, to: number) => {
  let d = (to - from) % (2 * PI);
  if (d > PI) d -= 2 * PI;
  if (d < -PI) d += 2 * PI;
  return d;
};

/** Which room a plan point is in. */
export function roomAt(x: number, y: number): RoomId {
  if (x >= 18) return 'lab';
  if (y < 9) return 'studio';
  return 'main';
}

const WALK_SPEED = 1.7; // plan units / s
const TURN_SPEED = 7; // rad / s

export class CharacterBrain {
  pose: CharacterPose;
  /** Fired when the character starts / stops an activity (the pet listens for 'pet'). */
  onActivity?: (name: string, active: boolean) => void;
  private node = 'start';
  private path: Node[] = [];
  private activity: Activity = ACTIVITIES[ACTIVITIES.length - 1];
  private left: number;
  private phase: 'act' | 'leave' | 'walk' | 'arrive' = 'act';

  constructor() {
    const s = N.start;
    // The poster shows the character standing on the rug, square to the room like the art (two sides showing).
    this.pose = { x: s.x, y: s.y, heading: PI / 2, clip: 'idle', seat: 0, settle: 0, t: 0, phase: 0 };
    this.left = 3; // hold the poster pose a moment before wandering off
  }

  private pick() {
    const options = ACTIVITIES.filter((a) => a.name !== this.activity.name);
    let r = Math.random() * options.reduce((s, a) => s + a.weight, 0);
    for (const a of options) if ((r -= a.weight) <= 0) return a;
    return options[0];
  }

  update(dt: number) {
    const p = this.pose;
    p.t += dt;
    switch (this.phase) {
      case 'act': {
        this.left -= dt;
        p.settle = Math.min(1, p.settle + dt * 2.5);
        this.turnTo(this.activity.face, dt);
        if (this.left <= 0) {
          this.onActivity?.(this.activity.name, false);
          this.phase = 'leave';
        }
        break;
      }
      case 'leave': {
        // stand up, then step back onto the graph
        p.settle = Math.max(0, p.settle - dt * 2.5);
        if (p.settle === 0) {
          const next = this.pick();
          const nodes = route(this.node, next.node).map((k) => N[k]);
          if (this.activity.at) nodes.unshift(N[this.activity.node]); // step off the seat first
          this.path = [...nodes, ...(next.at ? [next.at] : [])];
          this.activity = next;
          this.node = next.node;
          this.phase = 'walk';
          this.setClip('walk');
        }
        break;
      }
      case 'walk': {
        const target = this.path[0];
        if (!target) {
          this.phase = 'arrive';
          break;
        }
        const dx = target.x - p.x, dy = target.y - p.y;
        const d = Math.hypot(dx, dy);
        if (d < 0.05) {
          this.path.shift();
          break;
        }
        const want = Math.atan2(dy, dx);
        this.turnTo(want, dt);
        // slow down while turning sharply, so corners look deliberate
        const facing = Math.cos(angleTo(p.heading, want));
        const step = Math.min(d, WALK_SPEED * dt * Math.max(0.15, facing));
        p.x += (dx / d) * step;
        p.y += (dy / d) * step;
        p.phase += step * 2.2;
        break;
      }
      case 'arrive': {
        this.turnTo(this.activity.face, dt);
        if (Math.abs(angleTo(p.heading, this.activity.face)) < 0.05) {
          this.setClip(this.activity.clip);
          p.seat = this.activity.seat ?? 0;
          p.settle = 0;
          this.left = rand(...this.activity.dur);
          this.phase = 'act';
          this.onActivity?.(this.activity.name, true);
        }
        break;
      }
    }
  }

  private setClip(c: Clip) {
    if (this.pose.clip !== c) {
      this.pose.clip = c;
      this.pose.t = 0;
    }
  }

  private turnTo(h: number, dt: number) {
    const d = angleTo(this.pose.heading, h);
    this.pose.heading += Math.sign(d) * Math.min(Math.abs(d), TURN_SPEED * dt);
  }
}

// ---------------------------------------------------------------- the pet (lab)

const BED = { x: 24.4, y: 12.9 };
const BOWL_SPOT = { x: 21.5, y: 14.7, face: Math.atan2(13.8 - 14.7, 22.4 - 21.5) };
const WANDER: Node[] = [
  { x: 27.5, y: 14.2 }, { x: 29.0, y: 17.4 }, { x: 25.6, y: 18.1 }, { x: 20.8, y: 17.6 }, { x: 27.2, y: 11.6 },
];
const BED_TOP = 0.3; // the cushion
/** Floor height under the pet: the bed cushion, or the floor. */
const floorAt = (x: number, y: number) => (((x - BED.x) / 1.2) ** 2 + ((y - BED.y) / 0.95) ** 2 < 1 ? BED_TOP : 0);
const R = 0.78; // body radius
const HOP_SPEED = 1.5;
const HOP_RATE = 2.6; // hops / s

type PetState = 'sleep' | 'idle' | 'hop' | 'eat' | 'happy';

export class PetBrain {
  pose: PetPose;
  private state: PetState = 'idle';
  private left = 4;
  private target: (Node & { face?: number }) | null = null;
  private hopT = 0;
  private visitor: Node | null = null;
  private stateT = 0;

  constructor() {
    // As in the art: awake on its bed, facing the viewer.
    this.pose = { x: BED.x, y: BED.y, heading: PI / 4, lift: BED_TOP + R, squash: 1, sleepy: 0, happy: false };
  }

  /** Someone came to say hello (the character, or a click on "Pet me"). */
  greet(from?: Node) {
    this.visitor = from ?? null;
    this.go('happy', 2.2);
  }
  /** The character left. */
  bye() {
    this.visitor = null;
  }

  private go(s: PetState, dur: number, target: (Node & { face?: number }) | null = null) {
    this.state = s;
    this.left = dur;
    this.stateT = 0;
    this.target = target;
  }

  private next() {
    const r = Math.random();
    if (this.visitor) {
      // stay close to whoever is visiting
      const v = this.visitor;
      return this.go('hop', 8, { x: v.x + 1.1, y: v.y - 1.0 });
    }
    if (r < 0.3) return this.go('hop', 10, { ...BED, face: PI / 4 });
    if (r < 0.5) return this.go('hop', 10, { x: BOWL_SPOT.x, y: BOWL_SPOT.y, face: BOWL_SPOT.face });
    const w = WANDER[Math.floor(Math.random() * WANDER.length)];
    return this.go('hop', 10, w);
  }

  update(dt: number) {
    const p = this.pose;
    this.left -= dt;
    this.stateT += dt;
    const base = floorAt(p.x, p.y) + R;
    p.happy = this.state === 'happy';
    p.sleepy += ((this.state === 'sleep' ? 1 : 0) - p.sleepy) * Math.min(1, dt * 3);

    switch (this.state) {
      case 'sleep':
        // slow breathing
        p.lift = base - 0.02;
        p.squash = 1 + Math.sin(this.stateT * 1.6) * 0.03;
        if (this.left <= 0) this.go('idle', 2);
        break;
      case 'idle':
      case 'eat': {
        p.lift = base;
        p.squash = this.state === 'eat' ? 1 - Math.abs(Math.sin(this.stateT * 6)) * 0.08 : 1 + Math.sin(this.stateT * 2.4) * 0.015;
        if (this.left <= 0) this.next();
        break;
      }
      case 'happy': {
        const b = Math.abs(Math.sin(this.stateT * 7));
        p.lift = base + b * 0.45;
        p.squash = 1 + (b - 0.5) * 0.16;
        if (this.visitor) p.heading += angleTo(p.heading, Math.atan2(this.visitor.y - p.y, this.visitor.x - p.x)) * Math.min(1, dt * 6);
        if (this.left <= 0) this.go('idle', 1.5);
        break;
      }
      case 'hop': {
        const t = this.target!;
        const dx = t.x - p.x, dy = t.y - p.y;
        const d = Math.hypot(dx, dy);
        this.hopT += dt * HOP_RATE;
        const h = Math.abs(Math.sin(this.hopT * PI));
        p.lift = base + h * 0.38;
        p.squash = h < 0.15 ? 0.9 : 1 + h * 0.06;
        if (d > 0.04) {
          p.heading += angleTo(p.heading, Math.atan2(dy, dx)) * Math.min(1, dt * 8);
          const step = Math.min(d, HOP_SPEED * dt);
          p.x += (dx / d) * step;
          p.y += (dy / d) * step;
        } else {
          // arrived: settle into whatever the spot is for
          if (t.face !== undefined) p.heading += angleTo(p.heading, t.face) * Math.min(1, dt * 6);
          const atBed = Math.hypot(t.x - BED.x, t.y - BED.y) < 0.1;
          const atBowl = Math.hypot(t.x - BOWL_SPOT.x, t.y - BOWL_SPOT.y) < 0.1;
          if (h < 0.1) {
            if (atBed) this.go('sleep', rand(7, 13));
            else if (atBowl) this.go('eat', rand(2.5, 4));
            else this.go('idle', rand(1.5, 3.5));
          }
        }
        if (this.left <= 0 && d > 0.04) this.left = 1; // keep hopping until it gets there
        break;
      }
    }
  }
}
