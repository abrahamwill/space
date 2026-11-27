"""The house v2: studio, main room (+ treadmill corner), lab, bedroom. Plan units; walls 4.2."""
import math
from engine import (Part, poly, box, hull, cham, cbox, cyl, disc, cone, rod, ico, qx, qy, cx_, cy_)
from character import character

H, HP, T = 4.2, 1.3, 0.5
P = dict(floor="#e2b07a", plank="#d39f69", lab="#d3cdc2", bfloor="#e6cfac", bplank="#d8bd96",
         wall="#ece3d4", bwall="#e6e3db", top="#fff4e6",
         wal="#9a5a30", walT="#ad6a3a", walD="#74401f", oli="#6e7a3c", oliT="#7f8c46",
         chr="#d6d6d2", red="#c8442b", cob="#2b4fa8", mus="#e0a72e", pink="#e9a3a0", char="#3a3a3c",
         leaf="#4f7a35", leaf2="#6f9a48", glass="#cfe2c0", glass2="#8fb06c", cream="#fbf3e6", creamS="#ece0cc",
         chkA="#6a655e", chkB="#8a847a", ink="#1b1a17", navy="#2f3d5c", white="#f3f1ec", cyan="#5fc3c4")

RIM = [(0, 0), (14, 0), (14, 9), (18, 9), (18, 4), (31, 4), (31, 33), (18, 33), (18, 28), (0, 28)]
CENTER = (15.5, 15.0, 1.4)

# exterior walls: (axis, const, a, b, interior normal sign, tag, colour)
EXT = [("y", 0, 0, 14, 1, "y0", P["wall"]), ("x", 14, 0, 9, -1, "x14", P["wall"]), ("y", 9, 14, 18, 1, "y9", P["wall"]),
       ("x", 18, 4, 9, 1, "x18l", P["wall"]), ("y", 4, 18, 31, 1, "y4", P["wall"]), ("x", 31, 4, 20, -1, "x31", P["wall"]),
       ("x", 31, 20, 33, -1, "x31b", P["bwall"]), ("y", 33, 18, 31, -1, "y33", P["bwall"]),
       ("x", 18, 28, 33, 1, "x18b", P["bwall"]), ("y", 28, 0, 18, -1, "y28", P["wall"]), ("x", 0, 0, 28, 1, "x0", P["wall"])]


def visible_tags(cam):
    keep = set()
    for ax, k, a, b, sg, tag, col in EXT:
        n = (sg, 0) if ax == "x" else (0, sg)
        if n[0] * cam.horiz[0] + n[1] * cam.horiz[1] > 0.05:
            keep.add(tag)
    return keep


class S:
    def __init__(s):
        s.parts = []   # (Part, tag)
        s.secs = []
        s.sec = "shell"

    def add(s, p, tag=None):
        s.parts.append((p, tag))
        s.secs.append(s.sec)

    def build(s, cam):
        keep = visible_tags(cam)
        out = Part()
        for p, tag in s.parts:
            if tag is None or tag in keep:
                out = out + p
        return out


def ext_wall(ax, k, a, b, sg, col):
    if ax == "x":
        x0 = k - T if sg > 0 else k
        return box(x0, a - T, 0, T, b - a + 2 * T, H, col, P["top"])
    y0 = k - T if sg > 0 else k
    return box(a - T, y0, 0, b - a + 2 * T, T, H, col, P["top"])


def full_wall(ax, k, a, b, gaps, colA, colB, lintel=3.15):
    """internal full-height wall centred on the line, two-tone (A = low side, B = high side)."""
    segs, cur = [], a
    for g0, g1 in gaps:
        segs.append((cur, g0)); cur = g1
    segs.append((cur, b))
    out = Part()
    def piece(s0, s1, z0, z1):
        if ax == "x":
            return box(k - T / 2, s0, z0, T / 2, s1 - s0, z1 - z0, colA, P["top"]) + box(k, s0, z0, T / 2, s1 - s0, z1 - z0, colB, P["top"])
        return box(s0, k - T / 2, z0, s1 - s0, T / 2, z1 - z0, colA, P["top"]) + box(s0, k, z0, s1 - s0, T / 2, z1 - z0, colB, P["top"])
    for s0, s1 in segs:
        if s1 > s0:
            out = out + piece(s0, s1, 0, H)
    for g0, g1 in gaps:
        out = out + piece(g0, g1, lintel, H)
    return out


