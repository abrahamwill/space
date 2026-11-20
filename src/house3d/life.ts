/**
 * The people of the Pinwheel house: the rigged character and the pet.
 *
 * - Character: public/house3d/character.glb (house3d/rig_character.py), the same mesh as the house's
 *   character_abraham, rigged, with idle / wave / walk / sit clips. The house's static copy is hidden.
 *   He starts on his mark (hero3d.person(), what the hero poster shows) in the designed standing pose.
 * - Routines, like the old house (src/house/life.ts): every so often he walks from his mark to a spot in
 *   public/house3d/walks.json (house3d/walks.py: paths round the furniture and through the doors), looks
 *   at the records, the turntable, the PC or the books, sits on the sofa, stands by the garden tree, or
 *   says hi to the pet, then walks back to his mark.
 * - greet(true) stops whatever he is doing (getting up first if he sits): he turns to the camera and
 *   waves. greet(false) puts his arm down and he carries on: on with a walk, or back to his mark.
 * - Pet: lab_pet_Pet in the house GLB. Its body and eyes hop on the cushion now and then and breathe in
 *   between; it hops a few times in a row when he waves or comes to see it. The bed doesn't move.
 *
 * All timing runs on update(dt), which the viewer only calls while the house is on screen and motion is
 * allowed; so off screen, or with reduced motion, he stays put.
 */
import * as THREE from 'three';
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';

export const CHARACTER_URL = '/house3d/character.glb';
export const WALKS_URL = '/house3d/walks.json';

const PET = 'lab_pet_Pet';
const PET_BODY = ['#fbf3e6', '#1b1a17']; // cream body, ink eyes (the mustard bed and cushion stay put)
const BUBBLE_ABOVE_HEAD = 0.68; // m above the head joint: just over his hair

const SPEED = 0.7; // m/s walking
const WALK_CLIP_SPEED = 0.83; // m/s the walk clip covers at timeScale 1 (two 0.42 m steps a second)
const TURN = 5; // rad/s
const SIT_TIME = 0.8; // s to sit down or get up

type XY = [number, number];
const TO_CAMERA: XY = [Math.SQRT1_2, Math.SQRT1_2]; // facing the HeroCamera (plan +x, +y)

export interface Spot {
  name: string;
  act: 'look' | 'sit' | 'pet';
  at: XY;
  face: XY;
  path: XY[];
  seat?: XY;
  lift?: number;
}
export interface Walks {
  mark: { at: XY; face: XY };
  spots: Spot[];
}

export interface Life {
  update(dt: number): void;
  /** on = stop, turn to the camera, wave and say hi. animate = false (reduced motion): jump to the pose. */
  greet(on: boolean, animate: boolean): void;
  /** World point just above the character's head, for the speech bubble. */
  bubbleAt(out: THREE.Vector3): THREE.Vector3;
}

const rand = (a: number, b: number) => a + Math.random() * (b - a);
const heading = (d: XY) => Math.atan2(d[0], d[1]); // plan (x, y) = three (X, Z); he faces +Z at 0
const wrap = (a: number) => Math.atan2(Math.sin(a), Math.cos(a));
const ease = (t: number) => t * t * (3 - 2 * t);

/** A polyline he walks along, by distance. */
function route(pts: XY[]) {
  const len = pts.slice(1).map((p, i) => Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]));
  const total = len.reduce((a, b) => a + b, 0);
  return {
    total,
    at(s: number): { p: XY; d: XY } {
      let k = 0;
      while (k < len.length - 1 && s > len[k]) s -= len[k++];
      const a = pts[k], b = pts[k + 1] ?? pts[k];
      const L = len[k] ?? 0;
      const t = L ? Math.min(1, Math.max(0, s / L)) : 1;
      const d: XY = L ? [(b[0] - a[0]) / L, (b[1] - a[1]) / L] : [0, 1];
      return { p: [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t], d };
    },
  };
}
type Route = ReturnType<typeof route>;

type State =
  | { k: 'home'; wait: number }
  | { k: 'walk'; spot: Spot; back: boolean; r: Route; s: number }
  | { k: 'turn'; spot: Spot | null; to: number }
  | { k: 'do'; spot: Spot; wait: number }
  | { k: 'sit'; spot: Spot; t: number; down: boolean; wait: number }
  | { k: 'hi' };

