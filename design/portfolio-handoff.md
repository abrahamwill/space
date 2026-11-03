# Portfolio site ("Space") — handoff

Last updated: 2026-11-03. Read this first in any new session about the portfolio.

## Where the work lives
- **Design canvas (moodboard + drafts):** https://claude.ai/artifact/885jDu185netxT4PYgYw9J — a Design artifact. Read `project/canvas.json` before editing; the owner edits it by hand too, so always re-read and merge, never overwrite.
- **House art generator:** project doc `claude/house-art-generator.py` (Python + Pillow). Run `python3 house-art-generator.py OUTDIR` → `house_dim.png` (main lit, studio+lab dark), `house_studio.png` (lab dark), `house_lit.png` (all lit), 2400×1800 transparent PNGs, plus `anchors.json` (hotspot positions in % of the image).
- Current uploaded art on the canvas: house_lit `/_blob/588f347394385827507993bcca7f476c`, house_dim `/_blob/3d125aedc5bd110a9839ca55d83cc71c`, house_studio `/_blob/555d6b4c6ece795db57659c1133b4511`. Owner screenshots: Prototype Hub `/_blob/eed3771577dd3544782cdeaebbe2c104`, pet game `/_blob/264d439347f8f091c2749ec8bce3c26f`.

## Concept (decided)
- One site, two ways in. **Fast view**: normal scrollable portfolio (hero, selected work, lab, about, contact) for recruiters. **House view**: interactive isometric house. Default per application link (`?mode=focus` / `?mode=play`). House code/art loads only on intent (hover/click), never for fast-view visitors.
- The house sits in the fast-view hero as a still image you can scroll past; clicking it (or "Come inside") enters the house.
- Case studies are the same pages in both views; in the house they open as a window over the zoomed room.

## House (decided)
- **Sunken cutaway, like the owner's reference:** the page is the ground; rooms are a pit cut into it. Outline = floor plan traced at wall-top height; the front rim hides a strip of floor (≈ wall height × 1.1 in plan units), so important things sit along back walls. Wall height 4.2 units. NOT a floating block.
- **Three rooms only**, irregular plan (plan units): Studio x0–14,y0–9 (small, back-left); Main room x0–18,y9–28 (biggest); Lab x18–31,y4–20 (right). Small notch at the back, big empty notch front-right. Low partitions with doorways between rooms.
- **Zoom, don't isolate:** room views scale the whole house ~2.1× centred on the room (other rooms stay visible, cropped by the screen). Overview → room is one CSS transform; hotspot labels counter-scale.
- **Rooms light up as visited:** overview = main lit, studio + lab dark with light spilling from doorways; counter "1/3 rooms lit".
- Optional small tilt (±15–20°) on drag/mouse; full 90° rotation postponed.
- **Room contents → content:**
  - Main room: turntable on walnut console (music), big garden window (about me), record shelf (photos), framed prints by the door (talks & workshops), front door + coat rack (contact + CV), the owner's avatar with a greeting bubble.
  - Studio: desk with 3 folders (3 featured case studies), walnut credenza + shelves (archive / older work), pinboard (how I work).
  - Lab: workbench (Prototype Hub), red arcade cabinet (cozy pet game), voice gadget (conversational AI + "ask the gadget" input), whiteboard (learning notes), pet bed ("pet me" easter egg).

## Art direction (decided)
- Line-iso illustration (flat fills, dark ink outlines), restyled **mid-century modern × Bauhaus** from the owner's interior references: cream plaster, oak plank floors, walnut panels/credenzas, olive lounge sofa, checkered rug, chrome tube furniture, fiddle-leaf plants; Bauhaus accents red #c8442b, cobalt #2b4fa8, mustard #e0a72e. Page/surface colour #ffeede, ink #1a1a1a.