def planks(x0, y0, x1, y1, col, alongx=False, step=1.1):
    out = Part()
    if not alongx:
        x = x0 + step
        while x < x1 - .05:
            out = out + poly([(x, y0, .004), (x + .05, y0, .004), (x + .05, y1, .004), (x, y1, .004)], col); x += step
    else:
        y = y0 + step
        while y < y1 - .05:
            out = out + poly([(x0, y, .004), (x1, y, .004), (x1, y + .05, .004), (x0, y + .05, .004)], col); y += step
    return out


def tube(x, y, z, w, d, h):
    return box(x, y, z, w, d, h, P["chr"])


def fiddle(cx, cy):
    g = cyl(cx, cy, 0, .55, .9, P["char"], n=8)
    g = g + box(cx - .06, cy - .06, .9, .12, .12, 2.6, P["walD"])
    for i, (dx, dy, dz, r) in enumerate([(.35, .1, 1.9, .5), (-.3, .25, 2.4, .55), (.25, -.3, 2.9, .5), (-.15, .1, 3.35, .48), (.2, .25, 3.7, .38)]):
        g = g + ico((cx + dx, cy + dy, dz), r, P["leaf"] if i % 2 else P["leaf2"], 0, seed=i + int(cx * 10), jit=.12)
    return g


def frame_y(Y, x0, x1, z0, z1, fcol, pcol, sgn=1, mat=.07):
    """picture frame on a wall plane y=Y (sgn: direction the face points)"""
    d = .06 * sgn
    f = box(x0, min(Y, Y + d), z0, x1 - x0, abs(d), z1 - z0, fcol)
    return f + qy(Y + d + .005 * sgn, x0 + mat, x1 - mat, z0 + mat, z1 - mat, pcol)


def frame_x(X, y0, y1, z0, z1, fcol, pcol, sgn=1, mat=.07):
    d = .06 * sgn
    f = box(min(X, X + d), y0, z0, abs(d), y1 - y0, z1 - z0, fcol)
    return f + qx(X + d + .005 * sgn, y0 + mat, y1 - mat, z0 + mat, z1 - mat, pcol)


def office_chair(cx, cy, yaw, frame="#2b2b2e", seat="#34343a"):
    g = Part()
    for k in range(5):
        a = math.radians(90 + k * 72)
        g = g + rod((0, 0, .2), (.72 * math.cos(a), .72 * math.sin(a), .14), .05, frame, 6)
        g = g + ico((.72 * math.cos(a), .72 * math.sin(a), .08), .08, "#1d1d1f", 0)
    g = g + cyl(0, 0, .15, .08, .9, "#9b9b96", n=8)
    g = g + cbox(0, 0, 1.12, .6, .58, .1, .06, seat)
    back = cbox(0, -.6, 1.95, .55, .09, .62, .1, seat) + box(-.06, -.62, 1.15, .12, .1, .5, frame)
    g = g + back.rot("x", 10, (0, -.55, 1.2))      # recline: the top of the backrest tips back (-y), away from the seat
    for sd in (-1, 1):
        g = g + box(sd * .58 - .04, -.2, 1.15, .08, .08, .45, frame) + box(sd * .58 - .07, -.35, 1.58, .14, .55, .06, frame)
    return g.rot("z", yaw).move(cx, cy, 0)


