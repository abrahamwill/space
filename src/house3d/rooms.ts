/**
 * The Pinwheel house (house_P2.glb) as the full view sees it: rooms, the room switch, and what each
 * object opens.
 *
 * GLB coordinates are the plan's metres (house3d/source/plans.py, plan "P2"): plan x → world X,
 * plan y → world Z, height → Y. The hero camera looks from +X +Z, so every wall in the GLB stands on a
 * room's low-x or low-z edge (the high edges are already cut away for that angle).
 *
 * The GLB doesn't carry the naming contract from design/house-v2-blender.md yet (`room:`, `hot:`,
 * `wp:`, `wall:`). Until it does:
 *   - rooms are the plan's rectangles, copied below;
 *   - hotspots hang on the named furniture (`<room>_<kind>_<Label>`), on clusters of `wall_art`
 *     inside a room, or on a point from the plan (the front door);
 *   - wall cut-aways are worked out from the plan's outline (see stage.ts).
 */
import type { Face } from './stage';

export type RoomId = 'living' | 'bedroom' | 'studio' | 'lab';
export const ROOM_ORDER: RoomId[] = ['living', 'bedroom', 'studio', 'lab'];

/** x, z, width (x), depth (z), in metres. */
export type Rect = readonly [number, number, number, number];

export interface Room {
  label: string;
  /** In the room switch. */
  short: string;
  /** The line under the label on the overview ("selected work →"). */
  sub: string;
  rect: Rect;
  /** Zoom relative to the overview. */
  zoom: number;
}

export const ROOMS: Record<RoomId, Room> = {
  living: { label: 'Living room', short: 'Living', sub: 'about me →', rect: [3, 3, 5, 5], zoom: 2 },
  bedroom: { label: 'Bedroom', short: 'Bedroom', sub: 'off the clock →', rect: [1.5, 0, 4.5, 3], zoom: 2.2 },
  studio: { label: 'Studio', short: 'Studio', sub: 'selected work →', rect: [0, 4.5, 3, 4], zoom: 2.2 },
  lab: { label: 'Lab', short: 'Lab', sub: 'experiments →', rect: [8, 1.5, 3, 4.5], zoom: 2.2 },
};

/**
 * Everything the plan puts on the ground (rooms, gardens, decks, the entry stair), from plans.py P2.
 * The outline of this is where the perimeter walls stand.
 */
export const FOOTPRINT: Rect[] = [
  [3, 3, 5, 5], [1.5, 0, 4.5, 3], [0, 4.5, 3, 4], [8, 1.5, 3, 4.5], // living, bedroom, studio, lab
  [11, 1.5, 1.5, 4.5], [4.5, 8, 4.5, 3.5], [0, 8.5, 3, 1.5], [3, 8, 1.5, 3.5], // deck, garden, workout deck
  [0, 3, 3, 1.5], [6, 0, 2, 3], [8, 6, 3, 2], // pocket gardens
  [-1.5, 3, 1.5, 1.5], [-3, 3, 1.5, 1.5], [-3, 1.5, 1.5, 1.5], // entry stair
];

export const inRect = (r: Rect, x: number, z: number, pad = 0) =>
  x > r[0] - pad && x < r[0] + r[2] + pad && z > r[1] - pad && z < r[1] + r[3] + pad;
export const onFootprint = (x: number, z: number) => FOOTPRINT.some((r) => inRect(r, x, z));
export function roomAt(x: number, z: number): RoomId | null {
  for (const id of ROOM_ORDER) if (inRect(ROOMS[id].rect, x, z)) return id;
  return null;
}

/** Where a hotspot hangs. */
export type Anchor =
  /** On top of a named object in the GLB. `drop` lowers the dot from the object's top (m). */
  | { object: string; drop?: number }
  /** On the framed art (`wall_art`) inside this part of a room. */
  | { art: Rect }
  /** A point in the house (plan data), for parts the GLB doesn't name. */
  | { point: readonly [number, number, number]; wall?: Face }
  /** On the character (follows him). */
  | { me: true };

export interface Hotspot {
  id: string;
  room: RoomId;
  label: string;
  anchor: Anchor;
  /** No window: does something in place (the pet). */
  inline?: boolean;
  /** Shown in every room's view (he walks around the house), not only in `room`. */
  everywhere?: boolean;
}

/**
 * What each object opens. Order = tab order within a room. The ids are the window ids in
 * src/house/Windows.tsx; titles are WINDOW_TITLES below.
 */
export const HOTSPOTS: Hotspot[] = [
  // living room
  { id: 'window', room: 'living', label: 'Me · about me', anchor: { me: true }, everywhere: true },
  { id: 'turntable', room: 'living', label: 'Turntable · next record', anchor: { object: 'living_console_Turntable' } },
  { id: 'photos', room: 'living', label: 'Record shelf · photos', anchor: { object: 'living_shelf_Records' } },
  { id: 'door', room: 'living', label: 'Front door · contact + CV', anchor: { point: [3, 1.2, 3.75] } },
  // bedroom (what opens here is an open question, see design/house-v2-blender.md)
  { id: 'pc', room: 'bedroom', label: 'Gaming PC', anchor: { object: 'bedroom_desk_Desk___PC' } },
  { id: 'photowall', room: 'bedroom', label: 'Photo wall', anchor: { art: [1.6, 0, 2.2, 0.6] } },
  // studio
  { id: 'folders', room: 'studio', label: '3 featured folders', anchor: { object: 'studio_desk_Desk', drop: 0.5 } },
  { id: 'archive', room: 'studio', label: 'Shelves · archive', anchor: { object: 'studio_shelf_Archive' } },
  { id: 'pinboard', room: 'studio', label: 'Pinboard · how I work', anchor: { art: [0, 4.5, 1, 4] } },
  { id: 'treadmill', room: 'studio', label: 'Treadmill', anchor: { object: 'deckS_treadmill_Treadmill' } },
  // lab
  { id: 'prototypehub', room: 'lab', label: 'Workbench · Prototype Hub', anchor: { object: 'lab_desk_Bench' } },
  { id: 'arcade', room: 'lab', label: 'Arcade · pet game', anchor: { object: 'lab_arcade_Arcade' } },
  { id: 'voice', room: 'lab', label: 'Voice gadget · conversational AI', anchor: { object: 'lab_table_Voice' } },
  { id: 'whiteboard', room: 'lab', label: 'Whiteboard · learning notes', anchor: { art: [8, 1.5, 3, 1] } },
  { id: 'pet', room: 'lab', label: 'Pet me', anchor: { object: 'lab_pet_Pet' }, inline: true },
];

/** The window that opens when you walk into a room. */
export const ROOM_DEFAULT: Record<RoomId, string | null> = { living: null, bedroom: null, studio: 'folders', lab: 'prototypehub' };

export const WINDOW_TITLES: Record<string, string> = {
  window: 'Living room · about me',
  turntable: 'Living room · turntable',
  photos: 'Living room · record shelf',
  door: 'Living room · front door',
  pc: 'Bedroom · gaming PC',
  photowall: 'Bedroom · photo wall',
  folders: 'Studio · featured work',
  archive: 'Studio · archive',
  pinboard: 'Studio · how I work',
  treadmill: 'Studio · treadmill',
  prototypehub: 'Lab · workbench',
  arcade: 'Lab · arcade',
  voice: 'Lab · voice gadget',
  whiteboard: 'Lab · whiteboard',
};
