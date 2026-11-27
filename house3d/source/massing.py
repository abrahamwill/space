"""3D massing preview of a plan from plans.py: floors, cut walls, garden. No furniture.
Outer back walls stand full height; walls between rooms are cut low like a dollhouse;
walls onto the garden are glazed; garden edges get a low hedge."""
import math
import numpy as np
from engine import Part, poly, box, Cam, render
from layouts import internal, garden as garden_patch, stones, shrub, planks
from scene import P, H, HP, T
from plans import PLANS, M2U

FLOOR = dict(living=(P["floor"], P["plank"]), studio=(P["floor"], P["plank"]), lab=(P["lab"],), bedroom=(P["bfloor"], P["bplank"], True),
             hall=("#d7a873", "#c99a68", True), entry=("#d7a873",), porch=("#c9a67a", "#b8956a", True))
OPEN = ("garden", "porch")


def U(v):
    return v * M2U


def build(plan):
    rects = []
    for key, label, kind, rs in plan["rooms"]:
        for (x, y, w, d) in rs:
            rects.append(dict(key=key, kind=kind, rect=(U(x), U(y), U(w), U(d))))

    def who(px, py):
        for r in rects:
            x0, y0, w, d = r["rect"]
            if x0 < px < x0 + w and y0 < py < y0 + d:
                return r
        return None
    doors = [(U(x), U(y), ax, U(w)) for (x, y, ax, w) in plan["doors"]]
    g = Part()
    # floors
    for r in rects:
        x0, y0, w, d = r["rect"]
        if r["kind"] == "garden":
            continue
        f = FLOOR[r["kind"]]
        g = g + poly([(x0, y0, 0), (x0 + w, y0, 0), (x0 + w, y0 + d, 0), (x0, y0 + d, 0)], f[0])
        if len(f) > 1:
            g = g + planks(x0, y0, x0 + w, y0 + d, f[1], alongx=len(f) > 2, step=.9 if len(f) > 2 else 1.1)
    # walls along each rect's back edges (x = x0 and y = y0)
    for r in rects:
        x0, y0, w, d = r["rect"]
        for ax, k, a0, a1 in (("x", x0, y0, y0 + d), ("y", y0, x0, x0 + w)):
            n = max(1, int(round((a1 - a0) / .2)))
            step = (a1 - a0) / n
            labs = []
            for i in range(n):
                m = a0 + (i + .5) * step
                labs.append(who(k - .2, m) if ax == "x" else who(m, k - .2))
            i = 0
            while i < n:
                j = i
                while j < n and labs[j] is labs[i]:
                    j += 1
                a, b, nb = a0 + i * step, a0 + j * step, labs[i]
                i = j
                if nb is not None and nb["key"] == r["key"]:
                    continue
                if nb is None:
                    if r["kind"] in OPEN:          # garden / deck edge: low hedge
                        if r["kind"] == "garden" and r["key"] != "apron":
                            hb = box(k - .7, a, 0, .7, b - a, .9, "#5a8a3a", "#6d9a48") if ax == "x" else box(a, k - .7, 0, b - a, .7, .9, "#5a8a3a", "#6d9a48")
                            g = g + hb
                        continue
                    ea, eb = a - (T if abs(a - a0) < 1e-6 else 0), b + (T if abs(b - a1) < 1e-6 else 0)
                    g = g + (box(k - T, ea, 0, T, eb - ea, H, P["wall"], P["top"]) if ax == "x" else box(ea, k - T, 0, eb - ea, T, H, P["wall"], P["top"]))
                    continue
                if r["kind"] in OPEN and nb["kind"] in OPEN:
                    continue
                if "apron" in (r["key"], nb["key"]):      # cutaway front: no wall, just a low sill
                    g = g + (box(k - .12, a, 0, .24, b - a, .3, P["wall"], P["top"]) if ax == "x" else box(a, k - .12, 0, b - a, .24, .3, P["wall"], P["top"]))
                    continue
                gaps = []
                for (dx, dy, dax, dw) in doors:
                    # loop axis "x" = the wall at x = k (runs along y): plans.py marks those doors "y"
                    if ax == "x":
                        on, c = dax == "y" and abs(dx - k) < .3, dy
                    else:
                        on, c = dax == "x" and abs(dy - k) < .3, dx
                    if on and a - .1 <= c <= b + .1:
                        gaps.append((c - dw / 2, c + dw / 2))
                kind = "glass" if (r["kind"] in OPEN or nb["kind"] in OPEN) else "low"
                g = g + internal(ax, k, a, b, dict(kind=kind, gaps=gaps), P["wall"], P["wall"])
    # garden dressing
    for r in rects:
        if r["kind"] != "garden":
            continue
        x0, y0, w, d = r["rect"]
        big = r["key"] != "apron" and w * d == max(rr["rect"][2] * rr["rect"][3] for rr in rects if rr["kind"] == "garden" and rr["key"] != "apron")
        g = g + garden_patch(x0, y0, w, d, seed=int(x0 * 3 + y0),
                             tree_at=(x0 + w * .45, y0 + d * .45, .62) if big else None,
                             pond=(x0 + w * .72, y0 + d * .72, min(w, d) * .14, min(w, d) * .1) if big and min(w, d) > 7 else None)
        if r["key"] != "apron":
            g = g + shrub(x0 + w * .82, y0 + d * .22, .55) + shrub(x0 + w * .18, y0 + d * .8, .5)
    return g, rects