## UI style (decided by owner)
- **Hero: very minimal Swiss/Bauhaus.** The house is the centre of attention (large, bleeding off the right edge, as in the owner's sketch). Nothing else competes: name, 3 room links + "Step inside", one headline, one sentence, two actions.
- **Below the hero: record sleeve / poster** for content and footer (square Bauhaus-shape covers, tracked caps labels, a colour-field footer). Structure follows Toan's and Arjun's landing pages: few items, big statements, sentences that flow into each other.
- **Less is more:** senior, direct, generous whitespace; never pack many things into small spaces. One typeface (Schibsted Grotesk); colours cream #f4eee4, ink #1b1a17, accents red #c8442b, cobalt #2b4fa8, mustard #e0a72e.
- **Copy is one connected thread** inviting people into the owner's space: hero "Welcome to my space" → "take the short tour" → 01 The studio (work) → 02 The lab (side projects) → 03 The main room (about) → footer "The door's open" (contact) → "step back inside the house". No section stands alone.
- Reference board: `Home-v3.dc.html` on the canvas. Older drafts (Portfolio-Home, Portfolio-Case, House HUD screens) still use the earlier neobrutal look and must be brought in line with this. The five UI option tiles stay on the canvas as history.

## Draft screens on the canvas (clickable in Play)
Portfolio-Home, Portfolio-Case (case-study template), House-Overview, House-Studio (zoom + case window), House-Lab (zoom + Prototype Hub window). Placeholders in [brackets] are for the owner to fill; no invented metrics.

## Content facts (from the owner)
- Senior Product Designer at Gokomodo (agri supply chain), since 2021, senior since 2023; led research + design of a storefront app for farmers in Kalimantan and Sumatra (case study 01).
- CS, Universitas Indonesia (2021); Deputy, Digital Product Design SIG at RISTEK; workshops at RISTEK and COMPFEST; Gen AI Labs community.
- Lab projects: **Prototype Hub** (handoff hub for coded prototypes: comments, touch hints, guided flows, versioning, present mode — used by their team; check before showing internal prototype names publicly), **cozy pet game** (in development), **conversational AI** (learning bit by bit).

## House = live 3D simulation (decided direction)
- **Stack (recommended, owner to confirm when building):** Astro site; the house as one React island using React Three Fiber + drei (orthographic camera, Outlines, Html hotspots, useGLTF/useAnimations) + Zustand for state; Blender models exported as compressed GLB, flat vertex colours, no textures. Not Unity/Godot web export (too heavy), Spline only for quick mock-ups.
- **Sunken look in 3D:** page-coloured surface plane at wall-top height with the floor-plan hole cut out, orthographic camera, background = page colour; flat/toon shading + ink outlines.
- **Always alive, even without zooming in:** first paint shows a still poster rendered from the same scene/camera; after the page loads and is idle (and only while the hero is visible) the 3D island loads and crossfades in. No auto-load on slow connections / Save-Data / low-memory devices / reduced motion. Hero renders ~30fps at reduced resolution; full quality when inside; pause when off-screen or tab hidden. `?mode=focus` = poster only until clicked. Budget ≈ 200 KB JS + 1–3 MB models.
- **Autonomous life:** the character and pets run routines via small state machines over a hand-placed waypoint graph (no navmesh); animation clips idle/walk/sit/interact; turntable spins, screens show looping video or a tiny canvas animation; "furniture interacting" is keyframed, no physics.
- **Click-to-task (later milestone):** clicking the turntable updates "now playing" instantly, then the character walks over (cap ~2 s, else swap in place) and plays a ~1.5 s record-swap clip; the song changes on the swap moment; rapid clicks keep only the latest. Same pattern later for arcade, sofa, pets. Fallback: turntable animates on its own.
- **Suggested milestones:** 1) fast-view home (Home v3) + one case study; 2) static 3D house + poster + camera zoom between rooms; 3) ambient routines (character, pets, turntable, screens); 4) click-to-task interactions.

## Open next steps
1. Pick a UI style and retune the Home/Case/HUD drafts to it.
2. Write case study 01 with real content to test the template.
3. Hero: consider making the house larger and bleeding off the right/bottom edge (owner's sketch).
4. Decide build stack (likely 3D with orthographic camera + flat/toon shading + outline pass, which makes zoom/tilt/rotation cheap) vs. layered 2D.
