"""Sunken cutaway house: the page is the ground, rooms are a pit cut into it.
Everything is clipped to the RIM = the floor plan outline at wall-top height.
usage: python3 house3.py OUTDIR -> PNGs + anchors.json"""
import json, math, os, sys
from PIL import Image, ImageDraw

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
R = 15.0
H = 4.2; HP = 1.3; T = 0.5
ZF = 2.2; K = 6; SS = 2
INK = "#1a1a1a"; NIGHT = (31, 36, 51)

def hx(c): c = c.lstrip("#"); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
def mix(c, t, f): a = hx(c); return "#%02x%02x%02x" % tuple(int(a[i] * (1 - f) + t[i] * f) for i in range(3))
def sh(c, f): a = hx(c); return "#%02x%02x%02x" % tuple(max(0, min(255, int(v * f))) for v in a)

P = dict(floor="#773d26", hall="#9a5a35", lab="#5d6247", wallX="#2f4625", wallY="#817b43", top="#fff2e3",
         wood="#e08e45", woodT="#f6b26b", woodD="#b86a2c", dark="#b8653f", darkT="#d48b5e", darkD="#8f4a2b",
         cream="#fff2e3", creamS="#efdcc4", creamD="#d6bf9f", teal="#2a9d8f", tealL="#bfe8e2", yel="#f2c14e", org="#f08a4b",
         red="#e05d44", sky="#79c2c2", leaf="#5c8a3a", leaf2="#a3c45a", sofa="#7da23e", sofaT="#a3c45a", sofaD="#5f7f2c",
         rug="#f39a72", rug2="#f7b597", navy="#2f3d5c", glow="#f6c86a")

def proj(x, y, z): return ((x - y) * 2 * K, (x + y) * K - z * K * ZF)

class Scene:
    def __init__(s): s.floor, s.back, s.groups, s.anchors = [], [], [], {}
    @staticmethod
    def box(x, y, z, w, d, h, t, l, r, ol=True):
        top = [(x, y, z + h), (x + w, y, z + h), (x + w, y + d, z + h), (x, y + d, z + h)]
        lf = [(x, y + d, z), (x + w, y + d, z), (x + w, y + d, z + h), (x, y + d, z + h)]
        rt = [(x + w, y, z), (x + w, y + d, z), (x + w, y + d, z + h), (x + w, y, z + h)]
        return [("p", lf, l, ol), ("p", rt, r, ol), ("p", top, t, ol)]
    @staticmethod
    def q(pts, fill, ol=True): return [("p", pts, fill, ol)]
    @staticmethod
    def ell(cx, cy, z, rx, ry, fill, ol=True, n=32):
        return [("p", [(cx + rx * math.cos(a), cy + ry * math.sin(a), z) for a in [i * 2 * math.pi / n for i in range(n)]], fill, ol)]
    @staticmethod
    def cyl(cx, cy, z, r, h, top, side, ol=True, n=24):
        pts = lambda zz: [(cx + r * math.cos(a), cy + r * math.sin(a), zz) for a in [i * 2 * math.pi / n for i in range(n)]]
        b, t = pts(z), pts(z + h)
        front = [i for i in range(n) if math.sin(i * 2 * math.pi / n + math.pi / 4) > -0.05]
        return [("p", [b[i] for i in front] + [t[i] for i in reversed(front)], side, ol), ("p", t, top, ol)]
    @staticmethod
    def blob(cx, cy, z, r, fill, hi): return [("c", (cx, cy, z), r, fill, True), ("c", (cx - r * .25, cy - r * .25, z + r * .4), r * .42, hi, False)]
    def add(s, room, key, items): s.groups.append((key, room, items))
    def addback(s, room, items): s.back.append((room, items))
    def addfloor(s, room, key, items): s.floor.append((key, room, items))
    def anchor(s, name, x, y, z): s.anchors[name] = (x, y, z)

def floor_room(S, room, ox, oy, color):
    S.addfloor(room, ox + oy, S.q([(ox, oy, 0), (ox + R, oy, 0), (ox + R, oy + R, 0), (ox, oy + R, 0)], color, True))
