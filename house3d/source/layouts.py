"""Layout explorations. Rooms are modules lifted from scene.py, placed (and optionally mirrored
across the diagonal, which keeps back-wall decor on back walls) into new floor plans.
Walls come from adjacency: exterior back walls are full height; internal walls follow WALLS."""
import math
from collections import defaultdict
import numpy as np
from engine import Part, poly, box, cyl, ico, rod, disc, hull, cham, cbox, qx, qy, cx_, cy_
import scene as SC
from scene import P, H, HP, T, planks, fiddle, frame_x, frame_y

ORIGIN = {"studio": (0, 0), "living": (0, 9), "lab": (18, 4), "bedroom": (18, 20), "treadmill": (0, 9), "person": (0, 9)}
TAGMAP = {"studio": {"y0": "y0", "x0": "x0"}, "living": {"x0": "x0", "y9": "y0"}, "lab": {"y4": "y0"},
          "treadmill": {"y28": "front"}, "bedroom": {"x31b": "front"}}


def swap(p):
    return Part(p.t[..., [1, 0, 2]], p.c, p.e)


def modules(state="wave"):
    sc = SC.build_scene(state)
    out = defaultdict(list)
    for (p, tag), sec in zip(sc.parts, sc.secs):
        if sec == "shell":
            continue
        ox, oy = ORIGIN[sec]
        loc = p.move(-ox, -oy, 0)
        t = TAGMAP.get(sec, {}).get(tag) if tag else None
        if t is None and len(loc.t):
            mn, mx = loc.t.reshape(-1, 3).min(0), loc.t.reshape(-1, 3).max(0)
            if sec == "treadmill" and mn[2] > 2.0:
                t = "front"                      # medal hanger sat on the old bedroom wall
            elif mx[0] < .6 and mn[2] > 1.2:
                t = "x0"
            elif mx[1] < .6 and mn[2] > 1.2:
                t = "y0"
        out[sec].append((loc, t))
    return out


def place(mods, sec, x, y, mirror=False, drop=()):
    g = Part()
    for p, t in mods[sec]:
        if mirror:
            p = swap(p); t = {"x0": "y0", "y0": "x0"}.get(t, t)
        if t == "front" or t in drop:
            continue
        g = g + p.move(x, y, 0)
    return g


# ---------------- generic rooms ----------------
def runner(x0, y0, x1, y1, axis):
    g = poly([(x0, y0, .015), (x1, y0, .015), (x1, y1, .015), (x0, y1, .015)], "#b84a32")
    if axis == "x":
        g = g + poly([(x0 + .25, y0 + .25, .02), (x1 - .25, y0 + .25, .02), (x1 - .25, y1 - .25, .02), (x0 + .25, y1 - .25, .02)], "#d9a066")
        k = x0 + .8
        while k < x1 - .8:
            g = g + poly([(k, y0 + .25, .025), (k + .25, y0 + .25, .025), (k + .25, y1 - .25, .025), (k, y1 - .25, .025)], "#b84a32"); k += 1.2
    else:
        g = g + poly([(x0 + .25, y0 + .25, .02), (x1 - .25, y0 + .25, .02), (x1 - .25, y1 - .25, .02), (x0 + .25, y1 - .25, .02)], "#d9a066")
        k = y0 + .8
        while k < y1 - .8:
            g = g + poly([(x0 + .25, k, .025), (x1 - .25, k, .025), (x1 - .25, k + .25, .025), (x0 + .25, k + .25, .025)], "#b84a32"); k += 1.2
    return g


def tree(cx, cy, s=1.0):
    g = cyl(cx, cy, 0, .22 * s, 2.6 * s, "#7a4a2a", n=7)
    for i, (dx, dy, dz, r) in enumerate([(0, 0, 3.2, 1.5), (-.9, .4, 2.7, 1.0), (.8, -.5, 2.9, 1.05), (.2, .7, 3.9, 1.0), (-.3, -.6, 3.8, .9)]):
        g = g + ico((cx + dx * s, cy + dy * s, dz * s), r * s, "#5f8f3e" if i % 2 else "#4c7a33", 1, seed=i + 3, jit=.15)
    return g


