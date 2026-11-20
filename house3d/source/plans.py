"""Compact 1-person house plans, in metres. Plan convention: x right, y down;
the top-left corner is the back of the house in the hero (camera looks from the bottom-right).
A room is (key, label, kind, [rects]); rect = (x, y, w, d). Doors are (x, y, axis, width):
a gap centred at (x, y) on a wall running along `axis` ('x' = horizontal wall)."""
import math
import numpy as np
from PIL import Image, ImageDraw

M2U = 1 / 0.41           # metres -> scene units (character is 4.1 units ≈ 1.7 m)
WALL_M = 4.2 * 0.41      # diorama wall height in metres

COL = dict(living="#f0e3cd", studio="#e9dcc6", lab="#ddd6c8", bedroom="#e2ddd2", hall="#ecd3a9",
           garden="#b9cf95", entry="#e6d2b4", porch="#d9cfbf")


def area(room):
    return sum(w * d for (_, _, w, d) in room[3])


def silhouette(plan, px=8):
    """projected outline of the walls' prism at the hero camera (az 45, el 30)."""
    a, e = math.radians(45), math.radians(30)
    r = np.array([math.sin(a), -math.cos(a), 0]); dn = np.array([math.sin(e) * math.cos(a), math.sin(e) * math.sin(a), -math.cos(e)])
    polys = []
    for room in plan["rooms"]:
        for (x, y, w, d) in room[3]:
            z = 0 if room[2] in ("garden", "porch") else WALL_M
            for zz in sorted({0, z}):
                pts = np.array([(x, y, zz), (x + w, y, zz), (x + w, y + d, zz), (x, y + d, zz)])
                polys.append(np.stack([pts @ r, pts @ dn], 1))
            if z:   # side faces
                for (p, q) in [((x, y), (x + w, y)), ((x + w, y), (x + w, y + d)), ((x + w, y + d), (x, y + d)), ((x, y + d), (x, y))]:
                    pts = np.array([(*p, 0), (*q, 0), (*q, z), (*p, z)])
                    polys.append(np.stack([pts @ r, pts @ dn], 1))
    allp = np.concatenate(polys)
    mn, mx = allp.min(0), allp.max(0)
    W, H = int((mx[0] - mn[0]) * px) + 2, int((mx[1] - mn[1]) * px) + 2
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    for p in polys:
        d.polygon([tuple(((q - mn) * px).tolist()) for q in p], fill=255)
    m = np.array(im) > 0
    cols = m.sum(0)
    mid = W / 2
    left, right = cols[: int(mid)].sum(), cols[int(mid):].sum()
    ys, xs = np.nonzero(m)
    cx = xs.mean() / W
    s = min(860 / W, 660 / H)
    return dict(aspect=W / H, balance=left / (left + right), cx=cx, fill=m.mean(), hero_w=W * s, hero_h=H * s, mask=im)


def stats(plan):
    rooms = plan["rooms"]
    inside = sum(area(r) for r in rooms if r[2] not in ("garden", "porch"))
    garden = sum(area(r) for r in rooms if r[2] == "garden")
    sil = silhouette(plan)
    return dict(inside=inside, garden=garden, **{k: v for k, v in sil.items() if k != "mask"}), sil["mask"]


# ------------------------------------------------------------------ the plans
PLANS = {}


def apron(rooms, depth=1.2):
    """lawn strips along every exposed front edge (x = x0 + w, y = y0 + d) of the indoor rooms."""
    rects = [(r[2], rr) for r in rooms for rr in r[3]]
    def inside(px, py):
        return any(x < px < x + w and y < py < y + d for _, (x, y, w, d) in rects)
    out = []
    for kind, (x, y, w, d) in rects:
        if kind in ("garden", "porch"):
            continue
        for ax in ("x", "y"):
            n = int(round((d if ax == "x" else w) / .5))
            run = None
            for i in range(n + 1):
                free = i < n and not (inside(x + w + .1, y + i * .5 + .25) if ax == "x" else inside(x + i * .5 + .25, y + d + .1))
                if free and run is None:
                    run = i
                if not free and run is not None:
                    a, b = run * .5, i * .5
                    out.append((x + w, y + a, depth, b - a) if ax == "x" else (x + a, y + d, b - a, depth))
                    run = None
        # corner
        if not inside(x + w + .1, y + d + .1):
            out.append((x + w, y + d, depth, depth))
    return ("apron", "Lawn", "garden", out)


def plan(key, name, idea, lawn=False):
    def deco(f):
        p = f()
        if lawn:
            p["rooms"].append(apron(p["rooms"]))
        p.update(key=key, name=name, idea=idea); PLANS[key] = p
        return f
    return deco