def wall_x(S, room, X, y0, y1):
    S.addback(room, S.box(X - T, y0, 0, T, y1 - y0, H, P["top"], P["wallX"], P["wallX"]))
def wall_y(S, room, Y, x0, x1):
    S.addback(room, S.box(x0, Y - T, 0, x1 - x0, T, H, P["top"], P["wallY"], P["wallY"]))
def part_x(S, room, X, y0, y1, gap):
    for a, b in [(y0, gap[0]), (gap[1], y1)]:
        S.add(room, X + (a + b) / 2 - 0.3, S.box(X - T, a, 0, T, b - a, HP, P["top"], P["wallX"], P["wallX"]))
def part_y(S, room, Y, x0, x1, gap):
    for a, b in [(x0, gap[0]), (gap[1], x1)]:
        S.add(room, (a + b) / 2 + Y - 0.3, S.box(a, Y - T, 0, b - a, T, HP, P["top"], P["wallY"], P["wallY"]))
def deco_x(S, room, X, y0, y1, z0, z1, fill, ol=True):
    S.addback(room, S.q([(X + .01, y0, z0), (X + .01, y1, z0), (X + .01, y1, z1), (X + .01, y0, z1)], fill, ol))
def deco_y(S, room, Y, x0, x1, z0, z1, fill, ol=True):
    S.addback(room, S.q([(x0, Y + .01, z0), (x1, Y + .01, z0), (x1, Y + .01, z1), (x0, Y + .01, z1)], fill, ol))

def plant(S, room, cx, cy, big=1.0):
    g = S.box(cx - .65 * big, cy - .65 * big, 0, 1.3 * big, 1.3 * big, 1.0 * big, P["org"], "#d96f30", P["darkD"])
    for dx, dy, dz, r in [(0, 0, 1.8, .9), (-.3, .2, 2.6, .7), (.25, -.2, 3.2, .55)]:
        g += S.blob(cx + dx, cy + dy, dz * big, r * big, P["leaf"], P["leaf2"])
    S.add(room, cx + cy, g)

def person(S, room, x, y):
    g = S.box(x, y, 0, .8, .8, 1.6, P["navy"], P["navy"], "#1f2a40")
    g += S.box(x - .18, y - .18, 1.6, 1.16, 1.16, 1.3, P["yel"], P["yel"], "#d9a830")
    g += S.box(x - .04, y - .04, 2.9, .88, .88, .8, "#f1b98f", "#f1b98f", "#d99a6e")
    g += S.box(x - .1, y - .1, 3.55, 1.08, 1.08, .32, INK, INK, INK)
    S.add(room, x + y + .8, g)


# ================= Bauhaus x mid-century restyle (same plan + anchors as v4) =================
P.update(dict(
    floor="#cf9c64", plank="#b98652", lab="#bdb6a8", wallX="#dccbb0", wallY="#ece0ca", top="#fff4e6",
    wal="#8f4f26", walT="#a8622f", walD="#6f3a1a",
    oli="#5a6330", oliT="#717c3d", oliD="#434a22",
    chr="#cfcfca", chrD="#9b9b96", red="#c8442b", cob="#2b4fa8", mus="#e0a72e", pink="#e9a3a0", char="#3a3a3c",
    leaf="#4f7a35", leaf2="#86ad57", glass="#cfe2c0", glass2="#7fa35e", cream="#fbf3e6", creamS="#ece0cc", creamD="#d4c4aa",
    chkA="#5e5a54", chkB="#807a70", glow="#f6c86a"))
RIM = [(0, 0), (14, 0), (14, 9), (18, 9), (18, 4), (31, 4), (31, 20), (18, 20), (18, 28), (0, 28)]
SPILL = {"studio": [(5, 9, 0), (9, 9, 0), (10.2, 5.4, 0), (3.8, 5.4, 0)],
         "lab": [(18, 12, 0), (18, 16, 0), (21.8, 17.2, 0), (21.8, 10.8, 0)]}

