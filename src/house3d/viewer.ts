/**
 * Live 3D view of the Pinwheel house (house3d/house_P2.blend → public/house3d/house_P2.glb).
 *
 * Framing comes from the GLB's own HeroCamera, so it matches reference/hero_P2.png.
 * Lighting re-creates the Blender scene (house3d/lighting.py + finish.py) in three.js:
 *   - the exported Sun, with soft shadows
 *   - a flat grey ambient for Blender's world light
 *   - the exported lamp-shade point lights
 * The GLB stores lights in glTF units (lux / candela, = Blender watts × 683). UNITS turns them back
 * into what Blender renders: three.js intensity = Blender strength / π. LIGHT then fine-tunes.
 * Fabric bump, AO and EEVEE soft shadows don't travel in a GLB.
 *
 * Life (life.ts): the rigged character (walking routines from walks.json) and the pet. They only move while the view is on screen, the
 * tab is visible and reduced motion is off, at HERO_FPS; otherwise nothing renders after the first frame.
 * `still` (the poster render) poses them at rest and never moves them.
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import { bringToLife, CHARACTER_URL, WALKS_URL, type Life, type Walks } from './life';
import { addProps } from './props';

const UNITS = 1 / (683 * Math.PI);

// Tuned against house3d/reference/hero_P2.png: mean error 25.6, brightness +0.2
// (the Blender render scores 21.3 / +1.7). Shadowed areas need more ambient here because
// three.js has no AO or light bounce to lift them.
export const LIGHT = {
  sun: 2.2,      // × the exported Sun (Blender strength 2.5)
  ambient: 1.1,  // grey world light (Blender world strength 0.32)
  lamp: 1,       // × the exported lamp lights (Blender 12 W)
};

export const HERO_FPS = 30;

export interface HouseOptions {
  url?: string;
  light?: typeof LIGHT;
  /** The rigged character's GLB, or false to keep the house's static copy. */
  character?: string | false;
  /** Where he walks (house3d/walks.py), or false to keep him on his mark. */
  walks?: string | false;
  /** Pose everything at rest and never animate (poster renders). */
  still?: boolean;
  /** Frames per second while something moves (default HERO_FPS). */
  fps?: number;
  /**
   * The caller drives the camera (the full house view, src/house3d/HouseView.tsx). The frustum is then
   * the canvas size in px, so camera.zoom is px per metre; position and zoom are the caller's.
   */
  control?: boolean;
  /** Called after the canvas is resized (control mode), before the frame is drawn. */
  onResize?: (w: number, h: number) => void;
}

export interface HouseView {
  scene: THREE.Scene;
  renderer: THREE.WebGLRenderer;
  ready: Promise<void>;
  render(): void;
  /** The character waves (and the pet hops) while on; with reduced motion he only changes pose. */
  greet(on: boolean): void;
  /** Where the speech bubble goes: px from the top-left of the mount element, or null before load. */
  bubbleAnchor(): { x: number; y: number } | null;
  /** Called after every rendered frame (e.g. to move the bubble). */
  onFrame: (() => void) | null;
  /** Called every animation tick with dt (s); return true while it still needs frames (e.g. a camera move). */
  step: ((dt: number) => boolean) | null;
  /** Start the loop if anything needs frames (call after changing what `step` animates). */
  kick(): void;
  /** The camera, once the house has loaded. */
  camera(): THREE.OrthographicCamera | null;
  /** The GLB HeroCamera's half-extents (m): the frame the hero poster is cut from. */
  heroFrame(): { x: number; y: number };
  /** The loaded house (gltf scene), once loaded. */
  house(): THREE.Object3D | null;
  /** The pet hops a few times (no-op with reduced motion or before load). */
  excitePet(): void;
  /** World point just above the character's head (null before load). */
  headAt(out: THREE.Vector3): THREE.Vector3 | null;
  dispose(): void;
}

