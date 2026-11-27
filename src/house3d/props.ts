/**
 * Small pieces added to the Pinwheel house in code, until they're modelled in house3d/source and the
 * GLB is rebuilt (asked for by Abraham, 2026-11-21).
 *
 * The running wall: a medal hanger and instax prints of his running, on the workout deck's outer wall
 * (x = 0), between the pull-up station's uprights, facing the treadmill's console end. Same look as the
 * GLB: flat colours from the house palette, lit and shadowed by the scene.
 *
 * World = the GLB's plan metres (plan x → X, plan y → Z, up → Y). Everything sits a few mm off the
 * wall's face and faces +X.
 */
import * as THREE from 'three';

export const RUNNING_WALL = 'deckS_running_wall';

const WALL_X = 0; // the deck's outer wall face
const Z0 = 8.93, Z1 = 9.67; // clear wall between the pull-up uprights

const INK = '#2b2b2e';
const GOLD = '#e0a72e', SILVER = '#cfcfca', BRONZE = '#b06c3a';
const RIBBONS = ['#c8442b', '#2b4fa8', '#5a8a3a', '#e0a72e', '#c8442b'];
const MEDALS = [GOLD, SILVER, BRONZE, GOLD, SILVER];
const CARD = '#fbf3e6';
// placeholder "photos": sky, track, sunrise, park, city, sea
const PHOTOS = ['#7fa7c9', '#c9774a', '#e8a24f', '#86ad57', '#8f8f99', '#5f8fb0'];

export function addProps(house: THREE.Object3D) {
  const mats = new Map<string, THREE.MeshStandardMaterial>();
  const mat = (hex: string, metal = false) => {
    const key = hex + (metal ? 'm' : '');
    if (!mats.has(key)) mats.set(key, new THREE.MeshStandardMaterial({ color: hex, roughness: metal ? 0.45 : 0.9, metalness: metal ? 0.35 : 0, flatShading: true }));
    return mats.get(key)!;
  };
  const wall = new THREE.Group();
  wall.name = RUNNING_WALL;
  /** A box on the wall: z, y = centre; d = how far it stands off the wall. */
  const box = (z: number, y: number, w: number, h: number, d: number, m: THREE.Material, off = 0, tilt = 0) => {
    const b = new THREE.Mesh(new THREE.BoxGeometry(d, h, w), m);
    b.position.set(WALL_X + off + d / 2, y, z);
    b.rotation.x = tilt;
    wall.add(b);
    return b;
  };

  // medal hanger: a black rail on two pegs, five medals on ribbons
  const zc = (Z0 + Z1) / 2;
  const railY = 1.42;
  box(zc, railY, 0.56, 0.035, 0.025, mat(INK), 0.012);
  for (const z of [zc - 0.24, zc + 0.24]) box(z, railY, 0.02, 0.02, 0.012, mat(INK));
  MEDALS.forEach((m, i) => {
    const z = zc - 0.2 + i * 0.1;
    const drop = 0.11 + (i % 2) * 0.03; // staggered, so they don't line up like a chart
    box(z, railY - 0.02 - drop / 2, 0.026, drop, 0.004, mat(RIBBONS[i]), 0.026);
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.032, 0.032, 0.008, 12), mat(m, true));
    disc.rotation.z = Math.PI / 2; // face +X
    disc.position.set(WALL_X + 0.034, railY - 0.02 - drop - 0.028, z);
    wall.add(disc);
  });

  // instax prints: two rows of three, each a cream card with the picture in the top part
  const cw = 0.12, ch = 0.15; // a little larger than life, so they read at house scale
  PHOTOS.forEach((p, i) => {
    const row = Math.floor(i / 3), col = i % 3;
    const z = zc + (col - 1) * 0.2 + (row ? 0.05 : -0.02);
    const y = 1.06 - row * 0.2;
    const tilt = [0.06, -0.04, 0.03, -0.05, 0.04, -0.03][i];
    box(z, y, cw, ch, 0.004, mat(CARD), 0.004, tilt);
    box(z, y + 0.013, cw * 0.82, ch * 0.62, 0.002, mat(p), 0.008, tilt);
  });

  wall.traverse((o) => {
    if ((o as THREE.Mesh).isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
  house.add(wall);
  return wall;
}