def oak_floor(S, room, x0, y0, x1, y1, color):
    S.addfloor(room, 0, S.q([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], color, True))
    x = x0 + 1.1
    while x < x1:   # planks run along y
        S.addfloor(room, 1, S.q([(x, y0, .005), (x + .06, y0, .005), (x + .06, y1, .005), (x, y1, .005)], P["plank"], False)); x += 1.1

def tube(S, x, y, z, w, d, h):  # chrome tube segment
    return S.box(x, y, z, w, d, h, P["chr"], P["chr"], P["chrD"])

def ring_y(S, room, Y, cx, cz, r, fill, n=28):  # circle decal on plane y=Y
    S.addback(room, S.q([(cx + r * math.cos(a), Y + .02, cz + r * math.sin(a)) for a in [i * 2 * math.pi / n for i in range(n)]], fill, False))

def fiddle(S, room, cx, cy):
    g = S.cyl(cx, cy, 0, .55, .9, P["char"], "#2a2a2c")
    g += S.box(cx - .06, cy - .06, .9, .12, .12, 2.6, P["walD"], P["walD"], P["walD"])
    for dx, dy, dz, r in [(.35, .1, 1.9, .5), (-.3, .25, 2.4, .55), (.25, -.3, 2.9, .5), (-.15, .1, 3.35, .48), (.2, .25, 3.7, .38)]:
        g += S.blob(cx + dx, cy + dy, dz, r, P["leaf"], P["leaf2"])
    S.add(room, cx + cy, g)

def person(S, room, x, y):
    g = S.box(x, y, 0, .8, .8, 1.6, P["char"], P["char"], "#262628")
    g += S.box(x - .18, y - .18, 1.6, 1.16, 1.16, 1.3, P["mus"], P["mus"], "#b8861f")
    g += S.box(x - .04, y - .04, 2.9, .88, .88, .8, "#e9b48a", "#e9b48a", "#cf9670")
    g += S.box(x - .1, y - .1, 3.55, 1.08, 1.08, .32, INK, INK, INK)
    S.add(room, x + y + .8, g)