def build_scene(person="wave"):
    sc = S()
    A = sc.add
    sc.sec = 'shell'
    # ------------- floors
    A(poly([(0, 9, 0), (18, 9, 0), (18, 28, 0), (0, 28, 0)], P["floor"]) + planks(0, 9, 18, 28, P["plank"]))
    A(poly([(0, 0, 0), (14, 0, 0), (14, 9, 0), (0, 9, 0)], P["floor"]) + planks(0, 0, 14, 9, P["plank"]))
    A(poly([(18, 4, 0), (31, 4, 0), (31, 20, 0), (18, 20, 0)], P["lab"]))
    A(poly([(18, 20, 0), (31, 20, 0), (31, 33, 0), (18, 33, 0)], P["bfloor"]) + planks(18, 20, 31, 33, P["bplank"], alongx=True, step=.9))
    # ------------- walls
    for ax, k, a, b, sg, tag, col in EXT:
        A(ext_wall(ax, k, a, b, sg, col), tag)
    for a, b in [(0, 5), (9, 14)]:                               # studio / main partition
        A(box(a, 9 - T, 0, b - a, T, HP, P["wall"], P["top"]))
    A(box(18 - T, 9, 0, T, 3, HP, P["wall"], P["top"]))          # main / lab partition (doorway y12-20)
    A(full_wall("x", 18, 20 - T / 2, 28, [(20.9, 22.9)], P["wall"], P["bwall"]))   # main | bedroom, door from the living room
    A(full_wall("y", 20, 18, 31, [], P["wall"], P["bwall"]))                       # lab | bedroom

    sc.sec = 'studio'
    # ================= STUDIO =================
    A(qy(.02, .4, 9.6, 0, 4.2, P["wal"]), "y0")
    for zs in (2.3, 3.2):
        A(box(1.0, 0, zs, 7.6, .55, .12, P["cream"]), "y0")
    A(box(1.4, .05, 2.42, .5, .4, .55, P["oli"]) + cyl(3.1, .3, 2.42, .22, .5, P["cream"], n=10) + box(4.6, .05, 2.42, 1.2, .4, .3, P["red"])
      + box(6.6, .05, 3.32, .9, .4, .55, P["cob"]) + cyl(2.2, .3, 3.32, .25, .55, P["mus"], n=10), "y0")
    g = box(.5, .2, 0, 8.6, 1.4, 1.5, P["wal"], P["walT"])
    bx, k = .7, 0
    while bx < 8.8:
        g = g + qy(1.61, bx, bx + .3, .2, 1.25, [P["cream"], P["char"], P["red"], P["creamS"], P["cob"], P["mus"], P["oli"]][k % 7]); bx += .38; k += 1
    A(g)
    A(qx(.02, 2.4, 7.4, 1.5, 3.7, "#d9a066"), "x0")
    for (a, b, z0, c) in [(2.8, 4.0, 2.6, P["mus"]), (4.4, 5.6, 2.8, P["pink"]), (6.0, 7.1, 2.5, P["cream"]), (3.2, 4.5, 1.7, P["cream"]), (5.3, 6.6, 1.75, P["mus"])]:
        A(qx(.04, a, b, z0, z0 + .75, c), "x0")
    g = Part()
    for lx, ly in [(3.4, 3.5), (8.6, 3.5), (3.4, 5.8), (8.6, 5.8)]:
        g = g + tube(lx, ly, 0, .16, .16, 1.6)
    g = g + box(3.2, 3.3, 1.6, 5.9, 2.9, .22, P["wal"], P["walT"]) + box(3.6, 3.5, 1.82, 2.1, .55, 1.45, P["cream"])
    g = g + qy(4.06, 3.75, 5.55, 1.98, 3.12, "#2a2f3a", True) + qy(4.07, 3.95, 4.9, 2.6, 2.9, P["mus"], True)
    for i, c in enumerate([P["red"], P["cob"], P["mus"]]):
        g = g + box(5.9 + i * .3, 4.2 + i * .42, 1.82 + i * .12, 2.0, 1.35, .12, c)
    g = g + box(8.3, 3.6, 1.82, .14, .14, .7, P["chr"]) + ico((8.37, 3.67, 2.65), .42, "#6fa3d8", 1)
    g = g + tube(5.3, 6.8, 0, .14, 1.3, .14) + tube(5.3, 6.8, 0, .14, .14, 1.0) + tube(6.6, 6.8, 0, .14, 1.3, .14) + tube(6.6, 6.8, 0, .14, .14, 1.0)
    g = g + box(5.3, 6.8, 1.0, 1.44, 1.3, .14, "#d9b47a") + box(5.3, 7.95, 1.14, 1.44, .15, 1.1, "#d9b47a")
    A(g)

    sc.sec = 'living'
    # ================= MAIN ROOM =================
    g = poly([(5.25, 12.45, .012), (12.35, 12.45, .012), (12.35, 19.15, .012), (5.25, 19.15, .012)], P["chkA"])
    for i in range(4):
        for j in range(4):
            x0, y0 = 5.4 + i * 1.7, 12.6 + j * 1.6
            g = g + poly([(x0, y0, .02), (x0 + 1.7, y0, .02), (x0 + 1.7, y0 + 1.6, .02), (x0, y0 + 1.6, .02)], P["chkA"] if (i + j) % 2 == 0 else P["chkB"])
    A(g)
    A(qx(.02, 10.8, 16.6, 1.1, 3.95, P["char"]) + qx(.03, 11.0, 16.4, 1.25, 3.8, P["glass"], True) + qx(.035, 11.0, 16.4, 1.25, 2.3, P["glass2"], True)
      + cx_(.04, 12.0, 2.5, 1.0, P["leaf"], rz=.9, emis=True) + cx_(.04, 14.8, 2.7, 1.1, P["leaf"], rz=.85, emis=True)
      + qx(.05, 12.75, 12.85, 1.25, 3.8, P["char"]) + qx(.05, 14.55, 14.65, 1.25, 3.8, P["char"]), "x0")
    g = box(.2, 11.0, 0, 1.2, 5.4, 1.05, P["wal"], P["walT"])
    by, k = 11.2, 0
    while by < 16.2:
        g = g + qx(1.41, by, by + .28, .15, .9, [P["cream"], P["red"], P["char"], P["cob"], P["creamS"], P["mus"], P["oli"]][k % 7]); by += .36; k += 1
    A(g)
    A(qx(.02, 20.5, 22.0, 1.7, 3.6, P["walT"]) + qx(.03, 20.7, 21.8, 1.9, 3.4, P["cream"]) + cx_(.04, 21.25, 2.85, .4, P["red"]) + qx(.04, 20.9, 21.6, 2.0, 2.2, P["cob"])
      + qx(.02, 22.2, 23.4, 2.0, 3.4, P["walT"]) + qx(.03, 22.35, 23.25, 2.15, 3.25, P["mus"])
      + qx(.02, 23.8, 26.4, 0, 3.3, P["walD"]) + qx(.03, 24.1, 26.1, .25, 3.05, P["wal"]) + qx(.04, 25.7, 25.9, 1.5, 1.8, P["chr"]), "x0")
    A(qy(9.02, 14.0, 18.0, 0, 4.2, P["wal"]), "y9")
    g = Part()
    for zs in (1.9, 3.0):
        g = g + box(14.2, 9.0, zs, 3.6, .45, .1, P["walT"])
    for (x0, zs, c, dsc) in [(14.4, 2.0, P["red"], True), (15.6, 2.0, P["char"], True), (16.8, 2.0, P["mus"], False), (14.8, 3.1, P["cob"], True), (16.2, 3.1, P["pink"], False)]:
        g = g + qy(9.47, x0, x0 + .85, zs, zs + .85, c)
        if dsc:
            g = g + cy_(9.48, x0 + .42, zs + .42, .3, P["ink"], n=14)
    A(g, "y9")
    A(fiddle(1.0, 10.0))
    g = box(.2, 16.9, 0, 1.9, 4.6, 1.2, P["wal"], P["walT"]) + qx(2.11, 17.2, 19.0, .2, 1.0, P["walD"]) + qx(2.11, 19.3, 21.2, .2, 1.0, "#4a4440")
    g = g + box(.45, 17.3, 1.2, 1.5, 1.9, .25, P["char"]) + cyl(1.2, 18.2, 1.45, .6, .04, P["ink"], n=16) + cyl(1.2, 18.2, 1.49, .2, .01, P["red"], n=12)
    g = g + box(1.6, 18.9, 1.45, .14, .14, .5, P["chr"]) + cyl(1.1, 20.6, 1.2, .1, .5, P["red"], n=6) + ico((1.1, 20.6, 1.85), .38, P["red"], 1)
    A(g)
    A(cyl(8.8, 15.8, 0, .35, .9, P["char"], n=8) + cyl(8.8, 15.8, .9, 1.5, .2, P["wal"], P["walT"], n=8)
      + cyl(8.4, 15.5, 1.1, .22, .45, P["pink"], n=8) + box(8.9, 15.7, 1.1, .9, .7, .14, P["cob"]))
    g = box(11.8, 12.2, 0, 1.9, 6.6, .9, P["oli"], P["oliT"]) + box(12.9, 12.2, .9, .8, 6.6, .9, P["oli"], P["oliT"])
    g = g + box(11.8, 11.7, 0, 1.9, .55, 1.3, P["oli"], P["oliT"]) + box(11.8, 18.8, 0, 1.9, .55, 1.3, P["oli"], P["oliT"])
    g = g + box(11.95, 13.2, .9, .9, 1.6, .06, P["mus"]) + box(11.95, 13.75, .96, .9, .3, .02, P["cob"])
    A(g)
    A(cyl(5.0, 11.7, 0, .7, .08, P["chr"], n=8) + cyl(5.0, 11.7, .08, .1, .5, P["chr"], n=6)
      + box(4.2, 10.9, .58, 1.6, 1.6, .5, "#a3a36a") + box(4.2, 10.9, 1.08, .45, 1.6, .9, "#a3a36a"))
    A(tube(16.33, 10.33, 0, .14, .14, 2.9) + cyl(16.4, 10.4, 0, .45, .08, P["chr"], n=8) + ico((16.4, 10.4, 3.25), .5, P["cream"], 1, emis=True))
    A(tube(2.6, 22.6, 0, .14, .14, 3.3) + cyl(2.67, 22.67, 0, .6, .07, P["chr"], n=8) + tube(2.2, 22.62, 2.95, .95, .1, .1) + box(2.05, 22.85, 1.9, .75, .5, 1.05, P["red"]))
    A(poly([(6.0, 19.6, .03), (8.4, 19.6, .03), (8.4, 21.0, .03), (6.0, 21.0, .03)], P["red"]) + poly([(6.3, 19.85, .04), (8.1, 19.85, .04), (8.1, 20.75, .04), (6.3, 20.75, .04)], P["mus"]))

    sc.sec = 'treadmill'
    tmblock(A)
    sc.sec = 'lab'
    # ================= LAB =================
    A(cy_(4.02, 26.9, 2.75, 1.05, P["cob"], n=28) + qy(4.02, 21.2, 25.8, 1.7, 3.9, P["cream"])
      + qy(4.04, 21.6, 23.2, 3.25, 3.65, P["cob"]) + qy(4.04, 23.5, 25.4, 3.4, 3.6, P["red"]) + qy(4.04, 21.6, 23.8, 2.4, 2.6, P["ink"])
      + qy(4.04, 24.1, 24.8, 2.2, 3.0, P["mus"]) + qy(4.04, 25.0, 25.5, 2.2, 3.0, P["pink"]), "y4")
    g = Part()
    for lx, ly in [(21.2, 4.5), (25.8, 4.5), (21.2, 6.3), (25.8, 6.3)]:
        g = g + tube(lx, ly, 0, .16, .16, 1.6)
    g = g + box(21.0, 4.3, 1.6, 5.2, 2.3, .22, P["cream"])
    for i, c in enumerate([P["cob"], P["red"], P["mus"]]):
        g = g + box(21.6 + i * 1.35, 5.1, 1.82, .85, .22, 1.3, P["ink"]) + qy(5.33, 21.7 + i * 1.35, 22.35 + i * 1.35, 1.94, 3.0, c, True)
    A(g)
    A(box(18.3, 6.4, 0, 2.4, 2.4, 3.8, P["red"]) + qx(20.71, 6.65, 8.55, 2.2, 3.4, P["ink"]) + qx(20.72, 6.85, 8.35, 2.35, 3.25, "#86ad57", True)
      + box(20.7, 6.4, 1.6, .8, 2.4, .3, P["mus"]))
    A(tube(22.15, 9.75, 0, .14, .14, 1.5) + tube(23.3, 9.75, 0, .14, .14, 1.5) + tube(22.15, 10.9, 0, .14, .14, 1.5) + tube(23.3, 10.9, 0, .14, .14, 1.5)
      + box(22.0, 9.6, 1.5, 1.6, 1.6, .12, P["char"]) + cyl(22.8, 10.4, 1.62, .45, .8, P["cream"], n=10) + cyl(22.8, 10.4, 2.42, .45, .02, P["cob"], n=10) + cyl(22.8, 10.4, 2.44, .24, .02, "#b9d6f0", n=10, emis=True))
    g = cyl(24.4, 12.9, 0, 1.6, .3, P["mus"], n=12, ry=1.3) + cyl(24.4, 12.9, .3, 1.2, .05, "#f0c96a", n=12, ry=.95)
    g = g + ico((24.4, 12.9, 1.0), .78, P["cream"], 1, (1, 1, .95))
    g = g + box(23.9, 12.45, 1.5, .26, .26, .6, P["cream"]) + box(24.65, 12.1, 1.5, .26, .26, .6, P["cream"])
    g = g + ico((24.93, 13.2, 1.15), .08, P["ink"], 0) + ico((25.1, 12.95, 1.15), .08, P["ink"], 0)
    g = g + cyl(22.4, 13.8, 0, .42, .3, P["cob"], n=8)
    A(g)
    A(fiddle(25.6, 8.6))

    sc.sec = 'bedroom'
    bedroom(A)

    sc.sec = 'person'
    # ---- the character
    if person == "wave":
        A(character("wave", -45, (6.9, 20.0, .04)))
    elif person == "run":
        A(character("run", 0, (16.3, 24.35, .33)))
    elif person == "desk":
        A(character("sit", 90, (21.5, 26.0, 0)))
    return sc


