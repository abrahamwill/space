/**
 * The house view: the whole house, zoom between rooms, windows over the zoomed room, rotate in
 * 90° steps. Rooms light up as you visit them. Deep links: /house?room=studio|lab|main
 *
 * Runs standalone on /house, or embedded on the home page, where it takes over the hero's engine
 * (see enter.ts) so entering the house is one continuous camera move.
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { HouseEngine, webglAvailable } from './engine';
import { fitHouse, fitRoom, azimuthFor, type Insets } from './camera';
import { toWorld } from './geometry';
import { track, setFlipEdge, setVisibleBand } from './overlay';
import { LIVE } from './actors';
import { ANCHORS, ROOMS, FACE_NORMAL, type AnchorId, type Face, type RoomId } from './layout';
import { useHouse, isLit, type View } from './store';
import { HOTSPOTS, ROOM_DEFAULT, type HouseContent } from './content';
import { WindowBody, WINDOW_TITLES } from './Windows';
import './house.css';

const MAX_TILT = (15 * Math.PI) / 180;
const ROOM_ORDER: RoomId[] = ['main', 'studio', 'lab'];
const reduced = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Space the HUD takes up. The overview frames inside this. */
function overviewInsets(w: number): Insets {
  const wide = w >= 900;
  return { top: wide ? 96 : 136, right: 32, bottom: wide ? 72 : 32, left: 32 };
}

/** Space the HUD and the open window take up, so a zoomed room centres in what's left. */
function insetsFor(view: View, item: string | null, w: number, h: number): Insets {
  const wide = w >= 900;
  const base = overviewInsets(w);
  if (view === 'overview' || !item) return base;
  return wide ? { ...base, right: Math.min(460, w * 0.42) + 32 } : { ...base, bottom: Math.round(h * 0.55) };
}

/** Camera goal for the current view: whole house, or a room at ~2.1× centred in the free space. */
function frameFor(view: View, item: string | null, rot: number) {
  return (w: number, h: number) => {
    const ins = insetsFor(view, item, w, h);
    // labels flip side before they'd run under the window (desktop) or off the right edge
    setFlipEdge(w - ins.right - 200);
    // pins that slide under the HUD bar or the window can't be clicked, so hide them
    setVisibleBand(overviewInsets(w).top - 16, w >= 900 || view === 'overview' || !item ? h : h - ins.bottom);
    // Room zoom is relative to the whole-house fit, so opening a window pans but doesn't change the zoom.
    const whole = fitHouse(w, h, overviewInsets(w), azimuthFor(rot));
    if (view !== 'overview') return fitRoom(whole, ROOMS[view].centre, ins, ROOMS[view].zoom);
    // On a phone the whole house is too small to read; start closer, on the main room.
    if (w < 600) return fitRoom(whole, 'c_main', ins, 2);
    return whole;
  };
}

