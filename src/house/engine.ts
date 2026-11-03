/**
 * The 3D house, framework-free. Plain three.js keeps the hero under the ~200 KB budget
 * (React Three Fiber pulls in all of three, roughly doubling the download).
 *
 * Renders on demand only: a frame is drawn when something changes (resize, tilt, zoom, rotation,
 * lighting), so an idle house costs nothing, and nothing runs while the tab is hidden.
 *
 * Views: the default view is the sunken cutaway from the art (a depth-only page surface hides
 * everything outside the plan, and the strip of floor behind the near rim). When the view is
 * rotated, the surface and the walls nearest the camera are cut away so every piece of furniture
 * can be seen.
 */
import {
  WebGLRenderer, Scene, OrthographicCamera, Mesh, MeshBasicMaterial, Color, ColorManagement, DoubleSide, BackSide,
  Raycaster, Vector2, Vector3, NoToneMapping, LinearSRGBColorSpace,
} from 'three';
import { LineSegments2 } from 'three/examples/jsm/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/examples/jsm/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js';
import { getRoomBuffers, surfaceGeometry, rimLines, spillGeometry, LINE_WORLD, type Batch } from './geometry';
import { applyCamera, isSunken, type Framing } from './camera';
import { updateOverlay } from './overlay';
import { INK, NIGHT, GLOW, FACE_NORMAL, type Face, type RoomId } from './layout';

// Colours are authored as sRGB hex and must reach the screen unchanged.
ColorManagement.enabled = false;

const ROOMS: RoomId[] = ['studio', 'main', 'lab'];
const DARK_MIX = 0.58; // same as the 2D generator
const SPILL_OPACITY = 115 / 255;

export interface EngineOptions {
  /** Max device pixel ratio. */
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
  silA: LineSegments2;
  silB: LineSegments2;
  walls: Array<{ face: Face; mesh: Mesh; lines: LineSegments2 }>;
}