def tmblock(A):
    # ---- NEW: treadmill corner (hidden from the front, seen when you rotate)
    tm = box(15.35, 22.8, 0, 1.9, 4.2, .32, "#3b3b3e", "#4a4a4e")
    tm = tm + poly([(15.55, 22.95, .33), (17.05, 22.95, .33), (17.05, 26.3, .33), (15.55, 26.3, .33)], "#1d1d1f")
    for X in (15.34, 17.26):
        tm = tm + qx(X, 23.1, 26.1, .12, .2, P["red"])
    tm = tm + box(15.35, 26.3, 0, 1.9, .7, .6, "#2e2e31", "#3b3b3e")
    for x0, x1 in ((15.5, 15.6), (17.1, 17.0)):
        tm = tm + rod((x0, 26.7, .55), (x1, 27.05, 2.5), .07, "#55555a")
        tm = tm + rod((x1, 26.95, 2.2), (x1, 25.3, 2.15), .05, "#9b9b96")
    con = box(15.55, 26.75, 2.42, 1.5, .5, .18, "#2b2b2e") + poly([(15.75, 26.85, 2.605), (17.05, 26.85, 2.605), (17.05, 27.15, 2.605), (15.75, 27.15, 2.605)], P["mus"], True)
    tm = tm + con.rot("x", 28, (16.3, 27.0, 2.5))
    A(tm.move(0, .6, 0))
    for k, (dx, c) in enumerate([(0, P["red"]), (.42, "#f3f1ec")]):    # running shoes by the wall
        A(hull(cham(14.35 + dx, 27.1, .12, .17, .4, .12, .06), c) + box(14.18 + dx, 26.72, 0, .34, .78, .05, "#f3f1ec"))
    # running photos on the front wall (y=28, faces into the room)
    for (x0, x1, z0, z1, fc, pc) in [(14.0, 15.3, 2.75, 3.75, P["ink"], "#8fb3c9"), (15.5, 16.4, 2.95, 3.95, "#f3f1ec", "#c9a27a"), (16.6, 17.6, 2.7, 3.55, P["ink"], "#9db07f"),
                                     (12.6, 13.7, 2.4, 3.3, P["walT"], "#d98b6a"), (12.9, 13.9, 3.45, 4.0, "#f3f1ec", "#6f8fb5"), (14.2, 15.1, 1.85, 2.55, "#f3f1ec", "#e0c48a")]:
        A(frame_y(28, x0, x1, z0, z1, fc, pc, sgn=-1), "y28")
    A(qy(27.95, 11.2, 12.2, 2.5, 3.3, "#fbfaf6") + qy(27.94, 11.35, 12.05, 2.95, 3.12, P["ink"]) + qy(27.94, 11.35, 12.05, 2.7, 2.78, P["red"]), "y28")   # race bib
    # medal hanger on the bedroom wall (main side)
    g = box(17.6, 24.0, 3.5, .14, 3.8, .14, "#1d1d1f") + box(17.62, 23.95, 3.42, .12, .1, .3, "#1d1d1f") + box(17.62, 27.75, 3.42, .12, .1, .3, "#1d1d1f")
    rib = [P["red"], P["cob"], P["mus"], "#f3f1ec", P["red"], P["cob"], P["mus"]]
    met = ["#d9a93a", "#c9c9c4", "#d9a93a", "#b0703c", "#d9a93a", "#c9c9c4", "#d9a93a"]
    for k in range(7):
        y = 24.35 + k * .5; zb = 2.75 - (.18 if k % 2 else 0)
        g = g + qx(17.72, y - .08, y + .08, zb + .18, 3.5, rib[k])
        g = g + cyl(0, 0, 0, .2, .06, met[k], n=12).rot("y", 90).move(17.62, y, zb)
    A(g)



