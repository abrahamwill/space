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
  go: (view: View, item?: string | null) => void;
  open: (item: string, room: RoomId) => void;
  close: () => void;
  setTilt: (t: number) => void;
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
}));

export const isLit = (room: RoomId, s: Pick<HouseState, 'view' | 'visited'>) =>
  room === 'main' || s.visited.includes(room) || s.view === room;