def shrub(cx, cy, r=.6, col="#5a8a3a"):
    return ico((cx, cy, r * .7), r, col, 1, (1, 1, .75), seed=abs(int(cx * 7 + cy)), jit=.15)


def garden(x0, y0, w, d, seed=1, tree_at=None, pond=None, bench=None):
    g = poly([(x0, y0, 0), (x0 + w, y0, 0), (x0 + w, y0 + d, 0), (x0, y0 + d, 0)], "#8fb062")
    rng = np.random.default_rng(seed)
    for _ in range(int(w * d / 6)):
        px, py = x0 + rng.uniform(.3, w - .3), y0 + rng.uniform(.3, d - .3)
        g = g + disc(px, py, .006, rng.uniform(.25, .5), "#7fa356", n=6)
    if pond:
        px, py, rx, ry = pond
        g = g + disc(px, py, .01, rx + .25, "#cdbf9f", n=16, ry=ry + .25) + disc(px, py, .02, rx, "#6fa3c4", n=16, ry=ry, emis=False)
    if tree_at:
        g = g + tree(*tree_at)
    if bench:
        bx, by, along = bench
        if along == "x":
            g = g + box(bx, by, .55, 2.4, .7, .14, P["wal"], P["walT"]) + box(bx + .1, by + .1, 0, .2, .5, .55, P["walD"]) + box(bx + 2.1, by + .1, 0, .2, .5, .55, P["walD"])
        else:
            g = g + box(bx, by, .55, .7, 2.4, .14, P["wal"], P["walT"]) + box(bx + .1, by + .1, 0, .5, .2, .55, P["walD"]) + box(bx + .1, by + 2.1, 0, .5, .2, .55, P["walD"])
    return g


def stones(pts):
    g = Part()
    for (x, y) in pts:
        g = g + cyl(x, y, 0, .38, .05, "#e8e0cf", n=8)
    return g


def running_wall_y(Y, x0, x1):
    """photos + medals on a wall plane y=Y facing +y"""
    g = Part()
    frames = [(0, .9, 2.55, 3.45, P["ink"], "#8fb3c9"), (1.1, 1.9, 2.75, 3.6, "#f3f1ec", "#c9a27a"), (2.1, 3.0, 2.5, 3.3, P["ink"], "#9db07f"),
              (.2, 1.0, 1.6, 2.3, "#f3f1ec", "#d98b6a"), (1.3, 2.4, 1.55, 2.4, P["walT"], "#6f8fb5")]
    for (a, b, z0, z1, fc, pc) in frames:
        g = g + frame_y(Y, x0 + a, x0 + b, z0, z1, fc, pc, sgn=1)
    g = g + qy(Y + .05, x0 + 3.3, x0 + 4.1, 2.2, 2.9, "#fbfaf6") + qy(Y + .06, x0 + 3.4, x0 + 4.0, 2.6, 2.75, P["ink"]) + qy(Y + .06, x0 + 3.4, x0 + 4.0, 2.38, 2.45, P["red"])
    mx0 = x0 + 4.5
    g = g + box(mx0, Y + .02, 3.5, x1 - mx0, .14, .14, "#1d1d1f")
    rib = [P["red"], P["cob"], P["mus"], "#f3f1ec"]; met = ["#d9a93a", "#c9c9c4", "#d9a93a", "#b0703c"]
    k, x = 0, mx0 + .3
    while x < x1 - .2:
        zb = 2.75 - (.18 if k % 2 else 0)
        g = g + qy(Y + .08, x - .08, x + .08, zb + .18, 3.5, rib[k % 4])
        g = g + cyl(0, 0, 0, .2, .06, met[k % 4], n=12).rot("x", 90).move(x, Y + .14, zb)
        x += .5; k += 1
    return g


