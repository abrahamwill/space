# Portfolio ("Space")

The fast view of the portfolio: the Home v3 design and case study 01. This is milestone 1.
The design brief and the reference files are in `design/`. Read `design/portfolio-handoff.md` first.

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # static site in dist/
npm run check    # type check
```

## What's here

| Route | File | Notes |
|---|---|---|
| `/` | `src/pages/index.astro` | Hero with the house poster, then 01 Studio, 02 Lab, 03 Main room, and the front-door footer |
| `/work/<slug>` | `src/pages/work/[slug].astro` | Case-study template. Only entries with `published: true` get a page |
| `/house` | `src/pages/house.astro` | Holding page until the 3D house is built (milestone 2) |

The site ships no framework JS. The only scripts are the reading progress bar and the "On this page" highlight on case studies, plus an inline `?mode=` recorder.

## Filling in content

Anything in `[brackets]` is a placeholder. Never invent metrics.

- **Name, links, CV, lab and about copy:** `src/data/site.ts`
- **Case studies:** `src/content/work/*.mdx`
  - Frontmatter holds the card summary, meta row, the "In short" paragraph, metrics, `prototypeUrl` and an optional `heroImage`.
  - In the body, `## Section name` becomes the numbered label and the "On this page" link. The `### Statement` below it is the big line.
  - The components `<Insights>`, `<Placeholder>`, `<Reflection>`, `<Screens>` and `<Action>` are in `src/components/case/`.
- **Featured cards 02 and 03:** `project-two.md` and `project-three.md` render as cards without links. Once a case study is written, set `published: true`. "The whole shelf →" shows up automatically when more than three are published, so `/work` has to exist by then.
- **Images:** put them in `src/assets/` and reference them from MDX or frontmatter. Astro outputs AVIF and WebP versions.

## House poster

`npm run poster` runs `scripts/make-poster.py`. It crops the 2400×1800 renders in `design/assets/house/` down to the drawing's bounding box, writes them to `src/assets/house/`, and records the crop box in `crop.json` so the hotspot anchors (% of the full image) can be mapped onto the cropped image. Re-run it whenever the generator's output changes.

## Tokens

`src/styles/global.css` mirrors `design/tokens.json`. Headings scale fluidly down to phone width. At 1280px and above they hit the token sizes exactly (H1 76, H2 48, lead 22).

## Next: milestone 2

- Replace `/house` with the React Three Fiber island (`@astrojs/react`, `three`, `@react-three/fiber`, `@react-three/drei`, `zustand`).
- In the hero, keep the `<Picture>` poster as the first paint. Load the island after idle, only while the hero is visible, and crossfade it in. Skip auto-load for Save-Data, slow connections, low memory, reduced motion, and `html[data-mode="focus"]`.
- "Open in the studio" on case studies already links to `/house?room=studio`.
