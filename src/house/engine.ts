/**
 * The 3D house, framework-free. Plain three.js keeps the hero under the ~200 KB budget
 * (React Three Fiber pulls in all of three, roughly doubling the download).
 *
 * Renders on demand only: a frame is drawn when something changes (resize, tilt, zoom, lighting),
 * so an idle house costs nothing, and nothing runs while the tab is hidden.
 */
import {
  WebGLRenderer, Scene, OrthographicCamera, Mesh, MeshBasicMaterial,
  Color, ColorManagement, DoubleSide, BackSide, Raycaster, Vector2, Vector3, NoToneMapping, LinearSRGBColorSpace,
} from 'three';
import { LineSegments2 } from 'three/examples/jsm/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/examples/jsm/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js';
import { getRoomBuffers, surfaceGeometry, rimLine, spillGeometry, LINE_WORLD } from './geometry';
import { applyCamera, type Framing } from './camera';
import { updateOverlay } from './overlay';
import { INK, NIGHT, GLOW, type RoomId } from './layout';

// Colours are authored as sRGB hex and must reach the screen unchanged.
ColorManagement.enabled = false;

const ROOMS: RoomId[] = ['studio', 'main', 'lab'];
const DARK_MIX = 0.58; // same as the 2D generator
const SPILL_OPACITY = 115 / 255;

export interface EngineOptions {
  /** Max device pixel ratio. Lower for the hero. */
  maxDpr?: number;
  /** Compute the camera goal for a given canvas size (CSS px). */
  frame: (width: number, height: number) => Framing;
  onRoomClick?: (room: RoomId) => void;
  /** Called once, after the first frame is on screen. */
  onFirstFrame?: () => void;
  preserveDrawingBuffer?: boolean;
}

interface Room {
  id: RoomId;
  mesh: Mesh;
  dark: { value: number };
  goalDark: number;
  spill: Mesh | null;
  spillMat: MeshBasicMaterial;
}

