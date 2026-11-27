/**
 * /house: the Pinwheel house, full screen. The whole house first (framed exactly like the poster it
 * fades in over), then zoom into a room from the room switch, a room label or a click on the room;
 * hotspots on the furniture open the content windows. Getting around (the HUD's buttons do all of it too):
 *   - turn: drag (all the way round), Q / E or [ / ] for quarter turns;
 *   - zoom: scroll or trackpad pinch (toward the pointer), pinch on touch, + / -;
 *   - move: right-drag or Shift + drag, two fingers on touch, the arrow keys;
 *   - 0 or the reset button: back to the framed view at the default angle. Changing room resets zoom
 *     and move (not the angle).
 * Deep links: /house?room=living|bedroom|studio|lab
 *
 * Port of src/house/HouseApp.tsx (the old 3-room house) onto src/house3d: viewer.ts draws the GLB with
 * the character and pet (life.ts), stage.ts moves the camera and cuts the walls. The windows, the pins
 * and the styles are the old house's (src/house/Windows.tsx, overlay.ts, house.css).
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { mountHouse, type HouseView as View3D } from './viewer';
import { Stage, type Goal, type Insets } from './stage';
import { ROOMS, ROOM_ORDER, HOTSPOTS, ROOM_DEFAULT, WINDOW_TITLES, type RoomId } from './rooms';
import { useHouse, type View } from './store';
import { track, updateOverlay, setFlipEdge, setVisibleBand } from '../house/overlay';
import { WindowBody, type Deck } from '../house/Windows';
import type { HouseContent } from '../house/content';
import '../house/house.css';
import './house.css';

const TURN_PER_PX = Math.PI / 450; // a drag across 900 px turns the house all the way round
const KEY_PAN = 60; // px per arrow press (Shift: 3x)
const KEY_ZOOM = 1.25;
const reduced = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
const isRoom = (r: string | null): r is RoomId => !!r && r in ROOMS;

/** Space the HUD takes up. The overview (and the poster on /house) frames inside this. */
export function overviewInsets(w: number): Insets {
  return w >= 900 ? { top: 96, right: 32, bottom: 72, left: 32 } : { top: 136, right: 16, bottom: 32, left: 16 };
}

/** The open window's size on screen, measured as it changes, so the room frames in what it leaves. */
const windowBox = { w: 0, h: 0 };

/** Space the HUD and the open window take up, so a zoomed room centres in what's left. */
function insetsFor(view: View, item: string | null) {
  return (w: number, h: number): Insets => {
    const base = overviewInsets(w);
    if (view === 'overview' || !item) return base;
    // desktop: the window on the right (plus its margin and a gap); smaller: the sheet or card at the bottom
    return w >= 900
      ? { ...base, right: (windowBox.w || Math.min(440, w * 0.42)) + 48 }
      : { ...base, bottom: (windowBox.h || Math.round(h * 0.55)) + 16 };
  };
}

function goalFor(view: View, item: string | null, rot: number, tilt: number, poster = false): Goal {
  const insets = insetsFor(view, item);
  if (view !== 'overview') return { kind: 'room', room: view, rot, tilt, insets, overviewInsets: (w) => overviewInsets(w) };
  // On a phone the whole house is too small to read; start closer, on the living room.
  const phone = !poster && typeof innerWidth !== 'undefined' && innerWidth < 600;
  return { kind: 'overview', rot, tilt, insets, phoneRoom: phone ? 'living' : undefined };
}

function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch {
    return false;
  }
}

/** A DOM element pinned to a point in the house. */
function Pin({ stage, anchor, className, children, hidden, clamp }: { stage: Stage; anchor: string; className: string; children: React.ReactNode; hidden?: boolean; clamp?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const at = stage.anchors.get(anchor);
    return ref.current && at ? track(ref.current, at) : undefined;
  }, [stage, anchor]);
  return (
    <div ref={ref} className={`hx-pin ${className}`} hidden={hidden} data-clamp={clamp ? '1' : undefined}>
      {children}
    </div>
  );
}

function Hearts() {
  return (
    <span className="hx-hearts" aria-hidden="true">
      <span>♥</span><span>♥</span><span>♥</span>
    </span>
  );
}