/** A DOM element pinned to a point in the house. */
function Pin({ anchor, className, children, hidden, clamp }: { anchor: AnchorId; className: string; children: React.ReactNode; hidden?: boolean; clamp?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  // the character and the pet move, so their pins follow live positions
  useLayoutEffect(
    () => (ref.current ? track(ref.current, anchor in LIVE ? LIVE[anchor as keyof typeof LIVE] : toWorld(ANCHORS[anchor])) : undefined),
    [anchor],
  );
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

interface Props {
  content: HouseContent;
  /** Embedded on the home page: reuse this engine instead of creating one. */
  engine?: HouseEngine;
  /** Embedded: leave the house without a page load. */
  onExit?: () => void;
  /** Embedded: fading out while the camera zooms back to the hero. */
  leaving?: boolean;
}

export const ENTER_SPEED = 4.5; // camera easing rate for the zoom in from the hero (slower than room moves)

export default function HouseApp({ content, engine: external, onExit, leaving = false }: Props) {
  const view = useHouse((s) => s.view);
  const item = useHouse((s) => s.item);
  const visited = useHouse((s) => s.visited);
  const go = useHouse((s) => s.go);
  const close = useHouse((s) => s.close);
  const setTilt = useHouse((s) => s.setTilt);
  const [ready, setReady] = useState(false);
  const [gl, setGl] = useState<boolean | null>(null);
  const [petted, setPetted] = useState(0);
  const windowRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const engine = useRef<HouseEngine | null>(null);
  const tilt = useHouse((s) => s.tilt);
  const rot = useHouse((s) => s.rot);
  const rotate = useHouse((s) => s.rotate);

  // Create the scene once WebGL is confirmed, or take over the hero's.
  useEffect(() => {
    if (!gl || !stageRef.current) return;
    const s = useHouse.getState();
    const onRoomClick = (room: RoomId) => useHouse.getState().go(room, ROOM_DEFAULT[room]);
    const lit = { main: true, studio: isLit('studio', s), lab: isLit('lab', s) };
    if (external) {
      // The canvas is framed on the hero's position; move it full-screen (it jumps to the same spot),
      // then ease into the house view. That ease is the "zoom in".
      external.setHost(stageRef.current);
      external.setRoomClick(onRoomClick);
      external.setTilt(0);
      external.setInstant(reduced());
      external.setLit(lit);
      external.nextFrame().then(() => {
        external.setFrame(frameFor(s.view, s.item, s.rot), false, ENTER_SPEED);
        setReady(true);
      });
      engine.current = external;
      return () => {
        external.setRoomClick(undefined);
        engine.current = null;
      };
    }
    const e = new HouseEngine(stageRef.current, {
      frame: frameFor(s.view, s.item, s.rot),
      onRoomClick,
      onFirstFrame: () => {
        e.setInstant(reduced());
        setReady(true);
      },
    });
    e.setLit(lit, true);
    e.setAmbient(60);
    engine.current = e;
    return () => {
      e.dispose();
      engine.current = null;
    };
  }, [gl, external]);

  // Keep the scene in step with the store (not while leaving: enter.ts owns the camera then).
  const first = useRef(true);
  useEffect(() => {
    if (first.current) return void (first.current = false);
    if (!leaving) engine.current?.setFrame(frameFor(view, item, rot));
  }, [view, item, rot, leaving]);
  useEffect(() => engine.current?.setLit({ main: true, studio: isLit('studio', { view, visited }), lab: isLit('lab', { view, visited }) }), [view, visited]);
  useEffect(() => engine.current?.setTilt(tilt), [tilt]);
  const lastHotspot = useRef<HTMLElement | null>(null);

  // Deep link in, and keep the URL in sync so a room can be shared.
  useEffect(() => {
    setGl(webglAvailable());
    const room = new URLSearchParams(location.search).get('room');
    if (room === 'studio' || room === 'lab' || room === 'main') go(room, ROOM_DEFAULT[room]);
  }, [go]);
  useEffect(() => {
    const url = new URL(location.href);
    if (view === 'overview') url.searchParams.delete('room');
    else url.searchParams.set('room', view);
    history.replaceState(history.state, '', url);
  }, [view]);

  // Escape: close the window, then step back out to the whole house.
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      const s = useHouse.getState();
      const typing = (e.target as HTMLElement)?.closest?.('input, textarea, [contenteditable]');
      if (!typing && (e.key === 'q' || e.key === '[')) return s.rotate(-1);
      if (!typing && (e.key === 'e' || e.key === ']')) return s.rotate(1);
      if (e.key !== 'Escape') return;
      if (s.item) {
        s.close();
        lastHotspot.current?.focus();
      } else if (s.view !== 'overview') s.go('overview');
    };
    addEventListener('keydown', key);
    return () => removeEventListener('keydown', key);
  }, []);

  // Move focus into a newly opened window.
  useEffect(() => {
    if (item) windowRef.current?.querySelector<HTMLElement>('h2')?.focus();
  }, [item]);

  // Drag to tilt (±15°). Pointer events on the canvas only, so hotspots and the window still click.
  const drag = useRef<{ x: number; t: number } | null>(null);
  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (reduced()) return;
    drag.current = { x: e.clientX, t: useHouse.getState().tilt };
  }, []);
  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!drag.current) return;
      const t = drag.current.t - ((e.clientX - drag.current.x) / 600) * MAX_TILT * 2;
      setTilt(Math.max(-MAX_TILT, Math.min(MAX_TILT, t)));
    },
    [setTilt],
  );
  const endDrag = useCallback(() => (drag.current = null), []);

  // walls facing the camera are cut away in rotated views; so are the hotspots hung on them
  const az = azimuthFor(rot);
  const wallShown = (f?: Face) => !f || FACE_NORMAL[f][0] * Math.sin(az) + FACE_NORMAL[f][1] * Math.cos(az) < 0;
  const litCount = ROOM_ORDER.filter((r) => isLit(r, { view, visited })).length;
  const here = view === 'overview' ? 'main' : view;
  const crumb = view === 'overview' ? null : ROOMS[view].label;

  const openHotspot = (id: string, room: RoomId, el: HTMLElement) => {
    lastHotspot.current = el;
    if (id === 'pet') {
      engine.current?.greetPet();
      return setPetted((n) => n + 1);
    }
    go(room, id);
  };

  if (gl === false) {
    return (
      <div className="hx-fallback">
        <p>This browser can't draw the 3D house. The short tour has everything:</p>
        <ul className="hx-links">
          <li><a href="/#studio">The studio · work</a></li>
          <li><a href="/#lab">The lab · side projects</a></li>
          <li><a href="/#about">The main room · about me</a></li>
        </ul>
      </div>
    );
  }

  return (
    <div className={`hx${ready ? ' is-ready' : ''}${leaving ? ' is-leaving' : ''}${external ? ' is-embedded' : ''}`} data-view={view}>
      <div
        ref={stageRef}
        className="hx-stage"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onPointerLeave={endDrag}
      >
      </div>

      {/* Hotspots and labels, pinned to the scene */}
      <div className="hx-overlay">
        {ROOM_ORDER.filter((r) => r !== here).map((r) => (
          <Pin key={r} anchor={ROOMS[r].labelAnchor} className="hx-roomlabel" hidden={view !== 'overview'} clamp>
            <button type="button" onClick={() => go(r, ROOM_DEFAULT[r])}>
              <span className="label">{ROOMS[r].label}</span>
              <span className="hx-roomlabel-sub">{r === 'studio' ? 'selected work →' : r === 'lab' ? 'experiments →' : 'about me →'}</span>
            </button>
          </Pin>
        ))}
        {HOTSPOTS.map((h) => (
          <Pin key={h.id} anchor={h.anchor} className={`hx-hotspot${item === h.id ? ' is-open' : ''}`} hidden={h.room !== here || !wallShown(h.wall)}>
            <button type="button" onClick={(e) => openHotspot(h.id, h.room, e.currentTarget)} aria-expanded={h.inline ? undefined : item === h.id}>
              <span className="hx-dot" aria-hidden="true" />
              <span className="hx-hotspot-label">{h.label}</span>
            </button>
            {h.id === 'pet' && petted > 0 && <Hearts key={petted} />}
          </Pin>
        ))}
        <Pin anchor="me" className="hx-bubble" hidden={view !== 'overview' || item !== null}>
          <p>Hi, I'm {content.site.name}. Make yourself at home. My work is in the studio.</p>
        </Pin>
      </div>

      <header className="hx-top">
        <div className="hx-top-start">
          <a
            className="hx-exit"
            href="/"
            onClick={(e) => {
              if (!onExit || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
              e.preventDefault();
              onExit();
            }}
          >
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
          {ROOM_ORDER.map((r) => (
            <button key={r} type="button" aria-current={view === r ? 'true' : undefined} onClick={() => go(r, ROOM_DEFAULT[r])}>
              {ROOMS[r].label}
            </button>
          ))}
        </nav>
        <div className="hx-lit" aria-live="polite">
          <span className="hx-lit-dots" aria-hidden="true">
            {ROOM_ORDER.map((r, i) => (
              <span key={r} className={isLit(r, { view, visited }) ? 'on' : ''} data-i={i} />
            ))}
          </span>
          {litCount === 3 ? 'All rooms lit' : `${litCount} / 3 rooms lit`}
        </div>
      </header>

      <p className="hx-hint">{view === 'overview' ? 'Follow the light through a doorway · drag to tilt' : 'Esc to step back · drag to tilt'}</p>

      <div className="hx-turn" role="group" aria-label="Rotate the view">
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
      </div>

      {item && WINDOW_TITLES[item] && (
        <aside ref={windowRef} className="hx-window" aria-labelledby="hx-window-title">
          <div className="hx-window-bar">
            <h2 id="hx-window-title" className="label" tabIndex={-1}>{WINDOW_TITLES[item]}</h2>
            <button
              type="button"
              className="hx-close"
              aria-label="Close window"
              onClick={() => {
                close();
                lastHotspot.current?.focus();
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" aria-hidden="true"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
            </button>
          </div>
          <div className="hx-window-body">
            <WindowBody id={item} content={content} />
          </div>
        </aside>
      )}
    </div>
  );
}