def build():
    S = Scene()
    oak_floor(S, "main", 0, 9, 18, 28, P["floor"])
    oak_floor(S, "studio", 0, 0, 14, 9, P["floor"])
    S.addfloor("lab", 0, S.q([(18, 4, 0), (31, 4, 0), (31, 20, 0), (18, 20, 0)], P["lab"], True))

    # ================= STUDIO =================
    wall_y(S, "studio", 0, 0, 14); wall_x(S, "studio", 0, 0 - T, 9)
    # walnut panel behind the credenza, white floating shelves above it
    deco_y(S, "studio", 0, 0.4, 9.6, 0, 4.2, P["wal"], False)
    for zs in (2.3, 3.2):
        S.addback("studio", S.box(1.0, 0, zs, 7.6, .55, .12, P["cream"], P["creamS"], P["creamD"]))
    S.addback("studio", S.box(1.4, .05, 2.42, .5, .4, .55, P["oliT"], P["oli"], P["oliD"]) + S.cyl(3.1, .3, 2.42, .22, .5, P["cream"], P["creamS"])
              + S.box(4.6, .05, 2.42, 1.2, .4, .3, P["red"], P["red"], "#a3361f") + S.box(6.6, .05, 3.32, .9, .4, .55, P["cob"], P["cob"], "#1f3b80")
              + S.cyl(2.2, .3, 3.32, .25, .55, P["mus"], "#b8861f"))
    g = S.box(0.5, .2, 0, 8.6, 1.4, 1.5, P["walT"], P["wal"], P["walD"])
    bx = .7; k = 0
    while bx < 8.8:
        c = [P["cream"], P["char"], P["red"], P["creamS"], P["cob"], P["mus"], P["oliT"]][k % 7]
        g += S.q([(bx, 1.61, .2), (bx + .3, 1.61, .2), (bx + .3, 1.61, 1.25), (bx, 1.61, 1.25)], c); bx += .38; k += 1
    S.add("studio", 4.8 + .9, g); S.anchor("archive", 4.7, 1.0, 3.4)
    deco_x(S, "studio", 0, 2.4, 7.4, 1.5, 3.7, "#d9a066")
    for (a, b, z0, c) in [(2.8, 4.0, 2.6, P["mus"]), (4.4, 5.6, 2.8, P["pink"]), (6.0, 7.1, 2.5, P["cream"]), (3.2, 4.5, 1.7, P["cream"]), (5.3, 6.6, 1.75, P["mus"])]:
        deco_x(S, "studio", 0.02, a, b, z0, z0 + .75, c)
    S.anchor("pinboard", 0, 4.9, 3.3)
    # walnut desk on chrome legs, cream monitor, folders, blue mushroom lamp
    g = []
    for lx, ly in [(3.4, 3.5), (8.6, 3.5), (3.4, 5.8), (8.6, 5.8)]: g += tube(S, lx, ly, 0, .16, .16, 1.6)
    g += S.box(3.2, 3.3, 1.6, 5.9, 2.9, .22, P["walT"], P["wal"], P["walD"])
    g += S.box(3.6, 3.5, 1.82, 2.1, .55, 1.45, P["cream"], P["creamS"], P["creamD"])
    g += S.q([(3.75, 4.06, 1.98), (5.55, 4.06, 1.98), (5.55, 4.06, 3.12), (3.75, 4.06, 3.12)], P["char"])
    g += S.q([(3.95, 4.07, 2.6), (4.9, 4.07, 2.6), (4.9, 4.07, 2.9), (3.95, 4.07, 2.9)], P["mus"], False)
    for i, c in enumerate([P["red"], P["cob"], P["mus"]]):
        g += S.box(5.9 + i * .3, 4.2 + i * .42, 1.82 + i * .12, 2.0, 1.35, .12, c, c, sh(c, .8))
    g += S.box(8.3, 3.6, 1.82, .14, .14, .7, P["chr"], P["chr"], P["chrD"]) + S.blob(8.37, 3.67, 2.65, .42, "#6fa3d8", "#b9d6f0")
    S.add("studio", 6.2 + 4.8, g); S.anchor("folders", 7.0, 5.0, 2.3)
    # cantilever tube chair with cane seat
    g = tube(S, 5.3, 6.8, 0, .14, 1.3, .14) + tube(S, 5.3, 6.8, 0, .14, .14, 1.0) + tube(S, 6.6, 6.8, 0, .14, 1.3, .14) + tube(S, 6.6, 6.8, 0, .14, .14, 1.0)
    g += S.box(5.3, 6.8, 1.0, 1.44, 1.3, .14, "#d9b47a", "#c49c60", "#a8844c") + S.box(5.3, 7.95, 1.14, 1.44, .15, 1.1, "#d9b47a", "#c49c60", "#a8844c")
    S.add("studio", 6.0 + 7.4, g)
    S.anchor("lbl_studio", 2.6, 7.9, 0); S.anchor("c_studio", 5.0, 4.4, 1.0)

    # ================= MAIN ROOM =================
    # checkered rug
    S.addfloor("main", 98, S.q([(5.25, 12.45, .015), (12.35, 12.45, .015), (12.35, 19.15, .015), (5.25, 19.15, .015)], P["chkA"], True))
    for i in range(4):
        for j in range(4):
            c = P["chkA"] if (i + j) % 2 == 0 else P["chkB"]
            x0, y0 = 5.4 + i * 1.7, 12.6 + j * 1.6
            S.addfloor("main", 99, S.q([(x0, y0, .02), (x0 + 1.7, y0, .02), (x0 + 1.7, y0 + 1.6, .02), (x0, y0 + 1.6, .02)], c, False))
    S.addfloor("main", 99, S.q([(6.0, 19.6, .03), (8.4, 19.6, .03), (8.4, 21.0, .03), (6.0, 21.0, .03)], P["red"]))
    S.addfloor("main", 99, S.q([(6.3, 19.85, .04), (8.1, 19.85, .04), (8.1, 20.75, .04), (6.3, 20.75, .04)], P["mus"], False))
    wall_x(S, "main", 0, 9, 28); wall_y(S, "main", 9, 14, 18)
    part_y(S, "main", 9, 0, 14, (5, 9))
    # big black-framed window onto a garden, low walnut bookshelf beneath it
    deco_x(S, "main", 0, 10.8, 16.6, 1.1, 3.95, P["char"]); deco_x(S, "main", 0.01, 11.0, 16.4, 1.25, 3.8, P["glass"])
    deco_x(S, "main", 0.015, 11.0, 16.4, 1.25, 2.3, P["glass2"], False)
    S.addback("main", S.q([(0.02, 12.0 + 1.0 * math.cos(a), 2.5 + .9 * math.sin(a)) for a in [i * 2 * math.pi / 20 for i in range(20)]], P["leaf"], False))
    S.addback("main", S.q([(0.02, 14.8 + 1.1 * math.cos(a), 2.7 + .85 * math.sin(a)) for a in [i * 2 * math.pi / 20 for i in range(20)]], P["leaf"], False))
    deco_x(S, "main", 0.03, 12.75, 12.85, 1.25, 3.8, P["char"], False); deco_x(S, "main", 0.03, 14.55, 14.65, 1.25, 3.8, P["char"], False)
    S.anchor("window", 0, 13.8, 3.4)
    g = S.box(0.2, 11.0, 0, 1.2, 5.4, 1.05, P["walT"], P["wal"], P["walD"])
    by = 11.2; k = 0
    while by < 16.2:
        c = [P["cream"], P["red"], P["char"], P["cob"], P["creamS"], P["mus"], P["oliT"]][k % 7]
        g += S.q([(1.41, by, .15), (1.41, by + .28, .15), (1.41, by + .28, .9), (1.41, by, .9)], c); by += .36; k += 1
    S.add("main", .8 + 13.7, g)
    # framed Bauhaus prints (talks & workshops) + walnut front door
    deco_x(S, "main", 0, 20.5, 22.0, 1.7, 3.6, P["walT"]); deco_x(S, "main", 0.01, 20.7, 21.8, 1.9, 3.4, P["cream"])
    S.addback("main", S.q([(0.02, 21.25 + .4 * math.cos(a), 2.85 + .4 * math.sin(a)) for a in [i * 2 * math.pi / 20 for i in range(20)]], P["red"], False))
    deco_x(S, "main", 0.02, 20.9, 21.6, 2.0, 2.2, P["cob"], False)
    deco_x(S, "main", 0, 22.2, 23.4, 2.0, 3.4, P["walT"]); deco_x(S, "main", 0.01, 22.35, 23.25, 2.15, 3.25, P["mus"])
    S.anchor("notice", 0, 21.9, 3.5)
    deco_x(S, "main", 0, 23.8, 26.4, 0, 3.3, P["walD"]); deco_x(S, "main", 0.02, 24.1, 26.1, 0.25, 3.05, P["wal"])
    deco_x(S, "main", 0.03, 25.7, 25.9, 1.5, 1.8, P["chr"], False)
    S.anchor("door", 0, 25.1, 3.3)
    # walnut panel + floating record shelves on the short back wall
    deco_y(S, "main", 9, 14.0, 18.0, 0, 4.2, P["wal"], False)
    for zs in (1.9, 3.0):
        S.addback("main", S.box(14.2, 9.0, zs, 3.6, .45, .1, P["walT"], P["walT"], P["walD"]))
    for (x0, zs, c, disc) in [(14.4, 2.0, P["red"], True), (15.6, 2.0, P["char"], True), (16.8, 2.0, P["mus"], False), (14.8, 3.1, P["cob"], True), (16.2, 3.1, P["pink"], False)]:
        S.addback("main", S.q([(x0, 9.42, zs), (x0 + .85, 9.42, zs), (x0 + .85, 9.42, zs + .85), (x0, 9.42, zs + .85)], c))
        if disc: S.addback("main", S.q([(x0 + .42 + .3 * math.cos(a), 9.43, zs + .42 + .3 * math.sin(a)) for a in [i * 2 * math.pi / 16 for i in range(16)]], INK, False))
    S.anchor("photos", 16.0, 9, 3.8)
    fiddle(S, "main", 1.0, 10.0)
    # long low walnut media console with the turntable, red mushroom lamp
    g = S.box(0.2, 16.9, 0, 1.9, 4.6, 1.2, P["walT"], P["wal"], P["walD"])
    g += S.q([(2.11, 17.2, .2), (2.11, 19.0, .2), (2.11, 19.0, 1.0), (2.11, 17.2, 1.0)], P["walD"])
    g += S.q([(2.11, 19.3, .2), (2.11, 21.2, .2), (2.11, 21.2, 1.0), (2.11, 19.3, 1.0)], "#4a4440")
    g += S.box(0.45, 17.3, 1.2, 1.5, 1.9, .25, P["char"], "#2a2a2c", "#1e1e20")
    g += S.ell(1.2, 18.2, 1.46, .6, .6, INK) + S.ell(1.2, 18.2, 1.47, .2, .2, P["red"], False)
    g += S.box(1.6, 18.9, 1.45, .14, .14, .5, P["chr"], P["chr"], P["chrD"])
    g += S.cyl(1.1, 20.6, 1.2, .1, .5, P["red"], P["red"]) + S.blob(1.1, 20.6, 1.85, .38, P["red"], "#e57a5e")
    S.add("main", 1.1 + 19.2, g); S.anchor("turntable", 1.5, 18.2, 2.6)
    # round walnut coffee table, pink vase, book
    g = S.cyl(8.8, 15.8, 0, .35, .9, P["char"], "#2a2a2c") + S.cyl(8.8, 15.8, .9, 1.5, .2, P["walT"], P["wal"])
    g += S.cyl(8.4, 15.5, 1.1, .22, .45, P["pink"], "#cf8784") + S.box(8.9, 15.7, 1.1, .9, .7, .14, P["cob"], P["cob"], "#1f3b80")
    S.add("main", 8.8 + 15.8, g)
    # low olive lounge sofa with a knot pillow and a throw
    g = S.box(11.8, 12.2, 0, 1.9, 6.6, .9, P["oliT"], P["oli"], P["oliD"])
    g += S.box(12.9, 12.2, .9, .8, 6.6, .9, P["oliT"], P["oli"], P["oliD"])
    g += S.box(11.8, 11.7, 0, 1.9, .55, 1.3, P["oliT"], P["oli"], P["oliD"]) + S.box(11.8, 18.8, 0, 1.9, .55, 1.3, P["oliT"], P["oli"], P["oliD"])
    g += S.box(11.95, 13.2, .9, .9, 1.6, .06, P["mus"], P["mus"], "#b8861f") + S.box(11.95, 13.75, .96, .9, .3, .02, P["cob"], P["cob"], P["cob"])
    S.add("main", 12.6 + 15.4, g)
    # swivel lounge chair on a chrome star base
    g = S.cyl(5.0, 11.7, 0, .7, .08, P["chr"], P["chrD"]) + S.cyl(5.0, 11.7, .08, .1, .5, P["chr"], P["chrD"])
    g += S.box(4.2, 10.9, .58, 1.6, 1.6, .5, "#a3a36a", "#8f8f58", "#767646") + S.box(4.2, 10.9, 1.08, .45, 1.6, .9, "#a3a36a", "#8f8f58", "#767646")
    S.add("main", 5.0 + 11.7, g)
    # chrome globe floor lamp by the record wall
    S.add("main", 16.4 + 10.4, tube(S, 16.33, 10.33, 0, .14, .14, 2.9) + S.cyl(16.4, 10.4, 0, .45, .08, P["chr"], P["chrD"]) + S.blob(16.4, 10.4, 3.25, .5, P["cream"], "#ffffff"))
    # chrome coat rack by the door
    g = tube(S, 2.6, 22.6, 0, .14, .14, 3.3) + S.cyl(2.67, 22.67, 0, .6, .07, P["chr"], P["chrD"])
    g += tube(S, 2.2, 22.62, 2.95, .95, .1, .1) + S.box(2.05, 22.85, 1.9, .75, .5, 1.05, P["red"], P["red"], "#a3361f")
    S.add("main", 2.7 + 22.7, g); S.anchor("coatrack", 2.7, 22.8, 3.4)
    person(S, "main", 6.0, 19.4); S.anchor("me", 6.4, 19.8, 3.9)
    S.anchor("lbl_main", 9.6, 22.4, 0); S.anchor("c_main", 8.0, 16.5, 1.0)

    # ================= LAB =================
    wall_y(S, "lab", 4, 18, 31); wall_x(S, "lab", 18, 4 - T, 9)
    part_x(S, "lab", 18, 9, 20, (12, 20))
    ring_y(S, "lab", 4, 26.9, 2.75, 1.05, P["cob"])
    deco_y(S, "lab", 4, 21.2, 25.8, 1.7, 3.9, P["cream"])
    for (a, b, z0, z1, c) in [(21.6, 23.2, 3.25, 3.65, P["cob"]), (23.5, 25.4, 3.4, 3.6, P["red"]), (21.6, 23.8, 2.4, 2.6, INK), (24.1, 24.8, 2.2, 3.0, P["mus"]), (25.0, 25.5, 2.2, 3.0, P["pink"])]:
        deco_y(S, "lab", 4.02, a, b, z0, z1, c, False)
    S.anchor("whiteboard", 23.5, 4, 3.6)
    g = []
    for lx, ly in [(21.2, 4.5), (25.8, 4.5), (21.2, 6.3), (25.8, 6.3)]: g += tube(S, lx, ly, 0, .16, .16, 1.6)
    g += S.box(21.0, 4.3, 1.6, 5.2, 2.3, .22, P["cream"], P["creamS"], P["creamD"])
    for i, c in enumerate([P["cob"], P["red"], P["mus"]]):
        g += S.box(21.6 + i * 1.35, 5.1, 1.82, .85, .22, 1.3, INK, INK, INK)
        g += S.q([(21.7 + i * 1.35, 5.33, 1.94), (22.35 + i * 1.35, 5.33, 1.94), (22.35 + i * 1.35, 5.33, 3.0), (21.7 + i * 1.35, 5.33, 3.0)], c, False)
    S.add("lab", 23.6 + 5.4, g); S.anchor("prototypehub", 23.2, 5.3, 3.1)
    # arcade in Bauhaus red with a mustard control deck
    g = S.box(18.3, 6.4, 0, 2.4, 2.4, 3.8, P["red"], P["red"], "#a3361f")
    g += S.q([(20.71, 6.65, 2.2), (20.71, 8.55, 2.2), (20.71, 8.55, 3.4), (20.71, 6.65, 3.4)], INK)
    g += S.q([(20.72, 6.85, 2.35), (20.72, 8.35, 2.35), (20.72, 8.35, 3.25), (20.72, 6.85, 3.25)], P["leaf2"], False)
    g += S.box(20.7, 6.4, 1.6, .8, 2.4, .3, P["mus"], P["mus"], "#b8861f")
    S.add("lab", 19.5 + 7.6, g); S.anchor("arcade", 19.6, 7.6, 3.9)
    # voice gadget on a chrome side table
    g = tube(S, 22.15, 9.75, 0, .14, .14, 1.5) + tube(S, 23.3, 9.75, 0, .14, .14, 1.5) + tube(S, 22.15, 10.9, 0, .14, .14, 1.5) + tube(S, 23.3, 10.9, 0, .14, .14, 1.5)
    g += S.box(22.0, 9.6, 1.5, 1.6, 1.6, .12, P["char"], "#2a2a2c", "#1e1e20")
    g += S.cyl(22.8, 10.4, 1.62, .45, .8, P["cream"], P["creamS"]) + S.ell(22.8, 10.4, 2.43, .45, .45, P["cob"], False) + S.ell(22.8, 10.4, 2.44, .24, .24, "#b9d6f0", False)
    S.add("lab", 22.8 + 10.4, g); S.anchor("voice", 22.8, 10.4, 2.7)
    g = S.ell(24.4, 12.9, .04, 1.6, 1.3, P["mus"]) + S.ell(24.4, 12.9, .3, 1.2, .95, "#f0c96a")
    g += [("c", (24.4, 12.9, 1.0), .78, P["cream"], True)]
    g += S.box(23.9, 12.45, 1.5, .26, .26, .6, P["cream"], P["cream"], P["creamD"]) + S.box(24.65, 12.1, 1.5, .26, .26, .6, P["cream"], P["cream"], P["creamD"])
    g += [("c", (24.6, 13.1, 1.05), .1, INK, False), ("c", (24.9, 12.8, 1.05), .1, INK, False)]
    g += S.cyl(22.4, 13.8, 0, .42, .3, P["cob"], "#1f3b80")
    S.add("lab", 24.4 + 12.9, g); S.anchor("pet", 24.4, 12.9, 2.1)
    fiddle(S, "lab", 25.6, 8.6)
    S.anchor("lbl_lab", 21.6, 15.0, 0); S.anchor("c_lab", 23.0, 9.4, 1.0)
    return S