def treadmill_x(x, y):
    """treadmill running along +x, belt x..x+4.2, y..y+1.9, console at the high-x end"""
    tm = box(15.35, 23.4, 0, 1.9, 4.2, .32, "#3b3b3e", "#4a4a4e")
    tm = tm + poly([(15.55, 23.55, .33), (17.05, 23.55, .33), (17.05, 26.9, .33), (15.55, 26.9, .33)], "#1d1d1f")
    for X in (15.34, 17.26):
        tm = tm + qx(X, 23.7, 26.7, .12, .2, P["red"])
    tm = tm + box(15.35, 26.9, 0, 1.9, .7, .6, "#2e2e31", "#3b3b3e")
    for x0, x1 in ((15.5, 15.6), (17.1, 17.0)):
        tm = tm + rod((x0, 27.3, .55), (x1, 27.65, 2.5), .07, "#55555a") + rod((x1, 27.55, 2.2), (x1, 25.9, 2.15), .05, "#9b9b96")
    con = box(15.55, 27.35, 2.42, 1.5, .5, .18, "#2b2b2e") + poly([(15.75, 27.45, 2.605), (17.05, 27.45, 2.605), (17.05, 27.75, 2.605), (15.75, 27.75, 2.605)], P["mus"], True)
    tm = tm + con.rot("x", 28, (16.3, 27.6, 2.5))
    return swap(tm.move(-15.35, -23.4, 0)).move(x, y, 0)


def reading_nook(x, y):
    g = cbox(x + .8, y + .8, .55, .75, .75, .3, .15, "#c49c60") + cbox(x + .2, y + .8, 1.3, .15, .75, .55, .1, "#c49c60")
    g = g + tube_lamp(x + .3, y + 2.0)
    return g


def tube_lamp(x, y):
    return box(x - .06, y - .06, 0, .12, .12, 2.8, P["chr"]) + cyl(x, y, 0, .35, .06, P["chr"], n=8) + ico((x, y, 3.0), .38, "#f4e2b8", 1, emis=True)


# ---------------- walls ----------------
def build_walls(rooms, walls):
    def who(px, py):
        for r in rooms:
            x0, y0, w, d = r["rect"]
            if x0 < px < x0 + w and y0 < py < y0 + d:
                return r["name"]
        return None
    col = {r["name"]: r.get("wall", P["wall"]) for r in rooms}
    out = Part()
    for r in rooms:
        x0, y0, w, d = r["rect"]
        for ax, k, a0, a1 in (("x", x0, y0, y0 + d), ("y", y0, x0, x0 + w)):
            n = int(round((a1 - a0) / .25))
            labels = [who(k - .25, a0 + (i + .5) * .25) if ax == "x" else who(a0 + (i + .5) * .25, k - .25) for i in range(n)]
            i = 0
            while i < n:
                j = i
                while j < n and labels[j] == labels[i]:
                    j += 1
                a, b, nb = a0 + i * .25, a0 + j * .25, labels[i]
                i = j
                if nb == r["name"]:
                    continue
                if nb is None:
                    ea = a - (T if abs(a - a0) < 1e-6 else 0); eb = b + (T if abs(b - a1) < 1e-6 else 0)
                    if ax == "x":
                        out = out + box(k - T, ea, 0, T, eb - ea, H, col[r["name"]], P["top"])
                    else:
                        out = out + box(ea, k - T, 0, eb - ea, T, H, col[r["name"]], P["top"])
                    continue
                spec = walls.get((r["name"], nb)) or walls.get((nb, r["name"])) or {"kind": "low"}
                out = out + internal(ax, k, a, b, spec, col[nb], col[r["name"]])
    return out


