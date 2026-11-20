import { create } from 'zustand';
import type { RoomId } from './rooms';

export type View = 'overview' | RoomId;

interface HouseState {
  view: View;
  /** Open window (hotspot id), or null. */
  item: string | null;
  tilt: number;
  /** Quarter turns from the default view. Unbounded, so turning keeps going the same way. */
  rot: number;
  /** The record asked for (shown as "now playing"). */
  record: number;
  sound: boolean;
  setRecord: (i: number) => void;
  setSound: (on: boolean) => void;
  go: (view: View, item?: string | null) => void;
  close: () => void;
  setTilt: (t: number) => void;
  rotate: (dir: 1 | -1) => void;
}

export const useHouse = create<HouseState>((set) => ({
  view: 'overview',
  item: null,
  tilt: 0,
  rot: 0,
  record: 0,
  sound: false,
  setRecord: (record) => set({ record }),
  setSound: (sound) => set({ sound }),
  go: (view, item = null) => set({ view, item }),
  close: () => set({ item: null }),
  setTilt: (tilt) => set({ tilt }),
  rotate: (dir) => set((s) => ({ rot: s.rot + dir, tilt: 0 })),
}));
