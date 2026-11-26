# House v2: the Pinwheel house, built with Blender

Handoff for the next house session. As of 2026-11-20 this is planned, not started: no Blender file, script or GLB exists yet.

## Goal

Replace today's 3-room house with the **Pinwheel house** from the Design canvas, so the home hero, "Step in" and `/house` all show it.

- Design canvas: https://claude.ai/artifact/885jDu185netxT4PYgYw9J (sign in to claude.ai in the browser pane to read it)
  - **Hero-Sunken-P2**: the hero with the rendered house, the new isometric grid (canvas asset `77d21eb61c29c1887ec2d992f9587fee`), and the house box moved to top 208, 860×454 (was top 120, 860×645). The hero windows, key and pet are placed against that box.
  - **Plan-P2**: written spec and flat plan. The living room was recently rearranged: checkered rug, re-sized sofa, coffee table, new record shelf, window and door tweaked.
- The render only exists as an image on the canvas. If the file or script that produced it turns up, start from that; it shrinks the work a lot.

## What the new house is

| | The site now | Pinwheel house |
|---|---|---|
| Look | Flat colours, ink outlines | Shaded low-poly, soft shadows, darkened corners, no outlines |
| Plan | 3 rooms (studio, main, lab) | Living room in the middle, four wings around it (bedroom, studio, lab, entry), entry stair cut into the page, 3 small gardens, workout deck, front garden, glass walls, hedges, faceted trees |
| Props | ~38 primitives | ~60–80: bed, gaming PC desk, treadmill, posters, trees… |
| Character | Boxes | Low-poly you: big head, glasses, hair; rigged with wave, walk/run and sit |
| Rooms | 3 | 4, which adds a room switch and new windows |

## How the house works today (what changes, what stays)

Engine: `src/house/*`, about 3,800 lines, three.js inside a React island.

- `layout.ts`: the house as data. Prims (`box`, `poly`, `cyl`, `ball`), `RoomId = 'studio' | 'main' | 'lab'`, `RIM` (the hole in the page the house sinks into), `SPILL`, and `ANCHORS` (hotspots and waypoints). It's a port of `design/assets/house/house-art-generator.py`.
- `geometry.ts`: turns prims into per-room buffers with flat vertex colours and ink outline lines (`LINE_WORLD`). Plan coords → world via `toWorld` (x → X, z → Y, y → Z, with `Z_SQUASH`).
- `camera.ts`: 2:1 dimetric, `ELEVATION = π/6`, `AZIMUTH = π/4`. Rotating cuts away the wall nearest the camera (`face` on prims).
- `actors.ts`, `life.ts`: character and pet, routines over a hand-placed waypoint graph.
- `engine.ts`, `hero.ts`, `enter.ts`, `HouseApp.tsx`, `Windows.tsx`, `screens.ts`, `content.ts`, `store.ts`: the scene loop, hero, the "Step in" transition, the room UI and hotspot windows.
- Posters: `npm run build && npm run poster` (`scripts/render-poster.mjs`) renders `/poster` with Playwright into `src/assets/house/poster-lit.png` and `poster-dim.png`, so the still and the live scene line up.

What stays in code: hotspots, rotation cut-aways, the "Step in" zoom, room switch, routines. Blender only names the parts the code hooks onto.

## The Blender plan

Claude drives Blender headless with Python (`blender -b -P script.py`). Blender doesn't need to be open, only on PATH (`blender --version`).

1. **Scripts in the repo:** for example `house3d/build.py` builds the scene from a data file, `house3d/export.py` exports the GLB, and `house3d/render.py` renders a check still. Keep the `.blend` as a build output, not the source of truth, so the house can be rebuilt from scripts.
2. **Bake the look:** bake ambient occlusion and soft shadows into vertex colours. The site then draws the shaded look with a cheap unlit material, with no lights or shadow maps at runtime.
3. **Naming contract:** objects named so the code can find them: `room:<id>`, `wall:<room>:<face>` (for cut-aways), `hot:<anchorId>` (hotspots), `wp:<id>` (waypoints), `screen:<id>` (video/canvas surfaces). `ANCHORS` and the waypoint graph come from these empties instead of hand-typed numbers.
4. **Export:** glTF binary, Draco or meshopt compressed, flat vertex colours, no textures. Budget: the house **under ~400 KB** (today ~151 KB) and JS around 200 KB. Character and pet as separate GLBs with animation clips (idle, walk, sit, wave, interact).
5. **Load:** `useGLTF`-style loading in the island; the poster still shows first, and the 3D crossfades in when idle and visible. Respect Save-Data, low memory and reduced motion (rules in `design/portfolio-handoff.md`).
6. **Check every step:** render a still from the site camera (dimetric, same angles) and compare it with the canvas render.

## Order of work (about 6–9 sessions)

