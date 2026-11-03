import { create } from 'zustand';
import type { RoomId } from './layout';

export type View = 'overview' | RoomId;

interface HouseState {
  view: View;
  /** Open window (hotspot id), or null. */
  item: string | null;
  /** Rooms visited this session. The main room is always lit. */
  visited: RoomId[];
  tilt: number;
  /** Quarter turns from the default view. Unbounded, so turning keeps going the same way. */
  rot: number;
  /** The record asked for (shown as "now playing" straight away). */
  record: number;
  /** The record actually on the platter, and what's happening to it. */
  onDeck: number;
  recordState: 'playing' | 'coming' | 'swapping';
  sound: boolean;
  setRecord: (i: number) => void;
  setDeck: (i: number, state: HouseState['recordState']) => void;
  setSound: (on: boolean) => void;
  go: (view: View, item?: string | null) => void;
  open: (item: string, room: RoomId) => void;
  close: () => void;
  setTilt: (t: number) => void;
  rotate: (dir: 1 | -1) => void;
  /** Back to the overview, default angle (leaving the house). */
  reset: () => void;
}

const KEY = 'house:visited';
const loadVisited = (): RoomId[] => {
  try {
    const v = JSON.parse(sessionStorage.getItem(KEY) || '[]');
    return Array.isArray(v) ? v.filter((r) => r === 'studio' || r === 'lab' || r === 'main') : [];
  } catch {
    return [];
  }
};
const saveVisited = (v: RoomId[]) => {
  try { sessionStorage.setItem(KEY, JSON.stringify(v)); } catch { /* private mode */ }
};

export const useHouse = create<HouseState>((set, get) => ({
  view: 'overview',
  item: null,
  visited: typeof window === 'undefined' ? [] : loadVisited(),
  tilt: 0,
  rot: 0,
  record: 0,
  onDeck: 0,
  recordState: 'playing',
  sound: false,
  setRecord: (record) => set({ record }),
  setDeck: (onDeck, recordState) => set({ onDeck, recordState }),
  setSound: (sound) => set({ sound }),
  go: (view, item = null) => {
    const visited = get().visited;
    if (view !== 'overview' && !visited.includes(view)) {
      const next = [...visited, view];
      saveVisited(next);
      set({ view, item, visited: next });
    } else set({ view, item });
  },
  open: (item, room) => get().go(room, item),
  close: () => set({ item: null }),
  setTilt: (tilt) => set({ tilt }),
  rotate: (dir) => set((s) => ({ rot: s.rot + dir, tilt: 0 })),
  reset: () => set({ view: 'overview', item: null, tilt: 0, rot: 0 }),
}));

export const isLit = (room: RoomId, s: Pick<HouseState, 'view' | 'visited'>) =>
  room === 'main' || s.visited.includes(room) || s.view === room;
