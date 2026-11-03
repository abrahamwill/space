import type { AnchorId, RoomId } from './layout';

/** Content handed to the house from Astro (so the house and the fast view share one source). */
export interface HouseContent {
  site: { name: string; email: string; emailHref: string; linkedin: string; cv: string };
  featured: Array<{
    slug: string;
    title: string;
    summary: string;
    company: string;
    role: string;
    year: string;
    published: boolean;
    cover: 'sun' | 'moon' | 'mast';
    tldr?: string;
    metrics: Array<{ value: string; label: string }>;
    prototypeUrl?: string;
  }>;
  lab: ReadonlyArray<{ title: string; body: string; status: string; mark: string }>;
  about: { body: string; facts: ReadonlyArray<{ what: string; when: string }> };
}

export interface Hotspot {
  id: string;
  anchor: AnchorId;
  room: RoomId;
  label: string;
  /** No window: does something in place (e.g. the pet). */
  inline?: boolean;
}

/** What each object in the house opens. Order = tab order within a room. */
export const HOTSPOTS: Hotspot[] = [
  // main room
  { id: 'window', anchor: 'window', room: 'main', label: 'Window · about me' },
  { id: 'turntable', anchor: 'turntable', room: 'main', label: 'Turntable' },
  { id: 'notice', anchor: 'notice', room: 'main', label: 'Prints · talks' },
  { id: 'door', anchor: 'door', room: 'main', label: 'Front door · contact + CV' },
  { id: 'photos', anchor: 'photos', room: 'main', label: 'Record shelf · photos' },
  // studio
  { id: 'folders', anchor: 'folders', room: 'studio', label: '3 featured folders' },
  { id: 'archive', anchor: 'archive', room: 'studio', label: 'Shelves · archive' },
  { id: 'pinboard', anchor: 'pinboard', room: 'studio', label: 'Pinboard · how I work' },
  // lab
  { id: 'prototypehub', anchor: 'prototypehub', room: 'lab', label: 'Workbench · Prototype Hub' },
  { id: 'arcade', anchor: 'arcade', room: 'lab', label: 'Arcade · pet game' },
  { id: 'voice', anchor: 'voice', room: 'lab', label: 'Voice gadget · conversational AI' },
  { id: 'whiteboard', anchor: 'whiteboard', room: 'lab', label: 'Whiteboard · learning notes' },
  { id: 'pet', anchor: 'pet', room: 'lab', label: 'Pet me', inline: true },
];

/** The window that opens when you walk into a room. */
export const ROOM_DEFAULT: Record<RoomId, string | null> = { main: null, studio: 'folders', lab: 'prototypehub' };