@plan("P1", "Open arms", "The house opens its arms to you. Living room at the back corner, one wing for work (studio, lab), one for night (bedroom, entry), and a deck along both wings around a garden in the crook.")
def _():
    return dict(rooms=[
        ("living", "Living", "living", [(0, 0, 5, 5)]),
        ("studio", "Studio", "studio", [(5, 0, 3.5, 3)]),
        ("lab", "Lab", "lab", [(8.5, 0, 3, 3)]),
        ("bedroom", "Bedroom", "bedroom", [(0, 5, 3, 4.5)]),
        ("entry", "Entry", "entry", [(0, 9.5, 3, 2)]),
        ("deckR", "Deck", "porch", [(5, 3, 6.5, 2)]),
        ("deckL", "Deck", "porch", [(3, 5, 2, 6.5)]),
        ("endR", "Deck", "porch", [(11.5, 0, 1.3, 5)]),
        ("endL", "Deck", "porch", [(0, 11.5, 5, 1.3)]),
        ("garden", "Garden", "garden", [(5, 5, 4.5, 4.5)]),
    ], doors=[(5, 1.5, "y", .9), (6.75, 3, "x", .9), (10, 3, "x", .9), (11.5, 1.5, "y", .9), (5, 4, "y", 1.4), (4, 5, "x", 1.4),
              (1.5, 5, "x", .9), (1.5, 9.5, "x", .9), (3, 10.5, "y", .9), (1.5, 11.5, "x", .9)])


@plan("P2", "Pinwheel", "The living room is the hub and four wings turn around it like a pinwheel. Every room opens straight off the living room, the bedroom takes the quiet back wing, three of the notches between wings hold a small pocket garden, the fourth is a workout deck off the living room and studio, and the big garden sits at the front.")
def _():
    return dict(rooms=[
        ("living", "Living", "living", [(3, 3, 5, 5)]),
        ("bedroom", "Bedroom", "bedroom", [(1.5, 0, 4.5, 3)]),
        ("studio", "Studio", "studio", [(0, 4.5, 3, 4)]),
        ("lab", "Lab", "lab", [(8, 1.5, 3, 4.5)]),
        ("deck", "Deck", "porch", [(11, 1.5, 1.5, 4.5)]),
        ("garden", "Garden", "garden", [(4.5, 8, 4.5, 3.5)]),
        ("deckS", "Workout deck", "porch", [(0, 8.5, 3, 1.5), (3, 8, 1.5, 3.5)]),
        ("pocketNW", "Entry court", "garden", [(0, 3, 3, 1.5)]),
        ("pocketNE", "Pocket", "garden", [(6, 0, 2, 3)]),
        ("pocketSE", "Pocket", "garden", [(8, 6, 3, 2)]),
    ], doors=[(3, 3.75, "y", .9), (4.5, 3, "x", .9), (3, 5.0, "y", .9), (8, 4.5, "y", .9), (7.25, 8, "x", 1.4), (11, 3.75, "y", .9), (3.5, 8, "x", .9)],
       stair=dict(shape="L", rects=[(-1.5, 3, 1.5, 1.5), (-3, 3, 1.5, 1.5), (-3, 1.5, 1.5, 1.5)]), path=0, props=False)


@plan("P3", "Cross", "A plus. The living room is the crossing; studio and bedroom are the two back arms, the lab is the front-right arm and the garden is the front-left arm, its tree balancing the lab.", lawn=True)
def _():
    return dict(rooms=[
        ("living", "Living", "living", [(3, 3, 5, 5)]),
        ("studio", "Studio", "studio", [(3.5, 0, 4, 3)]),
        ("bedroom", "Bedroom", "bedroom", [(0, 3.5, 3, 4)]),
        ("lab", "Lab", "lab", [(8, 3.5, 3.5, 4)]),
        ("deck", "Deck", "porch", [(8, 7.5, 3.5, 1.3)]),
        ("garden", "Garden", "garden", [(3.5, 8, 4.5, 3.5)]),
    ], doors=[(5.5, 3, "x", .9), (3, 5.5, "y", .9), (8, 5.5, "y", .9), (5.5, 8, "x", 1.6), (9.75, 7.5, "x", .9)])


@plan("P4", "Courtyard", "A small courtyard garden tucked into the house. The living room wraps its back as an L; studio, lab and bedroom each open straight off the living room and look into the courtyard.", lawn=True)
def _():
    return dict(rooms=[
        ("living", "Living", "living", [(0, 0, 7.5, 3), (0, 3, 3.5, 3.5)]),
        ("studio", "Studio", "studio", [(7.5, 0, 3, 3)]),
        ("lab", "Lab", "lab", [(6.5, 3, 3.5, 3.5)]),
        ("bedroom", "Bedroom", "bedroom", [(0, 6.5, 3.5, 4)]),
        ("garden", "Garden", "garden", [(3.5, 3, 3, 3.5), (3.5, 6.5, 2.5, 1.5)]),
    ], doors=[(0, 1.5, "y", .9), (7.5, 1.5, "y", .9), (7, 3, "x", .9), (1.75, 6.5, "x", .9), (3.5, 4.75, "y", 1.6), (5, 3, "x", 1.4), (6.5, 5.5, "y", .9), (3.5, 7.25, "y", .9)])