/** Vertex colours, side faces pick light/dark by screen side, and a uniform mix toward night blue. */
function roomMaterial(dark: { value: number }, right: { value: Vector2 }) {
  const m = new MeshBasicMaterial({ vertexColors: true, side: DoubleSide, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
  m.onBeforeCompile = (shader) => {
    shader.uniforms.uDark = dark;
    shader.uniforms.uNight = { value: new Color(NIGHT) };
    shader.uniforms.uRight = right;
    shader.vertexShader = shader.vertexShader
      .replace('void main() {', 'attribute vec3 color2;\nattribute vec2 sideN;\nuniform vec2 uRight;\nvoid main() {')
      .replace('#include <color_vertex>', '#include <color_vertex>\nif (dot(sideN, uRight) > 0.0) vColor.rgb = color2;');
    shader.fragmentShader = shader.fragmentShader
      .replace('void main() {', 'uniform float uDark;\nuniform vec3 uNight;\nvoid main() {')
      .replace('#include <dithering_fragment>', `gl_FragColor.rgb = mix(gl_FragColor.rgb, uNight, uDark * ${DARK_MIX.toFixed(2)});\n#include <dithering_fragment>`);
  };
  return m;
}

function lines(positions: Float32Array, material: LineMaterial) {
  const g = new LineSegmentsGeometry();
  g.setPositions(positions.length ? positions : new Float32Array(6));
  return new LineSegments2(g, material);
}

export class HouseEngine {
  readonly canvas: HTMLCanvasElement;
  private renderer: WebGLRenderer;
  private scene = new Scene();
  private camera = new OrthographicCamera(-1, 1, 1, -1, 0.1, 400);
  private rooms: Room[] = [];
  private surface: Mesh;
  private rims: Array<{ face: Face; lines: LineSegments2 }> = [];
  private right = { value: new Vector2(1, 0) };
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
  private cur: { zoom: number; target: Vector3; azimuth: number; tilt: number } | null = null;
  private instant = true;
  private speed = 7;
  private firstDone = false;
  private frameWaiters: Array<() => void> = [];
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

    this.surface = new Mesh(surfaceGeometry(), new MeshBasicMaterial({ colorWrite: false, side: DoubleSide }));
    this.surface.renderOrder = -10; // fill depth first so it hides the floor behind the front rim
    this.scene.add(this.surface);
    this.disposables.push(this.surface.geometry, this.surface.material as MeshBasicMaterial);
    for (const [face, pos] of Object.entries(rimLines()) as Array<[Face, Float32Array]>) {
      const l = lines(pos, this.rimMat);
      this.scene.add(l);
      this.rims.push({ face, lines: l });
      this.disposables.push(l.geometry);
    }

    for (const id of ROOMS) {
      const b = buffers[id];
      const dark = { value: 0 };
      const mat = roomMaterial(dark, this.right);
      const mesh = new Mesh(b.base.mesh, mat);
      mesh.userData.room = id;
      const l = lines(b.base.lines, this.lineMat);
      const silA = lines(b.silA, this.lineMat);
      const silB = lines(b.silB, this.lineMat);
      this.scene.add(mesh, l, silA, silB);
      if (b.hull) this.scene.add(new Mesh(b.hull, hullMat));
      const walls = (Object.entries(b.walls) as Array<[Face, Batch]>).map(([face, w]) => {
        const wm = new Mesh(w.mesh, mat);
        wm.userData.room = id;
        const wl = lines(w.lines, this.lineMat);
        this.scene.add(wm, wl);
        this.disposables.push(wl.geometry);
        return { face, mesh: wm, lines: wl };
      });
      const sg = spillGeometry(id);
      const spillMat = new MeshBasicMaterial({ color: new Color(GLOW), transparent: true, opacity: 0, depthWrite: false });
      const spill = sg ? new Mesh(sg, spillMat) : null;
      if (spill) {
        spill.visible = false;
        this.scene.add(spill);
        this.disposables.push(spill.geometry);
      }
      this.disposables.push(mat, spillMat, l.geometry, silA.geometry, silB.geometry);
      this.rooms.push({ id, mesh, dark, goalDark: 0, spill, spillMat, silA, silB, walls });
    }

    // ---- size ----
    this.goal = opts.frame(1, 1);
    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(host);
    this.resize();

    // ---- room clicks (ignored after a drag) ----
    this.canvas.addEventListener('pointerdown', this.onDown);
    this.canvas.addEventListener('click', this.onClick);
    document.addEventListener('visibilitychange', this.onVisibility);
  }

  /** Move the canvas into another element (the hero ↔ the full-screen house) without losing the GL context. */
  setHost(el: HTMLElement) {
    if (el === this.host) return;
    this.ro.unobserve(this.host);
    this.host = el;
    el.appendChild(this.canvas);
    this.ro.observe(el);
    this.resize();
  }

  setRoomClick(fn: EngineOptions['onRoomClick']) {
    this.opts.onRoomClick = fn;
  }

  private onVisibility = () => {
    if (!document.hidden) this.invalidate();
  };

  private onDown = (e: PointerEvent) => {
    this.down = { x: e.clientX, y: e.clientY };
  };

  private onClick = (e: MouseEvent) => {
    if (!this.opts.onRoomClick) return;
    if (this.down && Math.hypot(e.clientX - this.down.x, e.clientY - this.down.y) > 6) return;
    const r = this.canvas.getBoundingClientRect();
    const ndc = new Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    const ray = new Raycaster();
    ray.setFromCamera(ndc, this.camera);
    // furniture and floors, plus the walls you can currently see (cut-away walls don't count)
    const targets = this.rooms.flatMap((x) => [x.mesh, ...x.walls.filter((w) => w.mesh.visible).map((w) => w.mesh)]);
    const hit = ray.intersectObjects(targets, false)[0];
    if (hit) this.opts.onRoomClick(hit.object.userData.room as RoomId);
  };

  private resize() {
    const w = Math.max(1, this.host.clientWidth);
    const h = Math.max(1, this.host.clientHeight);
    if (w === this.width && h === this.height && this.cur) return;
    this.width = w;
    this.height = h;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, this.opts.maxDpr ?? 2));
    this.renderer.setSize(w, h, false);
    this.camera.left = -w / 2;
    this.camera.right = w / 2;
    this.camera.top = h / 2;
    this.camera.bottom = -h / 2;
    this.goal = this.unwrap(this.opts.frame(w, h));
    this.lineMat.resolution.set(w, h);
    this.rimMat.resolution.set(w, h);
    // jump on resize; easing across a resize looks like a glitch
    this.cur = null;
    this.invalidate();
  }

  /** Swap how the camera frames the house. Eases there unless `instant`. `speed` sets the easing rate. */
  setFrame(frame: EngineOptions['frame'], instant = false, speed = 7) {
    this.opts.frame = frame;
    this.goal = this.unwrap(frame(this.width, this.height));
    this.speed = speed;
    if (instant) this.cur = null;
    this.invalidate();
  }

  /** Turn the short way round: put the goal azimuth within half a turn of where the camera is. */
  private unwrap(f: Framing): Framing {
    if (!this.cur) return f;
    const TAU = Math.PI * 2;
    const d = ((((f.azimuth - this.cur.azimuth) % TAU) + TAU + Math.PI) % TAU) - Math.PI;
    return { ...f, azimuth: this.cur.azimuth + d };
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

  /** Resolve after the next frame has been drawn. */
  nextFrame() {
    return new Promise<void>((res) => {
      this.frameWaiters.push(res);
      this.invalidate();
    });
  }

  /** True while the camera is still easing toward its goal. */
  get settling() {
    return this.raf !== 0;
  }

  invalidate() {
    if (!this.raf) this.raf = requestAnimationFrame(this.frame);
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
      this.cur = { zoom: g.zoom, target: g.target.clone(), azimuth: g.azimuth, tilt: this.goalTilt };
    } else {
      const c = this.cur;
      const k = 1 - Math.exp(-dt * this.speed);
      c.zoom = Math.exp(Math.log(c.zoom) + (Math.log(g.zoom) - Math.log(c.zoom)) * k);
      c.target.lerp(g.target, k);
      c.azimuth += (g.azimuth - c.azimuth) * k;
      c.tilt += (this.goalTilt - c.tilt) * k;
      if (
        Math.abs(c.zoom / g.zoom - 1) < 0.001 && c.target.distanceTo(g.target) < 0.002 &&
        Math.abs(c.azimuth - g.azimuth) < 0.0005 && Math.abs(c.tilt - this.goalTilt) < 0.0005
      ) {
        c.zoom = g.zoom;
        c.target.copy(g.target);
        c.azimuth = g.azimuth;
        c.tilt = this.goalTilt;
      } else moving = true;
    }
    const az = this.cur.azimuth + this.cur.tilt;
    applyCamera(this.camera, this.cur.target, this.cur.zoom, az);

    // What's visible from this angle: near walls are cut away; the page surface only in the default view.
    const toCam = [Math.sin(az), Math.cos(az)]; // plan (x, y) direction toward the camera
    const back = (f: Face) => FACE_NORMAL[f][0] * toCam[0] + FACE_NORMAL[f][1] * toCam[1] < 0;
    const sunken = isSunken(az);
    this.surface.visible = sunken;
    for (const r of this.rims) r.lines.visible = sunken || back(r.face);
    const diagA = Math.sin(az) * Math.cos(az) > 0;
    this.right.value.set(Math.cos(az), -Math.sin(az));

    // lines keep a constant world width, so they thicken with zoom like the 2D art
    const px = Math.max(0.75, LINE_WORLD * this.cur.zoom);
    this.lineMat.linewidth = px;
    this.rimMat.linewidth = px * 1.7;

    // lighting + per-room visibility
    const kd = this.instant ? 1 : 1 - Math.exp(-dt * 4);
    for (const r of this.rooms) {
      r.silA.visible = diagA;
      r.silB.visible = !diagA;
      for (const w of r.walls) w.mesh.visible = w.lines.visible = back(w.face);
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
    if (this.frameWaiters.length) {
      const w = this.frameWaiters;
      this.frameWaiters = [];
      requestAnimationFrame(() => w.forEach((f) => f()));
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