export function bringToLife(house: THREE.Object3D, char: GLTF, walks: Walks | null): Life {
  // The house's own (static, waving) copy makes way for the rigged one.
  const still = house.getObjectByName('character_abraham');
  if (still) still.visible = false;

  const me = char.scene;
  me.traverse((o) => {
    if ((o as THREE.Mesh).isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
      o.frustumCulled = false; // skinned: the bind-pose bounds don't follow him around
    }
  });
  house.parent?.add(me);
  const rig = me.getObjectByName('rig_abraham') ?? me.children[0] ?? me;
  const floorY = rig.position.y;

  const mixer = new THREE.AnimationMixer(me);
  const action = (name: string) => {
    const clip = THREE.AnimationClip.findByName(char.animations, name);
    if (!clip) throw new Error(`character.glb has no "${name}" clip`);
    return mixer.clipAction(clip);
  };
  const clips = { idle: action('idle'), wave: action('wave'), walk: action('walk'), sit: action('sit') };
  clips.walk.timeScale = SPEED / WALK_CLIP_SPEED;
  let clip = clips.idle;
  clip.play();
  mixer.update(0);
  const play = (next: THREE.AnimationAction, fade = 0.25) => {
    if (next === clip) return;
    next.reset().setEffectiveWeight(1).fadeIn(fade).play();
    clip.fadeOut(fade);
    clip = next;
  };

  const head = me.getObjectByName('head') ?? me;
  const pet = petHops(house);

  // ---- where he is (plan metres; three.js X, Z)
  const pos: XY = walks ? [...walks.mark.at] : [rig.position.x, rig.position.z];
  let yaw = walks ? heading(walks.mark.face) : 0;
  let lift = 0;
  const place = () => {
    rig.position.set(pos[0], floorY + lift, pos[1]);
    rig.quaternion.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, yaw);
  };
  if (walks) place();
  const turnTo = (target: number, dt: number) => {
    const d = wrap(target - yaw);
    const stepA = TURN * dt;
    yaw = Math.abs(d) <= stepA ? target : yaw + Math.sign(d) * stepA;
    return Math.abs(d) <= stepA;
  };
  const seatAt = (spot: Spot, t: number) => {
    const k = ease(t), a = spot.at, b = spot.seat ?? spot.at;
    pos[0] = a[0] + (b[0] - a[0]) * k;
    pos[1] = a[1] + (b[1] - a[1]) * k;
    lift = (spot.lift ?? 0) * k;
  };

  // ---- the routine: home -> walk out -> turn -> look / sit / pet -> walk back -> turn -> home
  let state: State = { k: 'home', wait: rand(6, 10) };
  let before: State | null = null; // what he was doing when someone said hi
  let last = '';

  const walkTo = (spot: Spot, back: boolean, s = 0) => {
    state = { k: 'walk', spot, back, r: route(back ? [...spot.path].reverse() : spot.path), s };
    play(clips.walk, 0.3);
  };
  const pick = () => {
    const options = walks!.spots.filter((p) => p.name !== last);
    return options[Math.floor(Math.random() * options.length)];
  };

  function step(dt: number) {
    switch (state.k) {
      case 'home':
        if ((state.wait -= dt) <= 0 && walks?.spots.length) {
          const spot = pick();
          last = spot.name;
          walkTo(spot, false);
        }
        break;
      case 'walk': {
        state.s += SPEED * dt;
        const { p, d } = state.r.at(state.s);
        [pos[0], pos[1]] = p;
        turnTo(heading(d), dt);
        if (state.s >= state.r.total) {
          play(clips.idle, 0.3);
          state = state.back
            ? { k: 'turn', spot: null, to: heading(walks!.mark.face) }
            : { k: 'turn', spot: state.spot, to: heading(state.spot.face) };
        }
        break;
      }
      case 'turn':
        if (turnTo(state.to, dt)) {
          const spot = state.spot;
          if (!spot) state = { k: 'home', wait: rand(8, 16) };
          else if (spot.act === 'sit') {
            state = { k: 'sit', spot, t: 0, down: true, wait: rand(6, 10) };
            play(clips.sit, SIT_TIME);
          } else {
            if (spot.act === 'pet') pet?.excite();
            state = { k: 'do', spot, wait: rand(3, 6) };
          }
        }
        break;
      case 'do':
        if ((state.wait -= dt) <= 0) walkTo(state.spot, true);
        break;
      case 'sit': {
        const st = state;
        if (st.down) {
          st.t = Math.min(1, st.t + dt / SIT_TIME);
          if (st.t >= 1 && (st.wait -= dt) <= 0) {
            st.down = false;
            play(clips.idle, SIT_TIME);
          }
        } else {
          st.t = Math.max(0, st.t - dt / SIT_TIME);
          if (st.t <= 0) walkTo(st.spot, true);
        }
        seatAt(st.spot, st.t);
        break;
      }
      case 'hi':
        // get up first if he was sitting, then face the camera
        if (before?.k === 'sit' && before.t > 0) {
          before.t = Math.max(0, before.t - dt / (SIT_TIME * 0.6));
          seatAt(before.spot, before.t);
        }
        turnTo(heading(TO_CAMERA), dt);
        break;
    }
  }

  return {
    update(dt) {
      step(dt);
      place();
      mixer.update(dt);
      pet?.update(dt);
    },
    greet(on, animate) {
      if (!animate) {
        // reduced motion: no routine runs; just change the pose where he stands
        clip.stop();
        clip = on ? clips.wave : clips.idle;
        clip.reset().setEffectiveWeight(1).play();
        mixer.update(0);
        return;
      }
      if (on) {
        if (state.k !== 'hi') before = state;
        state = { k: 'hi' };
        play(clips.wave, 0.3);
        pet?.excite();
        return;
      }
      if (state.k !== 'hi') return;
      const was = before;
      before = null;
      if (!walks || !was || was.k === 'home') {
        play(clips.idle, 0.45);
        state = { k: 'home', wait: rand(4, 8) };
      } else if (was.k === 'walk') {
        walkTo(was.spot, was.back, was.s); // carry on where he was
      } else if (was.k === 'turn' && !was.spot) {
        play(clips.idle, 0.45);
        state = { k: 'turn', spot: null, to: heading(walks.mark.face) };
      } else if (was.k !== 'hi') {
        // interrupted at a spot: he's up now, so head back to his mark from where he stands
        const spot = was.spot!;
        lift = 0;
        const r = route([[pos[0], pos[1]], ...[...spot.path].reverse().slice(1)]);
        state = { k: 'walk', spot, back: true, r, s: 0 };
        play(clips.walk, 0.45);
      }
    },
    bubbleAt(out) {
      head.getWorldPosition(out);
      out.y += BUBBLE_ABOVE_HEAD;
      return out;
    },
  };
}