def render(S, rim, fname, W, Hh, dark=(), pad=46, spill_rooms=()):
    rp = [proj(x, y, H) for x, y in rim]
    minx, maxx = min(p[0] for p in rp), max(p[0] for p in rp); miny, maxy = min(p[1] for p in rp), max(p[1] for p in rp)
    s = min((W - 2 * pad) / (maxx - minx), (Hh - 2 * pad) / (maxy - miny))
    ox = (W - (maxx - minx) * s) / 2 - minx * s; oy = (Hh - (maxy - miny) * s) / 2 - miny * s
    im = Image.new("RGBA", (W * SS, Hh * SS), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    lw = max(1, int(1.5 * SS))
    def PP(p): a, b = proj(*p); return ((a * s + ox) * SS, (b * s + oy) * SS)
    def col(c, room): return mix(c, NIGHT, .58) if room in dark else c
    def draw(d, room):
        nonlocal dr
        if d[0] == "p":
            q = [PP(p) for p in d[1]]
            dr.polygon(q, fill=col(d[2], room))
            if d[3]: dr.line(q + [q[0]], fill=INK, width=lw, joint="curve")
        else:
            _, c, r, fill, ol = d; cx, cy = PP(c); rr = r * 2 * K * s * SS
            dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col(fill, room), outline=INK if ol else None, width=lw if ol else 0)
    for key, room, it in sorted(S.floor, key=lambda t: t[0]):
        for d in it: draw(d, room)
    spill = SPILL
    for r in spill_rooms:
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).polygon([PP(p) for p in spill[r]], fill=hx(P["glow"]) + (115,))
        im = Image.alpha_composite(im, ov); dr = ImageDraw.Draw(im)
    for room, it in S.back:
        for d in it: draw(d, room)
    for key, room, it in sorted(S.groups, key=lambda t: t[0]):
        for d in it: draw(d, room)
    # ---- the cut: clip to the rim (plan outline at wall-top height) and ink the edge
    rim_px = [PP((x, y, H)) for x, y in rim]
    mask = Image.new("L", im.size, 0); ImageDraw.Draw(mask).polygon(rim_px, fill=255)
    a = im.getchannel("A"); im.putalpha(Image.fromarray(__import__("numpy").minimum(__import__("numpy").array(a), __import__("numpy").array(mask))))
    ImageDraw.Draw(im).line(rim_px + [rim_px[0]], fill=INK, width=int(lw * 1.7), joint="curve")
    im = im.resize((W, Hh), Image.LANCZOS); im.save(os.path.join(OUT, fname))
    out = {}
    for k, v in S.anchors.items():
        a_, b_ = proj(*v); out[k] = [round((a_ * s + ox) / W * 100, 2), round((b_ * s + oy) / Hh * 100, 2)]
    return out

A = {}
A["house_dim"] = render(build(), RIM, "house_dim.png", 2400, 1800, dark=("studio", "lab"), spill_rooms=("studio", "lab"), pad=60)
A["house_studio"] = render(build(), RIM, "house_studio.png", 2400, 1800, dark=("lab",), spill_rooms=("lab",), pad=60)
A["house_lit"] = render(build(), RIM, "house_lit.png", 2400, 1800, pad=60)
json.dump(A, open(os.path.join(OUT, "anchors.json"), "w"), indent=1)