def internal(ax, k, a, b, spec, colBack, colFront):
    kind, gaps = spec["kind"], [g for g in spec.get("gaps", []) if g[1] > a and g[0] < b]
    if kind == "open":
        return Part()
    segs, cur = [], a
    for g0, g1 in sorted(gaps):
        segs.append((cur, max(cur, g0))); cur = min(b, g1)
    segs.append((cur, b))
    def bx(s0, s1, z0, z1, c, side):
        t0 = k - T / 2 if side == 0 else k
        if ax == "x":
            return box(t0, s0, z0, T / 2, s1 - s0, z1 - z0, c, P["top"])
        return box(s0, t0, z0, s1 - s0, T / 2, z1 - z0, c, P["top"])
    out = Part()
    if kind in ("full", "low"):
        zt = H if kind == "full" else HP
        for s0, s1 in segs:
            if s1 > s0:
                out = out + bx(s0, s1, 0, zt, colBack, 0) + bx(s0, s1, 0, zt, colFront, 1)
        if kind == "full":
            for g0, g1 in gaps:
                out = out + bx(g0, g1, 3.15, H, colBack, 0) + bx(g0, g1, 3.15, H, colFront, 1)
    elif kind == "glass":     # low sill, slim posts, top beam: reads as a glazed wall you can see through
        fr = "#ead9bf"
        for s0, s1 in segs:
            if s1 <= s0:
                continue
            out = out + bx(s0, s1, 0, .6, colBack, 0) + bx(s0, s1, 0, .6, colFront, 1)
            nposts = max(1, int(round((s1 - s0) / 3.2)))
            for i in range(nposts + 1):
                p = s0 + (s1 - s0) * i / nposts
                if spec.get("no_end_posts") and (abs(p - a) < 1e-6 or abs(p - b) < 1e-6):
                    continue
                out = out + (box(k - .05, p - .05, .6, .1, .1, H - .6, fr) if ax == "x" else box(p - .05, k - .05, .6, .1, .1, H - .6, fr))
        out = out + (box(k - .07, a, H - .14, .14, b - a, .14, fr) if ax == "x" else box(a, k - .07, H - .14, b - a, .14, .14, fr))
    return out


def floors(rooms):
    out = Part()
    for r in rooms:
        x0, y0, w, d = r["rect"]
        f = r.get("floor")
        if f is None:
            continue
        out = out + poly([(x0, y0, 0), (x0 + w, y0, 0), (x0 + w, y0 + d, 0), (x0, y0 + d, 0)], f[0])
        if len(f) > 1:
            out = out + planks(x0, y0, x0 + w, y0 + d, f[1], alongx=f[2] if len(f) > 2 else False, step=.9 if (len(f) > 2 and f[2]) else 1.1)
    return out


OAK = (P["floor"], P["plank"]); LABF = (P["lab"],); BEDF = (P["bfloor"], P["bplank"], True); HALLF = ("#d7a873", "#c99a68", True)


# ---------------- the options ----------------
def layout_A(state="wave"):
    """Gallery diamond: living at the top, lab right, studio left, bedroom at the front,
    an L-shaped gallery hall wrapping the bedroom (running wall + treadmill nook)."""
    M = modules(state)
    rooms = [dict(name="living", rect=(0, 0, 19, 19), floor=OAK), dict(name="lab", rect=(19, 0, 13, 16), floor=LABF),
             dict(name="studio", rect=(0, 19, 16, 13), floor=OAK), dict(name="bedroom", rect=(19, 19, 13, 13), floor=BEDF, wall=P["bwall"]),
             dict(name="hallA", rect=(19, 16, 13, 3), floor=HALLF), dict(name="hallB", rect=(16, 19, 3, 13), floor=HALLF)]
    walls = {("lab", "living"): dict(kind="low", gaps=[(10.5, 14.5)]), ("studio", "living"): dict(kind="full", gaps=[(10.6, 13.4)]),
             ("hallA", "lab"): dict(kind="full"), ("bedroom", "hallA"): dict(kind="full", gaps=[(19.4, 21.6)]),
             ("bedroom", "hallB"): dict(kind="full"), ("hallB", "studio"): dict(kind="low"), ("hallA", "living"): dict(kind="open"),
             ("hallB", "living"): dict(kind="open")}
    g = floors(rooms) + build_walls(rooms, walls)
    g = g + place(M, "living", 0, 0) + place(M, "person", 0, 0) + place(M, "lab", 19, 0) + place(M, "studio", 0, 19) + place(M, "bedroom", 19, 19)
    g = g + runner(19.6, 17.0, 27.0, 18.1, "x") + running_wall_y(16.25, 19.6, 27.0) + treadmill_x(27.2, 16.55)
    g = g + runner(16.9, 19.6, 18.1, 30.5, "y") + fiddle(17.5, 31.0) + reading_nook(14.2, 22.5) + shrub(15.0, 30.6, .7)
    return g, rooms