export function mountHouse(el: HTMLElement, opts: HouseOptions = {}): HouseView {
  const { url = '/house3d/house_P2.glb', light = LIGHT, character = CHARACTER_URL, walks = WALKS_URL, still = false, fps = HERO_FPS, control = false } = opts;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping; // Blender "Standard" view
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap; // soft edge comes from shadow.radius
  renderer.setClearColor(0x000000, 0);
  el.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.add(new THREE.AmbientLight(new THREE.Color(0.8, 0.8, 0.82), light.ambient));
  let camera: THREE.OrthographicCamera | null = null;
  let base = { x: 1, y: 1 }; // HeroCamera half-extents

  const draco = new DRACOLoader().setDecoderPath('/draco/');
  const loader = new GLTFLoader().setDRACOLoader(draco);

  const fit = () => {
    const w = el.clientWidth || 1, h = el.clientHeight || 1;
    renderer.setSize(w, h, false);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    if (!camera) return;
    if (control) {
      camera.left = -w / 2; camera.right = w / 2; camera.top = h / 2; camera.bottom = -h / 2;
      opts.onResize?.(w, h);
      camera.updateProjectionMatrix();
      return;
    }
    // Contain: keep the whole HeroCamera frame visible at any aspect.
    const a = w / h;
    let x = base.x, y = base.y;
    if (a > x / y) x = y * a; else y = x / a;
    camera.left = -x; camera.right = x; camera.top = y; camera.bottom = -y;
    camera.updateProjectionMatrix();
  };

  let life: Life | null = null;
  let houseRoot: THREE.Object3D | null = null;
  const view = { onFrame: null, step: null } as Pick<HouseView, 'onFrame' | 'step'>;
  const render = () => {
    if (!camera) return;
    renderer.render(scene, camera);
    view.onFrame?.();
  };

  // ---- the loop: only while there is something to see move
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let onScreen = false;
  let raf = 0;
  let last = 0;
  let stepping = false; // `step` asked for more frames
  const alive = () => !!life && !still && onScreen && !document.hidden && !reduced.matches;
  const moving = () => alive() || (stepping && !!camera && !document.hidden);
  const tick = (now: number) => {
    raf = 0;
    if (!moving()) return;
    raf = requestAnimationFrame(tick);
    const dt = (now - last) / 1000;
    if (dt < 1 / fps - 0.004) return;
    last = now;
    const d = Math.min(dt, 0.1);
    if (alive()) life!.update(d);
    stepping = !!view.step?.(d);
    render();
  };
  const wake = () => {
    if (raf || !moving()) return;
    last = performance.now();
    raf = requestAnimationFrame(tick);
  };
  const io = new IntersectionObserver((entries) => {
    onScreen = entries.some((e) => e.isIntersecting);
    wake();
  });
  io.observe(el);
  document.addEventListener('visibilitychange', wake);
  reduced.addEventListener('change', wake);

  const charGltf = character
    ? loader.loadAsync(character).catch((e) => {
        console.warn('house3d: character failed to load, keeping the static one', e);
        return null;
      })
    : Promise.resolve(null);

  const walkData: Promise<Walks | null> =
    character && walks && !still
      ? fetch(walks)
          .then((r) => (r.ok ? (r.json() as Promise<Walks>) : null))
          .catch(() => null)
      : Promise.resolve(null);

  const ready = Promise.all([loader.loadAsync(url), charGltf, walkData]).then(([gltf, charG, walkG]) => {
    const root = gltf.scene;
    const box = new THREE.Box3();
    root.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) {
        const m = o as THREE.Mesh;
        if (m.name.startsWith('page_surface') || m.parent?.name === 'page_surface') {
          // Like Blender's holdout: invisible, but hides what sits below page level. Lifted 5 mm so it
          // also covers the outer wall tops (1 mm above the page), as in reference/hero_P2.png;
          // otherwise they show as a cream border around the house.
          m.material = new THREE.MeshBasicMaterial({ colorWrite: false, side: THREE.DoubleSide });
          m.renderOrder = -1;
          m.position.y += 0.005;
          return;
        }
        m.castShadow = true;
        m.receiveShadow = true;
        box.expandByObject(m);
      } else if ((o as THREE.DirectionalLight).isDirectionalLight) {
        const s = o as THREE.DirectionalLight;
        s.intensity *= UNITS * light.sun;
        s.castShadow = true;
        s.shadow.mapSize.set(4096, 4096);
        s.shadow.bias = -0.001;
        s.shadow.normalBias = 0.02;
        s.shadow.radius = 4;
      } else if ((o as THREE.PointLight).isPointLight) {
        (o as THREE.PointLight).intensity *= UNITS * light.lamp;
      }
    });
    addProps(root); // pieces not in the GLB yet (props.ts)
    scene.add(root);
    houseRoot = root;
    root.updateMatrixWorld(true);
    if (charG) life = bringToLife(root, charG, walkG);

    // Sun shadow camera: cover the whole house, seen from the sun.
    const suns: THREE.DirectionalLight[] = [];
    root.traverse((o) => { if ((o as THREE.DirectionalLight).isDirectionalLight) suns.push(o as THREE.DirectionalLight); });
    const centre = box.getCenter(new THREE.Vector3());
    const r = box.getSize(new THREE.Vector3()).length() / 2;
    for (const s of suns) {
      // glTF lights shine down their node's -Z; getWorldDirection gives +Z, i.e. toward the sun.
      const toSun = s.getWorldDirection(new THREE.Vector3());
      scene.attach(s);
      scene.add(s.target);
      s.target.position.copy(centre);
      s.position.copy(centre).addScaledVector(toSun, 2 * r);
      const c = s.shadow.camera;
      c.left = -r; c.right = r; c.top = r; c.bottom = -r; c.near = 0.1; c.far = 4 * r;
      c.updateProjectionMatrix();
    }

    const cam = gltf.cameras.find((c) => (c as THREE.OrthographicCamera).isOrthographicCamera) as THREE.OrthographicCamera | undefined;
    if (!cam) throw new Error('house_P2.glb has no orthographic HeroCamera');
    camera = cam;
    base = { x: cam.right, y: cam.top };
    fit();
    if (control) stepping = !!view.step?.(0);
    render();
    wake();
  });

  const ro = new ResizeObserver(() => { fit(); render(); });
  ro.observe(el);

  const v = new THREE.Vector3();
  return Object.assign(view, {
    scene,
    renderer,
    ready,
    render,
    greet(on: boolean) {
      if (!life || still) return;
      const animate = !reduced.matches;
      life.greet(on, animate);
      if (animate) wake();
      else render();
    },
    bubbleAnchor() {
      if (!life || !camera) return null;
      life.bubbleAt(v).project(camera);
      return { x: (v.x * 0.5 + 0.5) * el.clientWidth, y: (-v.y * 0.5 + 0.5) * el.clientHeight };
    },
    kick() {
      if (!camera) return;
      stepping = true;
      if (raf) return;
      if (moving()) wake();
    },
    camera: () => camera,
    heroFrame: () => base,
    house: () => houseRoot,
    excitePet() {
      if (!life || still || reduced.matches) return;
      life.excitePet();
      wake();
    },
    headAt(out: THREE.Vector3) {
      return life ? life.bubbleAt(out) : null;
    },
    dispose() {
      cancelAnimationFrame(raf);
      io.disconnect();
      document.removeEventListener('visibilitychange', wake);
      reduced.removeEventListener('change', wake);
      ro.disconnect();
      draco.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  });
}