1. Set up the Blender → GLB → site pipeline and agree the look on **one room** (lighting, baked shadows, a faceted tree). (1–2)
2. Floor plan, walls, glass, gardens, stair, and the rim the house sinks into. (1–2)
3. Furniture and props, matched to the render. (2)
4. Character and pet, rigged and animated. (1–2) **Done for the hero (2026-11-21):** `house3d/rig_character.py` → `public/house3d/character.glb` (idle, wave, walk, sit); the hero waves and says hi on hover/focus, once on touch; the pet hops (`src/house3d/life.ts`). He walks routines too (`house3d/walks.py` → `public/house3d/walks.json`: records, turntable, sofa, pet, PC, books, garden tree) and stands on a new mark the camera sees whole. Hotspots and the 4-room switch are still step 5.
5. Waypoints, hotspots, bedroom content, room switch for 4 rooms. (1) **Mostly done (2026-11-21, branch `house-v2-full`):** `/house` and "Step in" show the Pinwheel house. `src/house3d/HouseView.tsx` (room switch for living, bedroom, studio, lab; hotspots opening the old windows; quarter turns with cut-aways; drag tilt; poster first), `stage.ts` (camera, cut-aways), `rooms.ts` (rooms, hotspots). "Step in" is a cross-document view transition from the hero to the `/house` poster. Still open:
   - The GLB has no `room:` / `hot:` / `wp:` / `wall:` / `screen:` names yet. Rooms are copied from `plans.py`, hotspots hang on the named furniture, `wall_art` clusters and one plan point (the front door), and cut-aways are worked out from the plan outline. Naming them in Blender would replace the copies in `rooms.ts`.
   - Not in the GLB at all: a window for "about me" (now on the character), the prints for "talks" (the old `notice` hotspot is dropped) and the turntable's record swap. Not adding them: the house stays as it is (decided 2026-11-22).
   - **Done (2026-11-22):** the "ask him" routines. `life.ts` `ask(spot)`: the turntable, arcade, sofa (a new inline hotspot) and pet hotspots send him there now, getting up first if he sits. `walks.py` adds an `arcade` spot (`ask: true`, never in his own routine) and `between`, a path from every spot to every other, so he walks straight from one to the next; mid-walk he carries on or turns back, whichever is shorter.
   - **Done (2026-11-22):** the arcade's game screen, in code (`src/house3d/screens.ts`): the cabinet's own `glow_#86ad57` face gets UVs and a pixel canvas of the pet game; it speeds up and shows "P1" while he plays. Move it to a named `screen:arcade` face when the GLB is next rebuilt.
   - Done (2026-11-21): the bedroom photo wall opens travel photos (`travel` in `src/data/site.ts`).
6. Hero placement (top 208, 860×454, new grid), posters, download size, phones, reduced motion. (1) **Mostly done (2026-11-22):** hero placement and grid (d0465e5, df6037d); poster re-rendered with the arcade screen; `/house` and `/` checked at 375 px (no sideways scroll); with reduced motion nothing walks, asks are ignored and the screen stays on its first frame. **Download size: kept as is (Abraham, 2026-11-22: keep the current house).** `house_P2.glb` is 1.03 MB (806 KB gzipped) against the ~400 KB budget. It's already Draco; coarser quantization (position 12 bits, normal 8) only gets 889 KB. The weight is the applied bevels (bookcase 83 KB, PC desk 51 KB…), 186 materials / 314 primitives (210 KB of JSON), and the house's static `character_abraham` (110 KB, hidden once character.glb loads). Getting near 400 KB would mean dropping or thinning the bevels, merging materials into vertex colours, and dropping the static character (the `still` poster mode would then need character.glb). Not doing it: the bevels are part of the look. Blender 5.2's exporter reproduces the current GLB byte for byte, so re-exporting is safe.

## Open questions for the owner

Answered 2026-11-21:
- Treadmill: on the wall beside it, a medal hanger and instax prints of his running; the prints open a window of running photos (`running` in `src/data/site.ts`, placeholders until he adds photos). Built in code for now (`src/house3d/props.ts`, on the deck's outer wall between the pull-up uprights); move it into `house3d/source` when the GLB is next rebuilt, then drop the code copy. The treadmill itself does nothing to click; on `/house` his routine takes him there now and then: he steps onto the belt, runs (the `run` clip) for 12–20 s, turns round and steps off. Not in the hero (asked by Abraham).
- Gaming PC: nothing for now.
- Bedroom: light on arrival, like every room.
- Rotation: snaps to four angles (plus the ±15° drag tilt).
- The bedroom's "off the clock →" stays for now.

Answered 2026-11-21 (later): the bedroom photo wall opens travel photos.

Decided 2026-11-22: **keep the current house.** The model stays as it is: no thinning the bevels or merging materials to cut the download size (1.03 MB is accepted), and no new objects (talks prints, an about-me window, a record-swap screen).

## Also still open from the board port

- Home hero: the new grid and house placement above (do them with step 6, or as an image swap earlier if wanted).
- Mobile home: **not building Space-FullPage-Mobile** (decided 2026-11-27). The mockup predates later decisions (sentence case, the Pinwheel house on its grid, the Get Info About, the turntable card) and no "HELLO my name is" sticker. Phones get the current home page in one column; fixed for phones: case previews keep the screenshots' landscape shape (no side crop) and the lab says "Tap to open." on touch screens.

## Setting up a new machine

```bash
git clone https://github.com/abrahamwill/space.git
cd space
npm install
npx astro dev
blender --version
```

Node 24 is what the Mac uses (24.21.0). On Windows: `winget install BlenderFoundation.Blender`, `winget install Git.Git`, `winget install OpenJS.NodeJS`, and add Blender's folder to PATH if `blender` isn't found.
