# Portfolio ("Space")

The portfolio has two ways in: the fast view (the Home v3 design and its case studies) and the house view (an interactive 3D cutaway of the house). Milestones 1 and 2 are done.
The design brief and the reference files are in `design/`. Read `design/portfolio-handoff.md` first.

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # static site in dist/
npm run check    # type check
npm run poster   # re-render the house posters from the 3D scene (run after npm run build)
```

## What's here

| Route | File | Notes |
|---|---|---|
| `/` | `src/pages/index.astro` | Hero with the house (poster first, then live 3D), then 01 Studio, 02 Lab, 03 Main room, and the front-door footer |
| `/work/<slug>` | `src/pages/work/[slug].astro` | Case-study template. Only entries with `published: true` get a page |
| `/house` | `src/pages/house.astro` → `src/house/HouseApp.tsx` | The house: the overview, zooming into rooms, info windows, rotating in 90° steps, and rooms lighting up as you visit them. Loading this URL directly gives the standalone page; from the home page the house opens in place (below) |
| `/poster` | `src/pages/poster.astro` | Internal (noindex). Used by `npm run poster` |

Entry links: `?mode=focus` keeps the hero a still image until the visitor hovers over or touches it. `?mode=play` on `/` goes straight to `/house`. `/house?room=studio|lab|main` opens a room directly.

## The house (`src/house/`)

| File | What it does |
|---|---|
| `layout.ts` | **The house as data.** Rooms, walls, furniture, decals, hotspot anchors and the light spill, ported 1:1 from `design/assets/house/house-art-generator.py`. Change the layout here. |
| `geometry.ts` | Turns the layout into GPU buffers. Each room gets one flat-colour mesh and one batch of ink outlines. |
| `engine.ts` | A three.js renderer with no framework, shared by the hero and `/house`. It renders on demand only, so an idle house costs nothing. |
| `camera.ts` | The orthographic 2:1 dimetric camera (the same angle as the 2D art), the framing of the whole house and of each room (`ROOMS[room].zoom`), and the poster aspect ratio. |
| `hero.ts` | Mounts the hero house, with a small tilt toward the mouse. The loader script in `index.astro` decides when to mount it. |
| `enter.ts` | Steps inside from the home page with no page load: the hero canvas moves to a full-screen layer framed exactly where the hero was, then the camera eases into the house while the UI fades in over the page. Uses `pushState('/house')`; back, forward and "Exit house" run the reverse zoom into the hero. |
| `HouseApp.tsx`, `Windows.tsx`, `store.ts`, `content.ts`, `house.css` | The `/house` UI: top bar, hotspots, windows, and zustand state. Content comes from `src/data/site.ts` and the work collection. |
| `overlay.ts` | Pins DOM hotspots and labels to 3D points. Labels never scale with zoom. |

**Rotating:** the rotate buttons (or Q/E) turn the view in 90° steps, so every piece of furniture can be seen from four sides. The default view is the sunken cutaway from the art. In the other three views the page surface and the walls nearest the camera (plus anything hung on them, and its hotspot) are cut away, because the near rim would otherwise hide exactly the furniture you rotated to see. Box sides take the art's light or dark colour depending on which side of the screen they face, so the lighting reads the same from every angle. Wall-mounted items are tagged in `layout.ts` with `on('-x', …)` etc.

How it looks:
- **Colours:** flat vertex colours, written to the screen without colour management, so every hex value matches the reference art exactly.
- **Rim:** the page surface is a depth-only plane at wall-top height with the floor plan cut out, which gives the sunken look.
- **Dark rooms** mix toward night blue and show the warm doorway spill, the same way the 2D generator does.

**Hero loading rules:** the hero shows `poster-lit.png` first. The 3D scene loads after `load`, then idle, then once the hero is visible, and crossfades in. The poster is rendered from the same scene and camera, so they line up pixel for pixel. Auto-load is skipped for Save-Data, 2g/3g connections, `deviceMemory ≤ 2`, reduced motion and `?mode=focus`; in those cases the scene loads when the visitor hovers over, focuses or touches the house.

**Weight (gzip):** the hero loads 151 KB (three.js plus the engine) and 1.5 KB of loader. `/house` adds React and the UI, about 75 KB, and only loads when someone decides to step inside. The brief suggested React Three Fiber, but it bundles all of three.js and roughly doubled the hero download (about 330 KB), so the scene is plain three.js. Milestone 3 can load GLB models with `GLTFLoader` and use `AnimationMixer` directly in `engine.ts`.

**Posters:** after changing the layout or the colours, run `npm run build && npm run poster`. That rewrites `src/assets/house/poster-lit.png` (the hero) and `poster-dim.png` (the first paint of `/house`).

## Filling in content

Anything in `[brackets]` is a placeholder. Never invent metrics.

- **Name, links, CV, lab and about copy:** `src/data/site.ts`. The house windows use the same data.
- **House-only copy** (archive, pinboard, whiteboard, turntable, photos): `src/house/Windows.tsx`
- **Case studies:** `src/content/work/*.mdx`
  - Frontmatter holds the card summary, meta row, the "In short" paragraph, metrics, `prototypeUrl` and an optional `heroImage`.
  - In the body, `## Section name` becomes the numbered label and the "On this page" link. The `### Statement` below it is the big line.
  - The components `<Insights>`, `<Placeholder>`, `<Reflection>`, `<Screens>` and `<Action>` are in `src/components/case/`.
- **Featured cards 02 and 03:** `project-two.md` and `project-three.md` render as cards without links. Once a case study is written, set `published: true`. "The whole shelf →" shows up automatically when more than three are published, so `/work` has to exist by then.
- **Images:** put them in `src/assets/` and reference them from MDX or frontmatter. Astro outputs AVIF and WebP versions.
- **Lab screenshots** (`design/assets/lab/`) are not on the site yet. Check them for internal prototype names first.

## Tokens

`src/styles/global.css` mirrors `design/tokens.json`. Headings scale fluidly down to phone width. At 1280px and above they hit the token sizes exactly (H1 76, H2 48, lead 22).

## Next: milestone 3

- Ambient life: character and pet routines (small state machines over a hand-placed waypoint graph), a spinning turntable, and looping screens. Add an animation clock to `engine.ts` that only runs while the scene is visible, at about 30 fps in the hero.
- Swap primitives for Blender GLBs room by room: compressed, flat vertex colours, no textures.
