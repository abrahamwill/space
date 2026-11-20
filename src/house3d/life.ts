/**
 * The people of the Pinwheel house: the rigged character and the pet.
 *
 * - Character: public/house3d/character.glb (house3d/rig_character.py), the same mesh as the house's
 *   character_abraham, rigged, with idle / wave / walk / sit clips. It stands where the house puts him;
 *   the house's static copy is hidden. At rest he plays "idle" (frame 0 is the designed standing pose,
 *   which is what the hero poster shows); greet(true) crossfades into "wave", greet(false) back.
 * - Pet: lab_pet_Pet in the house GLB. Its body and eyes hop on the cushion now and then and breathe in
 *   between; greet(true) makes it hop a few times in a row. The bed doesn't move.
 */
import * as THREE from 'three';
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';

export const CHARACTER_URL = '/house3d/character.glb';

const PET = 'lab_pet_Pet';
const PET_BODY = ['#fbf3e6', '#1b1a17']; // cream body, ink eyes (the mustard bed and cushion stay put)
const BUBBLE_ABOVE_HEAD = 0.68; // m above the head joint: just over his hair

export interface Life {
  update(dt: number): void;
  /** on = wave and say hi. animate = false (reduced motion): jump straight to the pose. */
  greet(on: boolean, animate: boolean): void;
  /** World point just above the character's head, for the speech bubble. */
  bubbleAt(out: THREE.Vector3): THREE.Vector3;
  /** The pet hops a few times in a row (the "pet me" hotspot). */
  excitePet(): void;
}

export function bringToLife(house: THREE.Object3D, char: GLTF): Life {
  // The house's own (static, waving) copy makes way for the rigged one.
  const still = house.getObjectByName('character_abraham');
  if (still) still.visible = false;

  const me = char.scene;
  me.traverse((o) => {
    if ((o as THREE.Mesh).isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
      o.frustumCulled = false; // skinned: the bind-pose bounds don't follow the raised arm
    }
  });
  house.parent?.add(me);

  const mixer = new THREE.AnimationMixer(me);
  const action = (name: string) => {
    const clip = THREE.AnimationClip.findByName(char.animations, name);
    if (!clip) throw new Error(`character.glb has no "${name}" clip`);
    return mixer.clipAction(clip);
  };
  const idle = action('idle');
  const wave = action('wave');
  idle.play();
  mixer.update(0);

  const head = me.getObjectByName('head') ?? me;
  const pet = petHops(house);

  return {
    update(dt) {
      mixer.update(dt);
      pet?.update(dt);
    },
    greet(on, animate) {
      const [to, from] = on ? [wave, idle] : [idle, wave];
      if (animate) {
        to.reset().setEffectiveWeight(1).fadeIn(on ? 0.3 : 0.45).play();
        from.fadeOut(on ? 0.3 : 0.45);
        if (on) pet?.excite();
      } else {
        from.stop();
        to.reset().setEffectiveWeight(1).play();
        mixer.update(0);
      }
    },
    excitePet() {
      pet?.excite();
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
