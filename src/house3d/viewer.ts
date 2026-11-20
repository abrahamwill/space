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
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';

const UNITS = 1 / (683 * Math.PI);

// Tuned against house3d/reference/hero_P2.png: mean error 25.6, brightness +0.2
// (the Blender render scores 21.3 / +1.7). Shadowed areas need more ambient here because
// three.js has no AO or light bounce to lift them.
export const LIGHT = {
  sun: 2.2,      // × the exported Sun (Blender strength 2.5)
  ambient: 1.1,  // grey world light (Blender world strength 0.32)
  lamp: 1,       // × the exported lamp lights (Blender 12 W)
};

export interface HouseView {
  scene: THREE.Scene;
  renderer: THREE.WebGLRenderer;
  ready: Promise<void>;
  render(): void;
  dispose(): void;
}

export function mountHouse(el: HTMLElement, url = '/house3d/house_P2.glb', light = LIGHT): HouseView {
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
    // Contain: keep the whole HeroCamera frame visible at any aspect.
    const a = w / h;
    let x = base.x, y = base.y;
    if (a > x / y) x = y * a; else y = x / a;
    camera.left = -x; camera.right = x; camera.top = y; camera.bottom = -y;
    camera.updateProjectionMatrix();
  };

  const render = () => { if (camera) renderer.render(scene, camera); };

  const ready = loader.loadAsync(url).then((gltf) => {
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
    scene.add(root);
    root.updateMatrixWorld(true);

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
    render();
  });

  const ro = new ResizeObserver(() => { fit(); render(); });
  ro.observe(el);

  return {
    scene,
    renderer,
    ready,
    render,
    dispose() {
      ro.disconnect();
      draco.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}