/** Hops: a short squash-and-stretch jump of the pet's body, pivoting on the cushion. */
function petHops(house: THREE.Object3D) {
  const pet = house.getObjectByName(PET);
  if (!pet) return null;
  const parts: THREE.Mesh[] = [];
  pet.traverse((o) => {
    const m = o as THREE.Mesh;
    if (m.isMesh && PET_BODY.includes((m.material as THREE.Material).name)) parts.push(m);
  });
  if (!parts.length) return null;

  // pivot at the bottom centre of the body, so it squashes onto the cushion
  house.updateMatrixWorld(true);
  const box = new THREE.Box3();
  parts.forEach((p) => box.expandByObject(p));
  const size = box.getSize(new THREE.Vector3());
  const foot = new THREE.Vector3((box.min.x + box.max.x) / 2, box.min.y, (box.min.z + box.max.z) / 2);
  const pivot = new THREE.Group();
  pivot.name = `${PET}_hop`;
  pet.add(pivot);
  pivot.position.copy(pet.worldToLocal(foot.clone()));
  pivot.updateMatrixWorld(true);
  parts.forEach((p) => pivot.attach(p));
  const rest = pivot.position.clone();
  const up = pet.worldToLocal(foot.clone().add(new THREE.Vector3(0, 1, 0))).sub(pivot.position).normalize();

  let t = 0;
  let hop: { start: number; dur: number; height: number } | null = null;
  let next = 1.2; // first hop shortly after the house appears
  let pairLeft = 1;
  let excitedUntil = -1;

  return {
    excite() {
      excitedUntil = t + 1.7;
      if (!hop) next = t;
    },
    update(dt: number) {
      t += dt;
      if (!hop && t >= next) {
        const excited = t < excitedUntil;
        hop = { start: t, dur: excited ? 0.36 : 0.42, height: size.y * (excited ? 0.55 : 0.3) };
        if (excited) next = t + hop.dur + 0.04;
        else if (pairLeft > 0) {
          pairLeft--; // hops come in pairs: hop-hop ... rest ... hop-hop
          next = t + hop.dur + 0.06;
        } else {
          pairLeft = 1;
          next = t + hop.dur + 2.4 + Math.random() * 1.6;
        }
      }
      let lift = 0, sy = 1, sxz = 1;
      if (hop) {
        const u = (t - hop.start) / hop.dur;
        if (u >= 1) hop = null;
        else if (u < 0.78) {
          const s = Math.sin(Math.PI * (u / 0.78));
          lift = hop.height * s;
          sy = 1 + 0.08 * s;
          sxz = 1 - 0.04 * s;
        } else {
          const s = Math.sin(Math.PI * ((u - 0.78) / 0.22));
          sy = 1 - 0.14 * s;
          sxz = 1 + 0.07 * s;
        }
      }
      if (!hop) {
        const b = Math.sin((t * 2 * Math.PI) / 2.2); // breathing between hops
        sy = 1 + 0.025 * b;
        sxz = 1 - 0.012 * b;
      }
      pivot.position.copy(rest).addScaledVector(up, lift);
      pivot.scale.set(sxz, sy, sxz);
    },
  };
}