export default function HouseView({ content }: { content: HouseContent }) {
  const view = useHouse((s) => s.view);
  const item = useHouse((s) => s.item);
  const go = useHouse((s) => s.go);
  const close = useHouse((s) => s.close);
  const tilt = useHouse((s) => s.tilt);
  const spin = useHouse((s) => s.spin);
  const rot = useHouse((s) => s.rot);
  const rotate = useHouse((s) => s.rotate);
  const record = useHouse((s) => s.record);
  const sound = useHouse((s) => s.sound);
  const [gl, setGl] = useState<boolean | null>(null);
  const [ready, setReady] = useState(false);
  const [petted, setPetted] = useState(0);
  const [moved, setMoved] = useState(false); // zoomed or panned away from the framed view
  const [stage] = useState(() => new Stage());
  const house = useRef<View3D | null>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const windowRef = useRef<HTMLElement>(null);
  const lastHotspot = useRef<HTMLElement | null>(null);
  const records = content.records;
  const hasAudio = records.some((r) => r.src);

  // Deep link in.
  useEffect(() => {
    setGl(webglAvailable());
    const q = new URLSearchParams(location.search).get('room');
    const room = q === 'main' ? 'living' : q; // the old house's name for the living room
    if (isRoom(room)) go(room, ROOM_DEFAULT[room]);
  }, [go]);

  // The scene: poster framing first, then the view asked for.
  useEffect(() => {
    if (!gl || !stageRef.current) return;
    const v = mountHouse(stageRef.current, { control: true, fps: 60, grid: true, onResize: (w, h) => stage.resize(w, h) });
    house.current = v;
    stage.attach(v);
    stage.setInstant(reduced());
    stage.onUserChange = setMoved;
    stage.onFrame = (cam, w, h) => updateOverlay(cam, w, h);
    if (import.meta.env.DEV) (window as any).__house = { view: v, stage };
    stage.go(goalFor('overview', null, 0, 0, true), true);
    let wave = 0;
    v.ready.then(
      () => {
        setReady(true);
        const now = useHouse.getState();
        stage.go(goalFor(now.view, now.item, now.rot, now.tilt));
        // say hello on the way in
        if (now.view === 'overview' && !reduced()) {
          v.greet(true);
          wave = window.setTimeout(() => v.greet(false), 2600);
        }
      },
      (e) => console.error('house: failed to load', e),
    );
    return () => {
      clearTimeout(wave);
      v.dispose();
      house.current = null;
    };
  }, [gl, stage]);

  // Keep the camera in step with the store.
  useEffect(() => {
    const w = innerWidth, h = innerHeight;
    const ins = insetsFor(view, item)(w, h);
    // labels open away from the window (desktop) and the screen's edges
    setFlipEdge(w - ins.right);
    // pins that slide under the HUD bar or the window can't be clicked, so hide them
    setVisibleBand(overviewInsets(w).top - 16, w >= 900 || view === 'overview' || !item ? h : h - ins.bottom);
    if (ready) stage.go(goalFor(view, item, rot, tilt));
  }, [view, item, rot, tilt, ready, stage]);

  // A new room (or back to the whole house) starts framed.
  useEffect(() => stage.resetView(), [view, stage]);

  // Keep the URL in sync so a room can be shared.
  useEffect(() => {
    const url = new URL(location.href);
    if (view === 'overview') url.searchParams.delete('room');
    else url.searchParams.set('room', view);
    history.replaceState(history.state, '', url);
  }, [view]);

  // Keys: Q / E turn, Escape closes the window, then steps back out to the whole house.
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      const s = useHouse.getState();
      const typing = (e.target as HTMLElement)?.closest?.('input, textarea, [contenteditable]');
      const inWindow = (e.target as HTMLElement)?.closest?.('.hx-window');
      if (!typing && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const k = e.key.toLowerCase();
        if (k === 'q' || k === '[') return s.rotate(-1);
        if (k === 'e' || k === ']') return s.rotate(1);
        if (k === '+' || k === '=') return stage.zoomBy(KEY_ZOOM);
        if (k === '-' || k === '_') return stage.zoomBy(1 / KEY_ZOOM);
        if (k === '0') {
          stage.resetView();
          return s.unturn();
        }
        // arrows move the view, unless they're scrolling the open window
        const arrow = ({ arrowleft: [1, 0], arrowright: [-1, 0], arrowup: [0, 1], arrowdown: [0, -1] } as Record<string, number[]>)[k];
        if (arrow && !inWindow) {
          e.preventDefault();
          const d = KEY_PAN * (e.shiftKey ? 3 : 1);
          return stage.panBy(arrow[0] * d, arrow[1] * d);
        }
      }
      if (e.key !== 'Escape') return;
      if (s.item) {
        s.close();
        lastHotspot.current?.focus();
      } else if (s.view !== 'overview') s.go('overview');
    };
    addEventListener('keydown', key);
    return () => removeEventListener('keydown', key);
  }, [stage]);

  // Measure the open window (it fits its content), and reframe the room around it.
  useEffect(() => {
    const el = windowRef.current;
    if (!item || !el) {
      windowBox.w = windowBox.h = 0;
      return;
    }
    const ro = new ResizeObserver(() => {
      const r = el.getBoundingClientRect();
      windowBox.w = r.width;
      windowBox.h = innerHeight - r.top; // from its top edge to the bottom of the screen
      const ins = insetsFor(useHouse.getState().view, item)(innerWidth, innerHeight);
      setFlipEdge(innerWidth - ins.right);
      setVisibleBand(overviewInsets(innerWidth).top - 16, innerWidth >= 900 ? innerHeight : innerHeight - ins.bottom);
      house.current?.kick();
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [item]);

  // Move focus into a newly opened window.
  useEffect(() => {
    if (item) windowRef.current?.querySelector<HTMLElement>('h2')?.focus();
  }, [item]);

  // Pointers on the house. One (mouse, pen, a finger): drag to turn; right-drag or Shift + drag to move.
  // Two fingers: pinch to zoom, move them together to pan. A click without a drag walks into the room
  // under the pointer.
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const drag = useRef<{ x: number; y: number; moved: boolean; pan: boolean; multi: boolean } | null>(null);
  const pinch = useRef<{ d: number; x: number; y: number } | null>(null);
  const local = (e: { clientX: number; clientY: number }) => {
    const r = stageRef.current!.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };
  const twoFingers = () => {
    const [a, b] = [...pointers.current.values()];
    return { d: Math.hypot(a.x - b.x, a.y - b.y), x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  };
  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (e.pointerType === 'mouse' && e.button !== 0 && e.button !== 2) return;
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); // keep the drag when it leaves the canvas
    } catch {
      /* not an active pointer (synthetic events) */
    }
    pointers.current.set(e.pointerId, local(e));
    if (pointers.current.size === 2) {
      pinch.current = twoFingers();
      if (drag.current) drag.current.multi = true; // no click once a second finger lands
    } else if (pointers.current.size === 1) {
      drag.current = { x: e.clientX, y: e.clientY, moved: false, pan: e.button === 2 || e.shiftKey, multi: false };
    }
  }, []);
  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      const prev = pointers.current.get(e.pointerId);
      if (!prev) return;
      const now = local(e);
      pointers.current.set(e.pointerId, now);
      if (pointers.current.size >= 2 && pinch.current) {
        const p = twoFingers(), q = pinch.current;
        stage.setDragging(true);
        if (q.d > 0 && p.d > 0) stage.zoomBy(p.d / q.d, p.x, p.y);
        stage.panBy(p.x - q.x, p.y - q.y);
        pinch.current = p;
        return;
      }
      const d = drag.current;
      if (!d) return;
      if (!d.moved && Math.abs(e.clientX - d.x) + Math.abs(e.clientY - d.y) > 6) d.moved = true;
      if (!d.moved) return;
      stage.setDragging(true);
      if (d.pan || e.shiftKey) stage.panBy(now.x - prev.x, now.y - prev.y);
      else spin(-(now.x - prev.x) * TURN_PER_PX);
    },
    [spin, stage],
  );
  const release = (e: React.PointerEvent) => {
    pointers.current.delete(e.pointerId);
    if (pointers.current.size < 2) pinch.current = null;
    if (pointers.current.size) return null;
    stage.setDragging(false);
    const d = drag.current;
    drag.current = null;
    return d;
  };
  const onPointerUp = useCallback(
    (e: React.PointerEvent) => {
      const had = pointers.current.has(e.pointerId);
      const d = release(e);
      if (!had || !d || d.moved || d.multi || d.pan || e.button !== 0) return;
      const p = local(e);
      const room = stage.roomAt(p.x, p.y);
      const s = useHouse.getState();
      if (room && room !== s.view) s.go(room, ROOM_DEFAULT[room]);
    },
    [stage],
  );
  const endDrag = useCallback((e: React.PointerEvent) => void release(e), [stage]);

  // Scroll (and trackpad pinch, which comes as ctrl + wheel) zooms toward the pointer.
  useEffect(() => {
    const el = stageRef.current?.parentElement;
    if (!el) return;
    const wheel = (e: WheelEvent) => {
      if ((e.target as HTMLElement).closest('.hx-window, .hx-top, .hx-now, .hx-turn')) return;
      e.preventDefault();
      const px = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaMode === 2 ? e.deltaY * 400 : e.deltaY;
      const f = Math.exp(-Math.max(-120, Math.min(120, px)) * (e.ctrlKey ? 0.01 : 0.002));
      const p = local(e);
      stage.zoomBy(f, p.x, p.y);
    };
    el.addEventListener('wheel', wheel, { passive: false });
    return () => el.removeEventListener('wheel', wheel);
  }, [gl, stage]);

  const here: RoomId = view === 'overview' ? 'living' : view;
  const crumb = view === 'overview' ? null : ROOMS[view].label;

  // ---- click-to-task ----
  const pickRecord = (i: number) => useHouse.getState().setRecord(i);
  const nextRecord = () => pickRecord((useHouse.getState().record + 1) % records.length);
  const deck: Deck = { record, state: 'playing', pick: pickRecord };

  const openHotspot = (id: string, room: RoomId, el: HTMLElement) => {
    lastHotspot.current = el;
    switch (id) {
      // click-to-task: he comes over (life.ts ask); the pet and the sofa open no window
      case 'pet':
        house.current?.excitePet();
        house.current?.ask('pet');
        return setPetted((n) => n + 1);
      case 'sofa':
        house.current?.ask('sofa');
        return;
      case 'turntable':
        nextRecord();
        house.current?.ask('turntable');
        break;
      case 'arcade':
        house.current?.ask('arcade');
        break;
      case 'window': {
        // he waves when you ask about him
        const v = house.current;
        if (v && !reduced()) {
          v.greet(true);
          setTimeout(() => v.greet(false), 2200);
        }
        break;
      }
    }
    go(room, id);
  };

  // Optional music: only if the owner has added audio files to the records.
  const audio = useRef<HTMLAudioElement | null>(null);
  useEffect(() => {
    const src = records[record]?.src;
    if (!sound || !src) {
      audio.current?.pause();
      return;
    }
    audio.current ??= new Audio();
    const a = audio.current;
    a.loop = true;
    if (!a.src.endsWith(src)) a.src = src;
    a.play().catch(() => {});
  }, [sound, record, records]);
  useEffect(() => () => audio.current?.pause(), []);

  if (gl === false) {
    return (
      <div className="hx-fallback">
        <p>This browser can't draw the 3D house. The short tour has everything:</p>
        <ul className="hx-links">
          <li><a href="/#work">The studio · work</a></li>
          <li><a href="/#lab">The lab · side projects</a></li>
          <li><a href="/#about">The living room · about me</a></li>
        </ul>
      </div>
    );
  }

  return (
    <div className={`hx hx2${ready ? ' is-ready' : ''}`} data-view={view}>
      <div
        ref={stageRef}
        className="hx-stage"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={endDrag}
        onLostPointerCapture={endDrag}
        onContextMenu={(e) => e.preventDefault()}
      />

      {/* Hotspots and labels, pinned to the scene */}
      <div className="hx-overlay">
        {ROOM_ORDER.filter((r) => r !== here).map((r) => (
          <Pin key={r} stage={stage} anchor={`room:${r}`} className="hx-roomlabel" hidden={view !== 'overview'} clamp>
            <button type="button" onClick={() => go(r, ROOM_DEFAULT[r])}>
              <span className="hx-roomlabel-name">{ROOMS[r].label}</span>
              <span className="hx-roomlabel-sub">{ROOMS[r].sub}</span>
            </button>
          </Pin>
        ))}
        {HOTSPOTS.map((h) => (
          <Pin
            key={h.id}
            stage={stage}
            anchor={h.id}
            className={`hx-hotspot${item === h.id ? ' is-open' : ''}`}
            hidden={!ready || (h.room !== here && !h.everywhere) || !stage.wallShown(stage.walls.get(h.id), rot)}
          >
            <button type="button" onClick={(e) => openHotspot(h.id, h.room, e.currentTarget)} aria-expanded={h.inline ? undefined : item === h.id}>
              <span className="hx-dot" aria-hidden="true" />
              <span className="hx-hotspot-label">{h.label}</span>
            </button>
            {h.id === 'pet' && petted > 0 && <Hearts key={petted} />}
          </Pin>
        ))}
        <Pin stage={stage} anchor="me" className="hx-bubble" hidden={!ready || view !== 'overview' || item !== null}>
          <p>Hi, I'm {content.site.name}. Make yourself at home. My work is in the studio.</p>
        </Pin>
      </div>

      <header className="hx-top">
        <div className="hx-top-start">
          <a className="hx-exit" href="/">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M19 12H5" /><path d="m11 18-6-6 6-6" /></svg>
            Exit house
          </a>
          <span className="hx-crumb">
            {crumb ? (
              <>
                <button type="button" onClick={() => go('overview')}>House</button> / <strong>{crumb}</strong>
              </>
            ) : (
              <strong>House</strong>
            )}
          </span>
        </div>
        <nav className="hx-rooms" aria-label="Rooms">
          <button type="button" aria-current={view === 'overview' ? 'true' : undefined} onClick={() => go('overview')}>
            House
          </button>
          {ROOM_ORDER.map((r) => (
            <button key={r} type="button" aria-current={view === r ? 'true' : undefined} onClick={() => go(r, ROOM_DEFAULT[r])}>
              {ROOMS[r].short}
            </button>
          ))}
        </nav>
      </header>

      {records.length > 0 && (
        <div className="hx-now" aria-live="polite">
          <span className="hx-now-disc is-spinning" style={{ ['--label' as string]: records[record]?.label }} aria-hidden="true" />
          <span className="hx-now-text">
            <strong>{records[record]?.title}</strong>
            <span className="hx-muted">{records[record]?.artist} · on the turntable</span>
          </span>
          <button type="button" className="hx-now-next" onClick={nextRecord} aria-label="Next record">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M5 4l10 8-10 8V4z" /><path d="M17 4h3v16h-3z" /></svg>
          </button>
          {hasAudio && (
            <button type="button" className="hx-now-next" onClick={() => useHouse.getState().setSound(!sound)} aria-pressed={sound} aria-label={sound ? 'Sound off' : 'Sound on'}>
              {sound ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M11 5 6 9H2v6h4l5 4V5z" /><path d="M15.5 8.5a5 5 0 0 1 0 7" /><path d="M19 5a10 10 0 0 1 0 14" /></svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M11 5 6 9H2v6h4l5 4V5z" /><path d="m22 9-6 6" /><path d="m16 9 6 6" /></svg>
              )}
            </button>
          )}
        </div>
      )}

      <p className="hx-hint">
        {view === 'overview' ? '' : 'Esc to step back · '}Drag to turn · scroll to zoom · right-drag to move
      </p>

      <div className="hx-turn" role="toolbar" aria-label="Camera">
        <button type="button" onClick={() => stage.zoomBy(1 / KEY_ZOOM)} aria-label="Zoom out (minus)" title="Zoom out (−)">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M5 12h14" /></svg>
        </button>
        <button type="button" onClick={() => stage.zoomBy(KEY_ZOOM)} aria-label="Zoom in (plus)" title="Zoom in (+)">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M5 12h14" /><path d="M12 5v14" /></svg>
        </button>
        <span className="hx-turn-sep" aria-hidden="true" />
        <button type="button" onClick={() => rotate(-1)} aria-label="Rotate left (Q)" title="Rotate left (Q)">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 4v5h5" /></svg>
        </button>
        <span className="hx-turn-dots" aria-live="polite">
          <span className="sr-only">View {(((rot % 4) + 4) % 4) + 1} of 4</span>
          {[0, 1, 2, 3].map((i) => (
            <span key={i} aria-hidden="true" className={(((rot % 4) + 4) % 4) === i ? 'on' : ''} />
          ))}
        </span>
        <button type="button" onClick={() => rotate(1)} aria-label="Rotate right (E)" title="Rotate right (E)">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 1 1-3-6.7" /><path d="M21 4v5h-5" /></svg>
        </button>
        <span className="hx-turn-sep" aria-hidden="true" />
        <button
          type="button"
          onClick={() => {
            stage.resetView();
            useHouse.getState().unturn();
          }}
          disabled={!moved && !tilt && rot % 4 === 0}
          aria-label="Reset view (0)"
          title="Reset view (0)"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 9V4h5" /><path d="M20 9V4h-5" /><path d="M4 15v5h5" /><path d="M20 15v5h-5" /></svg>
        </button>
      </div>

      {item && WINDOW_TITLES[item] && (
        <aside ref={windowRef} className="hx-window" aria-labelledby="hx-window-title">
          <div className="hx-window-bar">
            <span className="hx-lights">
              <button
                type="button"
                className="hx-close"
                aria-label="Close window"
                onClick={() => {
                  close();
                  lastHotspot.current?.focus();
                }}
              />
              <i aria-hidden="true" />
              <i aria-hidden="true" />
            </span>
            <h2 id="hx-window-title" tabIndex={-1}>{WINDOW_TITLES[item]}</h2>
          </div>
          <div className="hx-window-body" key={item}>
            <WindowBody id={item} content={content} deck={deck} />
          </div>
        </aside>
      )}
    </div>
  );
}