@plan("P5", "Two pavilions", "Day and night in two small blocks. The day pavilion (living, studio, lab) sits at the back; the bedroom pavilion sits across the garden, reached by a short glass link.", lawn=True)
def _():
    return dict(rooms=[
        ("studio", "Studio", "studio", [(0, 0, 3.5, 3)]),
        ("living", "Living", "living", [(0, 3, 5.5, 5)]),
        ("lab", "Lab", "lab", [(3.5, 0, 3, 3)]),
        ("link", "Link", "hall", [(5.5, 3, 1.3, 4)]),
        ("bedroom", "Bedroom", "bedroom", [(6.8, 3, 4, 4)]),
        ("garden", "Garden", "garden", [(1.5, 8, 5.3, 2.5), (6.8, 7, 4, 3.5)]),
    ], doors=[(0, 7.3, "y", .9), (1.75, 3, "x", .9), (4.0, 3, "x", .9), (5.5, 6.5, "y", .9), (6.8, 5, "y", .9), (3, 8, "x", 1.6), (8.8, 7, "x", 1.4)])


@plan("P6", "Terrace", "Rooms step down the slope of the hero like terraces, each one half a room further forward, with a planted step in front of each.", lawn=True)
def _():
    return dict(rooms=[
        ("bedroom", "Bedroom", "bedroom", [(0, 0, 4, 3.5)]),
        ("living", "Living", "living", [(2, 3.5, 5.5, 5)]),
        ("studio", "Studio", "studio", [(4, 0, 3.5, 3.5)]),
        ("lab", "Lab", "lab", [(7.5, 3.5, 3, 3.5)]),
        ("gardenL", "Garden", "garden", [(.5, 3.5, 1.5, 5), (2, 8.5, 3.5, 1.5)]),
        ("gardenR", "Garden", "garden", [(10.5, 3.5, 1.5, 3.5)]),
        ("deck", "Deck", "porch", [(5.5, 8.5, 2, 1.5), (7.5, 7, 3, 1.5)]),
    ], doors=[(2.75, 3.5, "x", .9), (5.75, 3.5, "x", .9), (7.5, 5.25, "y", .9), (2, 5.0, "y", 1.4), (6.5, 8.5, "x", 1.4)])


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "pl"
    import os; os.makedirs(out, exist_ok=True)
    S = 34
    tiles = []
    for k, p in PLANS.items():
        st, mask = stats(p)
        xs = [x + w for r in p["rooms"] for (x, y, w, d) in r[3]]; ys = [y + d for r in p["rooms"] for (x, y, w, d) in r[3]]
        im = Image.new("RGB", (900, 520), "#f4eee4"); d = ImageDraw.Draw(im)
        for r in p["rooms"]:
            for (x, y, w, dd) in r[3]:
                d.rectangle((20 + x * S, 40 + y * S, 20 + (x + w) * S, 40 + (y + dd) * S), fill=COL[r[2]], outline="#1b1a17", width=2)
            x, y, w, dd = r[3][0]
            d.text((26 + x * S, 46 + y * S), f"{r[1]} {area(r):.0f}", fill="#1b1a17")
        for (x, y, ax, w) in p["doors"]:
            if ax == "x":
                d.line((20 + (x - w / 2) * S, 40 + y * S, 20 + (x + w / 2) * S, 40 + y * S), fill="#c8442b", width=5)
            else:
                d.line((20 + x * S, 40 + (y - w / 2) * S, 20 + x * S, 40 + (y + w / 2) * S), fill="#c8442b", width=5)
        d.text((20, 10), f"{k} {p['name']}  inside {st['inside']:.0f} m2  garden {st['garden']:.0f}  aspect {st['aspect']:.2f}  balance {st['balance']:.2f}  hero {st['hero_w']:.0f}x{st['hero_h']:.0f}", fill="#1b1a17")
        m = mask.convert("RGB"); m.thumbnail((440, 300)); im.paste(m, (450, 120))
        tiles.append(im); print(k, {a: (round(b, 2) if isinstance(b, float) else b) for a, b in st.items()})
    G = Image.new("RGB", (1800, 520 * ((len(tiles) + 1) // 2)), "white")
    for i, t in enumerate(tiles):
        G.paste(t, ((i % 2) * 900, (i // 2) * 520))
    G.save(f"{out}/_plans.png")