def layout_B(state="wave"):
    """Garden court: a small sunken garden between lab and bedroom; living, lab and bedroom all open to it.
    Bedroom is mirrored so the bed and photo wall sit on the hall wall and the desk faces the garden glass."""
    M = modules(state)
    rooms = [dict(name="living", rect=(0, 0, 19, 19), floor=OAK), dict(name="lab", rect=(19, 0, 13, 16), floor=LABF),
             dict(name="garden", rect=(19, 16, 13, 5)), dict(name="bedroom", rect=(19, 21, 13, 13), floor=BEDF, wall=P["bwall"]),
             dict(name="hall", rect=(16, 19, 3, 15), floor=HALLF), dict(name="studio", rect=(0, 19, 16, 13), floor=OAK)]
    walls = {("lab", "living"): dict(kind="low", gaps=[(10.5, 14.5)]), ("studio", "living"): dict(kind="full", gaps=[(10.6, 13.4)]),
             ("garden", "lab"): dict(kind="glass", gaps=[(29.0, 31.0)]), ("garden", "living"): dict(kind="glass", gaps=[(16.4, 18.6)]),
             ("garden", "hall"): dict(kind="glass"), ("bedroom", "garden"): dict(kind="glass"),
             ("bedroom", "hall"): dict(kind="full", gaps=[(21.4, 23.6)]), ("hall", "studio"): dict(kind="low"), ("hall", "living"): dict(kind="open")}
    g = floors(rooms) + build_walls(rooms, walls)
    g = g + garden(19, 16, 13, 5, seed=4, tree_at=(26.5, 18.4, .9), pond=(22.6, 18.6, 1.1, .7), bench=(29.3, 18.9, "x"))
    g = g + stones([(20.0, 17.5), (21.0, 19.6), (24.2, 19.9), (28.0, 17.4), (30.0, 17.5)])
    g = g + place(M, "living", 0, 0) + place(M, "person", 0, 0) + place(M, "lab", 19, 0) + place(M, "studio", 0, 19)
    g = g + place(M, "bedroom", 19, 21, mirror=True, drop=("y0",))
    g = g + place(M, "treadmill", 0, 0)
    g = g + runner(16.9, 19.6, 18.1, 32.5, "y") + reading_nook(14.2, 22.5) + fiddle(17.5, 33.0)
    return g, rooms


