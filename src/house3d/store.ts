import { create } from 'zustand';
import type { RoomId } from './rooms';

export type View = 'overview' | RoomId;

const QUARTER = Math.PI / 2;

interface HouseState {
  view: View;
  /** Open window (hotspot id), or null. */
  item: string | null;
  /** The free turn a drag adds on top of `rot` (rad), kept within ±45°. */
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
  /** Turn freely by `d` rad (a drag); past 45° it rolls over into the next quarter turn. */
  spin: (d: number) => void;
  /** Back to the default angle (the nearest full turn, so it doesn't spin round several times). */
  unturn: () => void;
  /** To the next quarter turn that way (from a free turn too). */
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
  spin: (d) =>
    set((s) => {
      const turns = s.rot + (s.tilt + d) / QUARTER;
      const rot = Math.round(turns);
      return { rot, tilt: (turns - rot) * QUARTER };
    }),
  unturn: () => set((s) => ({ rot: Math.round(s.rot / 4) * 4, tilt: 0 })),
  rotate: (dir) =>
    set((s) => {
      const turns = s.rot + s.tilt / QUARTER;
      return { rot: dir > 0 ? Math.floor(turns + 1e-3) + 1 : Math.ceil(turns - 1e-3) - 1, tilt: 0 };
    }),
}));