def bedroom(A):
    """x18-31, y20-33. Back walls (seen from the front): y=20 (bed + photo wall) and x=18 (desk setup)."""
    g = poly([(20.8, 24.9, .012), (27.2, 24.9, .012), (27.2, 30.5, .012), (20.8, 30.5, .012)], "#2f4a7a")
    for i in range(10):
        for j in range(9):
            if (i + j) % 2 == 0:
                x0, y0 = 20.8 + i * .64, 24.9 + j * .622
                g = g + poly([(x0, y0, .02), (x0 + .64, y0, .02), (x0 + .64, y0 + .622, .02), (x0, y0 + .622, .02)], "#3e5f96")
    A(g)
    # bed, headboard on the lab wall
    g = box(22.6, 20.25, 0, 3.6, 4.45, .55, "#9a5d33", "#a8622f") + box(22.5, 20.25, 0, 3.8, .35, 2.05, "#8a5029", "#a8622f")
    g = g + box(22.7, 20.6, .55, 3.4, 3.95, .45, "#f2ece2")
    g = g + box(22.58, 21.75, 1.0, 3.64, 2.95, .22, "#66704f") + box(22.56, 21.6, 1.0, 3.68, .4, .32, "#7a8461")
    for y in (22.35, 23.35, 24.25):
        g = g + poly([(22.58, y, 1.223), (26.22, y, 1.223), (26.22, y + .26, 1.223), (22.58, y + .26, 1.223)], "#3a4560")
        g = g + poly([(22.58, y + .36, 1.225), (26.22, y + .36, 1.225), (26.22, y + .41, 1.225), (22.58, y + .41, 1.225)], "#d9cfb8")
    for x in (23.0, 24.2, 25.4):
        g = g + poly([(x, 21.75, 1.224), (x + .26, 21.75, 1.224), (x + .26, 24.7, 1.224), (x, 24.7, 1.224)], "#3a4560")
    g = g + cbox(23.55, 21.05, 1.2, .74, .34, .16, .08, "#ebe4d6") + cbox(25.25, 21.05, 1.2, .74, .34, .16, .08, "#ebe4d6")
    A(g)
    A(box(21.35, 20.35, 0, 1.0, 1.0, 1.1, P["wal"], P["walT"]) + qy(21.36, 21.5, 22.2, .65, .95, P["walD"])
      + cyl(21.85, 20.85, 1.1, .05, .45, "#e8e2d6", n=6) + ico((21.85, 20.85, 1.62), .3, "#ffe2a8", 1, (1, 1, .6), emis=True))
    # photo wall above the bed
    for (x0, x1, z0, z1, fc, pc) in [(21.2, 22.0, 2.45, 3.15, "#f3f1ec", "#86a8c4"), (22.5, 23.4, 2.3, 3.2, P["ink"], "#c4a17d"), (23.8, 24.9, 2.4, 3.3, "#f3f1ec", "#9db07f"),
                                     (25.3, 26.1, 2.3, 3.0, P["walT"], "#d98b6a"), (22.7, 23.5, 3.4, 4.0, "#f3f1ec", "#e0c48a"), (24.0, 25.1, 3.5, 4.0, P["ink"], "#7d93b8"),
                                     (25.5, 26.4, 3.25, 3.95, "#f3f1ec", "#b5869b"), (21.4, 22.1, 3.35, 3.9, P["ink"], "#a7b7a0"), (26.6, 27.3, 2.6, 3.3, "#f3f1ec", "#c9b08a")]:
        A(frame_y(20.25, x0, x1, z0, z1, fc, pc, sgn=1))
    # desk on the living-room wall: white top, navy drawers, black legs
    g = box(18.25, 23.3, 1.55, 2.2, 5.5, .12, "#f2efe8") + box(18.35, 23.4, 0, 1.95, 1.2, 1.55, "#2f3d5c")
    for z0 in (.15, .65, 1.1):
        g = g + qx(20.31, 23.5, 24.5, z0, z0 + .38, "#3b4b70")
    for lx, ly in [(18.35, 28.65), (20.3, 28.65)]:
        g = g + box(lx, ly, 0, .1, .1, 1.55, "#1d1d1f")
    A(g)
    # gaming PC: white case, black front, tinted glass side with soft cyan
    g = box(18.45, 23.5, 1.67, 1.15, .62, 1.2, P["white"])
    g = g + qx(19.61, 23.52, 24.1, 1.72, 2.82, "#18181a") + qx(19.62, 23.58, 23.61, 1.78, 2.76, P["cyan"], True)
    g = g + qy(24.13, 18.55, 19.5, 1.75, 2.78, "#1c272b")
    for cz in (2.0, 2.47):
        g = g + cy_(24.14, 19.25, cz, .2, P["cyan"], 14, emis=True) + cy_(24.15, 19.25, cz, .14, "#22343a", 14, emis=True)
    g = g + qy(24.145, 18.6, 19.45, 2.66, 2.7, P["cyan"], True)
    A(g)
    # pixar-style desk lamp at the front corner, leaning over the keyboard
    g = cyl(20.05, 24.45, 1.67, .2, .06, "#e9e5dc", n=10)
    g = g + rod((20.05, 24.45, 1.73), (19.55, 24.2, 2.75), .045, "#e9e5dc", 6) + ico((19.55, 24.2, 2.75), .07, "#55555a", 0)
    g = g + rod((19.55, 24.2, 2.75), (19.95, 24.85, 3.1), .045, "#e9e5dc", 6) + ico((19.95, 24.85, 3.1), .08, "#55555a", 0)
    g = g + cone((19.97, 24.9, 3.1), (19.85, 25.25, 2.78), .08, .24, "#ece8df", 10) + disc(0, 0, 0, .2, "#ffe7b0", 12, emis=True).rot("x", 40).move(19.84, 25.27, 2.76)
    A(g)
    # main monitor, square in front of the chair
    g = box(18.45, 25.65, 1.67, .5, .7, .05, "#1a1a1c") + box(18.55, 25.92, 1.72, .12, .16, .5, "#1a1a1c")
    g = g + box(18.67, 24.65, 2.05, .12, 2.7, 1.52, "#151517")
    g = g + qx(18.80, 24.75, 27.25, 2.13, 3.49, "#2a3a64", True) + qx(18.805, 24.75, 27.25, 2.13, 2.6, "#3f6b4a", True)
    g = g + cx_(18.81, 25.5, 3.1, .18, P["mus"], 14, emis=True) + qx(18.81, 26.3, 26.55, 2.6, 2.9, P["red"], True)
    g = g + box(19.45, 25.25, 1.67, .45, 1.5, .06, "#2a2a2c") + poly([(19.4, 26.95, 1.675), (20.1, 26.95, 1.675), (20.1, 27.75, 1.675), (19.4, 27.75, 1.675)], "#3a3a3e")
    g = g + ico((19.75, 27.3, 1.72), .1, "#1d1d1f", 0, (1.3, 1, .5))
    A(g)
    # second monitor, portrait, on a clamp arm, angled to the chair
    g = box(18.32, 28.0, 1.67, .12, .12, 1.8, "#1a1a1c")
    g = g + rod((18.38, 28.06, 3.0), (18.7, 27.85, 3.0), .04, "#1a1a1c", 6) + rod((18.7, 27.85, 3.0), (18.85, 27.75, 2.85), .04, "#1a1a1c", 6)
    mon = box(-.45, -.05, -.82, .9, .1, 1.64, "#151517") + qy(.055, -.39, .39, -.75, .75, "#1f2b35", True)
    for k in range(6):
        mon = mon + qy(.06, -.3, .3 - (k % 3) * .12, .55 - k * .22, .6 - k * .22, "#8fa3b5" if k % 2 else P["cyan"], True)
    g = g + mon.rot("z", -125).move(19.0, 27.85, 2.75)
    A(g)
    A(office_chair(21.5, 26.0, 90))
    # pegboard + little figures above the PC
    A(qx(18.27, 23.3, 24.9, 2.5, 3.6, "#ebe6dc") + box(18.25, 23.4, 2.85, .3, 1.4, .06, "#d6d0c4"))
    for k, c in enumerate([P["red"], P["mus"], P["cob"]]):
        A(box(18.32, 23.55 + k * .45, 2.91, .18, .22, .3, c) + ico((18.41, 23.66 + k * .45, 3.3), .12, "#e9c9a5", 0))
    # simple wardrobe at the end of the lab wall
    g = box(27.4, 20.25, 0, 2.2, 1.45, 3.9, "#efe7d8", "#f6f0e6") + box(27.45, 20.3, 0, 2.1, 1.42, .18, P["walD"])
    g = g + qy(21.71, 28.48, 28.52, .25, 3.85, "#cbbfa9") + box(28.35, 21.7, 1.6, .06, .06, .7, P["wal"]) + box(28.62, 21.7, 1.6, .06, .06, .7, P["wal"])
    A(g)
    # window with blinds on the far wall (seen when rotated)
    g = qx(30.98, 24.0, 29.0, 1.2, 3.9, "#d9d3c6") + qx(30.97, 24.15, 28.85, 1.35, 3.75, "#f7f3ea", True)
    for k in range(11):
        z = 1.5 + k * .22
        g = g + qx(30.965, 24.15, 28.85, z, z + .03, "#e2dccf", True)
    A(g, "x31b")
    A(fiddle(30.0, 32.0))