def layout_C(state="wave"):
    """Entry courtyard: the front door moves to a small garden porch at the front corner;
    rooms wrap it in a U (studio left, living top-left, lab top-right, bedroom right)."""
    M = modules(state)
    rooms = [dict(name="living", rect=(0, 0, 19, 19), floor=OAK), dict(name="lab", rect=(19, 0, 13, 16), floor=LABF),
             dict(name="bedroom", rect=(32, 0, 13, 13), floor=BEDF, wall=P["bwall"]),
             dict(name="studio", rect=(0, 19, 16, 13), floor=OAK), dict(name="court", rect=(16, 16, 16, 16)),
             dict(name="hall", rect=(32, 13, 3, 6), floor=HALLF)]
    walls = {("lab", "living"): dict(kind="low", gaps=[(10.5, 14.5)]), ("studio", "living"): dict(kind="full", gaps=[(10.6, 13.4)]),
             ("bedroom", "lab"): dict(kind="full"), ("court", "lab"): dict(kind="glass", gaps=[(27, 29)]),
             ("court", "living"): dict(kind="glass", gaps=[(16.4, 18.6)]), ("court", "studio"): dict(kind="glass", gaps=[(22, 24)]),
             ("hall", "bedroom"): dict(kind="full", gaps=[(32.4, 34.6)]), ("hall", "lab"): dict(kind="low"), ("court", "hall"): dict(kind="glass")}
    g = floors(rooms) + build_walls(rooms, walls)
    g = g + garden(16, 16, 16, 16, seed=8, tree_at=(22.0, 22.5, 1.1), pond=(27.0, 21.0, 1.6, 1.0), bench=(18.0, 26.0, "y"))
    g = g + stones([(17.6, 17.5), (19.5, 19.0), (21.5, 20.0), (24.0, 19.0), (26.5, 18.0), (28.0, 17.3), (20.0, 23.5), (19.0, 25.5)])
    g = g + place(M, "living", 0, 0) + place(M, "person", 0, 0) + place(M, "lab", 19, 0) + place(M, "studio", 0, 19)
    g = g + place(M, "bedroom", 32, 0) + place(M, "treadmill", 0, 0)
    g = g + shrub(30.5, 30.5, .9) + shrub(17.2, 30.8, .7) + shrub(30.8, 24.0, .6)
    return g, rooms


def layout_V2(state="wave"):
    M = modules(state)
    rooms = [dict(name="studio", rect=(0, 0, 14, 9), floor=OAK), dict(name="living", rect=(0, 9, 18, 19), floor=OAK),
             dict(name="lab", rect=(18, 4, 13, 16), floor=LABF), dict(name="bedroom", rect=(18, 20, 13, 13), floor=BEDF, wall=P["bwall"])]
    walls = {("living", "studio"): dict(kind="low", gaps=[(5, 9)]), ("lab", "living"): dict(kind="low", gaps=[(12, 20)]),
             ("bedroom", "living"): dict(kind="full", gaps=[(20.9, 22.9)]), ("bedroom", "lab"): dict(kind="full")}
    g = floors(rooms) + build_walls(rooms, walls)
    g = g + place(M, "living", 0, 9) + place(M, "person", 0, 9) + place(M, "lab", 18, 4) + place(M, "studio", 0, 0) + place(M, "bedroom", 18, 20) + place(M, "treadmill", 0, 9)
    return g, rooms


LAYOUTS = {"v2": layout_V2, "A": layout_A, "B": layout_B, "C": layout_C}


def layout_D(state="wave"):
    """Stepped diamond: the side rooms slide toward the front, leaving a notch top-right and left.
    Taller silhouette (about 4:3), mirror-balanced across the diagonal, no corridors needed."""
    M = modules(state)
    rooms = [dict(name="living", rect=(0, 0, 19, 19), floor=OAK), dict(name="lab", rect=(19, 5, 13, 16), floor=LABF),
             dict(name="studio", rect=(5, 19, 14, 13), floor=OAK), dict(name="bedroom", rect=(19, 21, 13, 13), floor=BEDF, wall=P["bwall"])]
    walls = {("lab", "living"): dict(kind="low", gaps=[(13.0, 17.0)]), ("studio", "living"): dict(kind="full", gaps=[(15.6, 18.4)]),
             ("lab", "studio"): dict(kind="low"), ("bedroom", "lab"): dict(kind="full", gaps=[(19.4, 21.6)]), ("bedroom", "studio"): dict(kind="full")}
    g = floors(rooms) + build_walls(rooms, walls)
    g = g + place(M, "living", 0, 0) + place(M, "person", 0, 0) + place(M, "lab", 19, 5) + place(M, "studio", 5, 19) + place(M, "bedroom", 19, 21)
    g = g + place(M, "treadmill", 0, 0)
    return g, rooms


LAYOUTS["D"] = layout_D