function roomMaterial(dark: { value: number }) {
  const m = new MeshBasicMaterial({ vertexColors: true, side: DoubleSide, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
  m.onBeforeCompile = (shader) => {
    shader.uniforms.uDark = dark;
    shader.uniforms.uNight = { value: new Color(NIGHT) };
    shader.fragmentShader = shader.fragmentShader
      .replace('void main() {', 'uniform float uDark;\nuniform vec3 uNight;\nvoid main() {')
      .replace('#include <dithering_fragment>', `gl_FragColor.rgb = mix(gl_FragColor.rgb, uNight, uDark * ${DARK_MIX.toFixed(2)});\n#include <dithering_fragment>`);
  };
  return m;
}

function lines(positions: Float32Array, material: LineMaterial) {
  const g = new LineSegmentsGeometry();
  g.setPositions(positions);
  return new LineSegments2(g, material);
}

export class HouseEngine {
  readonly canvas: HTMLCanvasElement;
  private renderer: WebGLRenderer;
  private scene = new Scene();
  private camera = new OrthographicCamera(-1, 1, 1, -1, 0.1, 400);
  private rooms: Room[] = [];
  private lineMat: LineMaterial;
  private rimMat: LineMaterial;
  private disposables: Array<{ dispose(): void }> = [];
  private ro: ResizeObserver;
  private raf = 0;
  private last = 0;
  private width = 1;
  private height = 1;
  private goal: Framing;
  private goalTilt = 0;
  private cur: { zoom: number; target: Vector3; tilt: number } | null = null;
  private instant = true;
  private firstDone = false;
  private down: { x: number; y: number } | null = null;

  constructor(private host: HTMLElement, private opts: EngineOptions) {
    this.renderer = new WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'low-power',
      preserveDrawingBuffer: !!opts.preserveDrawingBuffer,
    });
    this.renderer.outputColorSpace = LinearSRGBColorSpace; // no conversion: hex in, hex out
    this.renderer.toneMapping = NoToneMapping;
    this.renderer.setClearColor(0x000000, 0);
    this.canvas = this.renderer.domElement;
    this.canvas.style.display = 'block';
    this.canvas.style.width = '100%';
    this.canvas.style.height = '100%';
    this.canvas.setAttribute('aria-hidden', 'true');
    host.appendChild(this.canvas);

    // ---- build the scene ----
    const buffers = getRoomBuffers();
    const ink = new Color(INK);
    this.lineMat = new LineMaterial({ color: ink.getHex(), linewidth: 1 });
    this.rimMat = new LineMaterial({ color: ink.getHex(), linewidth: 1.7 });
    const hullMat = new MeshBasicMaterial({ color: ink, side: BackSide });
    this.disposables.push(this.lineMat, this.rimMat, hullMat);

    const surface = new Mesh(surfaceGeometry(), new MeshBasicMaterial({ colorWrite: false, side: DoubleSide }));
    surface.renderOrder = -10; // fill depth first so it hides the floor behind the front rim
    this.scene.add(surface);
    const rim = lines(rimLine(), this.rimMat);
    this.scene.add(rim);
    this.disposables.push(surface.geometry, surface.material as MeshBasicMaterial, rim.geometry);

    for (const id of ROOMS) {
      const b = buffers[id];
      const dark = { value: 0 };
      const mat = roomMaterial(dark);
      const mesh = new Mesh(b.mesh, mat);
      mesh.userData.room = id;
      this.scene.add(mesh);
      const l = lines(b.lines, this.lineMat);
      this.scene.add(l);
      if (b.hull) this.scene.add(new Mesh(b.hull, hullMat));
      const sg = spillGeometry(id);
      const spillMat = new MeshBasicMaterial({ color: new Color(GLOW), transparent: true, opacity: 0, depthWrite: false });
      const spill = sg ? new Mesh(sg, spillMat) : null;
      if (spill) {
        spill.visible = false;
        this.scene.add(spill);
        this.disposables.push(spill.geometry);
      }
      this.disposables.push(mat, spillMat, l.geometry);
      this.rooms.push({ id, mesh, dark, goalDark: 0, spill, spillMat });
    }

    // ---- size ----
    this.goal = opts.frame(1, 1);
    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(host);
    this.resize();

    // ---- room clicks (ignored after a drag) ----
    if (opts.onRoomClick) {
      this.canvas.addEventListener('pointerdown', this.onDown);
      this.canvas.addEventListener('click', this.onClick);
    }
    document.addEventListener('visibilitychange', this.onVisibility);
  }

  private onVisibility = () => {
    if (!document.hidden) this.invalidate();
  };

  private onDown = (e: PointerEvent) => {
    this.down = { x: e.clientX, y: e.clientY };
  };

  private onClick = (e: MouseEvent) => {
    if (this.down && Math.hypot(e.clientX - this.down.x, e.clientY - this.down.y) > 6) return;
    const r = this.canvas.getBoundingClientRect();
    const ndc = new Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    const ray = new Raycaster();
    ray.setFromCamera(ndc, this.camera);
    const hit = ray.intersectObjects(this.rooms.map((x) => x.mesh), false)[0];
    if (hit) this.opts.onRoomClick?.(hit.object.userData.room as RoomId);
  };

  private resize() {
    const w = Math.max(1, this.host.clientWidth);
    const h = Math.max(1, this.host.clientHeight);
    this.width = w;
    this.height = h;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, this.opts.maxDpr ?? 2));
    this.renderer.setSize(w, h, false);
    this.camera.left = -w / 2;
    this.camera.right = w / 2;
    this.camera.top = h / 2;
    this.camera.bottom = -h / 2;
    this.goal = this.opts.frame(w, h);
    this.lineMat.resolution.set(w, h);
    this.rimMat.resolution.set(w, h);
    // jump on resize; easing across a resize looks like a glitch
    this.cur = null;
    this.invalidate();
  }

  /** Recompute the camera goal (e.g. the view changed). Eases unless `instant`. */
  reframe(instant = false) {
    this.goal = this.opts.frame(this.width, this.height);
    if (instant) this.cur = null;
    this.invalidate();
  }

  setFrame(frame: EngineOptions['frame'], instant = false) {
    this.opts.frame = frame;
    this.reframe(instant);
  }

  setTilt(t: number) {
    this.goalTilt = t;
    this.invalidate();
  }

  setLit(lit: Record<RoomId, boolean>, instant = false) {
    for (const r of this.rooms) {
      r.goalDark = lit[r.id] ? 0 : 1;
      if (instant) r.dark.value = r.goalDark;
    }
    this.invalidate();
  }

  /** After the first frame, ease camera moves and light changes (unless reduced motion). */
  setInstant(v: boolean) {
    this.instant = v;
  }

  invalidate() {
    if (!this.raf) {
      this.raf = requestAnimationFrame(this.frame);
    }
  }

  private frame = (now: number) => {
    this.raf = 0;
    if (document.hidden) return;
    const dt = this.last ? Math.min((now - this.last) / 1000, 0.05) : 1 / 60;
    this.last = now;
    let moving = false;

    // camera
    const g = this.goal;
    if (!this.cur || this.instant) {
      this.cur = { zoom: g.zoom, target: g.target.clone(), tilt: this.goalTilt };
    } else {
      const c = this.cur;
      const k = 1 - Math.exp(-dt * 7);
      c.zoom = Math.exp(Math.log(c.zoom) + (Math.log(g.zoom) - Math.log(c.zoom)) * k);
      c.target.lerp(g.target, k);
      c.tilt += (this.goalTilt - c.tilt) * k;
      if (Math.abs(c.zoom / g.zoom - 1) < 0.001 && c.target.distanceTo(g.target) < 0.002 && Math.abs(c.tilt - this.goalTilt) < 0.0005) {
        c.zoom = g.zoom;
        c.target.copy(g.target);
        c.tilt = this.goalTilt;
      } else moving = true;
    }
    applyCamera(this.camera, this.cur.target, this.cur.zoom, this.cur.tilt);

    // lines keep a constant world width, so they thicken with zoom like the 2D art
    const px = Math.max(0.75, LINE_WORLD * this.cur.zoom);
    this.lineMat.linewidth = px;
    this.rimMat.linewidth = px * 1.7;

    // lighting
    const kd = this.instant ? 1 : 1 - Math.exp(-dt * 4);
    for (const r of this.rooms) {
      const d = r.dark;
      d.value += (r.goalDark - d.value) * kd;
      if (Math.abs(r.goalDark - d.value) < 0.002) d.value = r.goalDark;
      else moving = true;
      r.spillMat.opacity = SPILL_OPACITY * d.value;
      if (r.spill) r.spill.visible = d.value > 0.001;
    }

    this.renderer.render(this.scene, this.camera);
    updateOverlay(this.camera, this.width, this.height);

    if (moving) this.invalidate();
    else this.last = 0;
    if (!this.firstDone) {
      this.firstDone = true;
      requestAnimationFrame(() => this.opts.onFirstFrame?.());
    }
  };

  dispose() {
    cancelAnimationFrame(this.raf);
    this.ro.disconnect();
    document.removeEventListener('visibilitychange', this.onVisibility);
    this.canvas.removeEventListener('pointerdown', this.onDown);
    this.canvas.removeEventListener('click', this.onClick);
    this.disposables.forEach((d) => d.dispose());
    this.renderer.dispose();
    this.canvas.remove();
  }
}

export function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch {
    return false;
  }
}