def masks(rects):
    out = []
    for r in rects:
        x0, y0, w, d = r["rect"]
        q = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + d), (x0, y0 + d)]
        if r["kind"] in OPEN:
            out.append([(a, b, 0) for a, b in q])
            # keep anything standing in the garden (tree, hedge): extrude the outline upward
            out.append([(x0, y0, 0), (x0 + w, y0, 0), (x0 + w, y0, H * 1.6), (x0, y0, H * 1.6)])
            out.append([(x0, y0, 0), (x0, y0 + d, 0), (x0, y0 + d, H * 1.6), (x0, y0, H * 1.6)])
            out.append([(x0, y0, H * 1.6), (x0 + w, y0, H * 1.6), (x0 + w, y0 + d, H * 1.6), (x0, y0 + d, H * 1.6)])
        else:
            out.append([(a, b, H) for a, b in q])
    return out


def render_plan(key, W=1720, Hh=1320, ss=2, pad=40):
    plan = PLANS[key]
    g, rects = build(plan)
    cam = Cam(45, 30)
    q = cam.proj(g.t.reshape(-1, 3))
    x0, x1, y0, y1 = q[:, 0].min(), q[:, 0].max(), q[:, 1].min(), q[:, 1].max()
    sc = min((W - 2 * pad) / (x1 - x0), (Hh - 2 * pad) / (y1 - y0))
    c = (x0 + x1) / 2 * cam.r + (y0 + y1) / 2 * cam.dn
    im, _ = render(g, cam, W, Hh, sc, c, ss=ss, mask_poly=masks(rects))
    return im


if __name__ == "__main__":
    import sys, os
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    keys = sys.argv[2].split(",") if len(sys.argv) > 2 else list(PLANS)
    W, Hh, ss = (int(v) for v in (sys.argv[3:6] if len(sys.argv) > 5 else (1720, 1320, 2)))
    for k in keys:
        im = render_plan(k, W, Hh, ss)
        a = np.array(im)[..., 3]; ys, xs = np.nonzero(a > 8)
        im.crop((xs.min() - 12, ys.min() - 12, xs.max() + 12, ys.max() + 12)).save(f"{out}/mass_{k}.png")
        print(k, flush=True)


def visibility(key, ppu=6):
    """share of each room's floor the hero camera actually shows (rim + walls + furniture-free)."""
    from engine import raster
    from PIL import ImageDraw, Image
    plan = PLANS[key]
    g, rects = build(plan)
    ids = []
    floor = Part()
    for i, r in enumerate(rects):
        x0, y0, w, d = r["rect"]
        floor = floor + poly([(x0, y0, .03), (x0 + w, y0, .03), (x0 + w, y0 + d, .03), (x0, y0 + d, .03)], "#000000")
        ids += [i, i]
    allp = g + floor
    tag = np.full(len(allp.t), -1); tag[len(g.t):] = ids
    cam = Cam(45, 30)
    P3 = cam.proj(allp.t.reshape(-1, 3)).reshape(-1, 3, 3)
    mn = P3[..., :2].reshape(-1, 2).min(0) - 1
    xy = (P3[..., :2] - mn) * ppu
    Wd, Hd = int(xy[..., 0].max()) + 3, int(xy[..., 1].max()) + 3
    zb, ib = raster(xy, P3[..., 2], Wd, Hd)
    mask = Image.new("L", (Wd, Hd), 0); md = ImageDraw.Draw(mask)
    for pl in masks(rects):
        mp = cam.proj(np.asarray(pl, float)); md.polygon([tuple(((p[:2] - mn) * ppu).tolist()) for p in mp], fill=255)
    vis = (np.array(mask) > 0) & (ib >= 0)
    hit = tag[ib[vis]]
    out = {}
    for i, r in enumerate(rects):
        x0, y0, w, d = r["rect"]
        exp = w * d * math.sin(math.radians(30)) * ppu * ppu
        out.setdefault(r["key"], [0, 0]); out[r["key"]][0] += (hit == i).sum(); out[r["key"]][1] += exp
    return {k: v[0] / v[1] for k, v in out.items()}


def hero_metrics(im):
    a = np.array(im)[..., 3] > 8
    ys, xs = np.nonzero(a); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = a.shape; cols = a.sum(0)
    bal = cols[: w // 2].sum() / cols.sum()
    s = min(860 / w, 660 / h)
    return dict(aspect=w / h, balance=bal, hero_w=w * s, hero_h=h * s)
