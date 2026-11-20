"""Furnished, sunken hero scene for a plan in plans.py.
The page is the ground at wall-top height H. The house sits in a pit: rooms, gardens and decks at z=0,
a grass bank rising from the house to the page along every front edge, and at the entrance a flight of
stairs cut into the bank with a paved path continuing on the page surface."""
import math
import numpy as np
from engine import Part, poly, box, cyl, disc, cone, rod, ico, hull, cham, cbox, Cam, render
from scene import P, H, HP, T, planks, fiddle, office_chair
from layouts import internal, tree, shrub
from massing import FLOOR, OPEN
from plans import PLANS, M2U
from furnish import furnish
from character import character

B = 1.2          # bank width, metres
STONE, STONE_T, EARTH = "#e2d8c6", "#f2ecdf", "#b9a68a"
GRASS, GRASS2 = "#8fb062", "#86a85a"

# hero entrances: (stair centre x, door) — stairs climb from the garden to the page along +y
HERO_ENTRY = {"P2": dict(x=6.25), "P3": dict(x=5.5), "P6": dict(x=3.75, door=(3.75, 8.5, "x", 1.3))}


def m(v):
    return v * M2U


def xform(part, x, y, w, d, face):
    """local (u along the wall, v away from the wall, z) -> world, in units."""
    t = part.t.copy()
    u, v = t[..., 0].copy(), t[..., 1].copy()
    if face == "py":
        t[..., 0], t[..., 1] = x + u, y + v
    elif face == "ny":
        t[..., 0], t[..., 1] = x + w - u, y + d - v
    elif face == "px":
        t[..., 0], t[..., 1] = x + v, y + d - u
    else:
        t[..., 0], t[..., 1] = x + w - v, y + u
    return Part(t, part.c, part.e)


def dims(w, d, face):
    return (w, d) if face in ("py", "ny") else (d, w)


# mid-century palette (Abraham's references: teak, birch, linoleum blue, oxblood, chrome, orange)
TEAK, TEAK_T, TEAK_D = "#b06c3a", "#c27d48", "#8a5126"
BIRCH, BIRCH_T = "#d8a865", "#e4b979"
LINO = "#53688a"
OXB, OXB_T, OXB_D = "#6c2b29", "#7c3632", "#55211f"
CHROME, ORANGE = "#cfd2d4", "#e8822f"


def tapered_legs(W, D, h, inset=.18, col=TEAK_D, r=.06):
    g = Part()
    for (u, v) in [(inset, inset), (W - inset, inset), (inset, D - inset), (W - inset, D - inset)]:
        g = g + rod((u, v, h), (u + (-.05 if u < W / 2 else .05), v + (-.05 if v < D / 2 else .05), 0), r, col, 6)
    return g


def mushroom(cx, cy, z, s=1.0, col="#f6f1e6"):
    """mushroom table lamp (glowing dome on a stem)"""
    g = cyl(cx, cy, z, .16 * s, .06 * s, col, n=12) + cyl(cx, cy, z, .07 * s, .42 * s, col, n=8)
    return g + dome(cx, cy, z + .72 * s, .34 * s, .3 * s, col, "#ffe7b0", n=14, rings=4)


def records_row(u0, u1, v, z0, z1, cols, step=.07):
    """vertical record sleeves seen edge-on in an open shelf (front at plane v)"""
    g = Part()
    u, k = u0, 0
    while u < u1 - step:
        hh = z1 - (k * 37 % 5) * .03
        g = g + poly([(u, v, z0), (u + step * .8, v, z0), (u + step * .8, v, hh), (u, v, hh)], cols[k % len(cols)])
        u += step; k += 1
    return g


# ------------------------------------------------------------ furniture (local frame, units)
def f_records(W, D):
    """teak record cabinet on tapered legs: two open bays of records, a plant on top"""
    zb, zt = .45, 1.6
    g = tapered_legs(W, D, zb) + box(0, 0, zb, W, D, zt - zb, TEAK, TEAK_T)
    g = g + poly([(.08, D + .01, zb + .08), (W - .08, D + .01, zb + .08), (W - .08, D + .01, zt - .08), (.08, D + .01, zt - .08)], "#5a3418")   # open front
    cols = [P["cream"], P["red"], P["char"], P["cob"], P["creamS"], P["mus"], "#3f6b4a", "#e9a3a0"]
    g = g + records_row(.14, W / 2 - .06, D + .02, zb + .1, zt - .14, cols) + records_row(W / 2 + .06, W - .14, D + .02, zb + .1, zt - .14, cols[3:] + cols[:3])
    g = g + poly([(W / 2 - .03, D + .02, zb + .08), (W / 2 + .03, D + .02, zb + .08), (W / 2 + .03, D + .02, zt - .08), (W / 2 - .03, D + .02, zt - .08)], TEAK)
    return g + cyl(W * .72, D * .5, zt, .2, .32, "#e9e1d0", n=10) + ico((W * .72, D * .5, zt + .62), .36, "#5f8f3e", 1, seed=4)


def f_console(W, D):
    """teak sideboard on tapered legs (two-tone sliding doors), turntable with smoked lid, orange mushroom lamp"""
    zb, zt = .45, 1.65
    g = tapered_legs(W, D, zb) + box(0, 0, zb, W, D, zt - zb, TEAK, TEAK_T)
    for i, c in enumerate([TEAK_D, "#e9e1d0", TEAK_D]):                         # three sliding doors
        u0 = .08 + i * (W - .16) / 3
        g = g + poly([(u0 + .02, D + .01, zb + .08), (u0 + (W - .16) / 3 - .02, D + .01, zb + .08), (u0 + (W - .16) / 3 - .02, D + .01, zt - .08), (u0 + .02, D + .01, zt - .08)], c)
        g = g + cyl(0, 0, 0, .05, .02, "#1f1f22", n=8).rot("x", 90).move(u0 + (W - .16) / 6, D + .02, (zb + zt) / 2)
    tw = min(1.35, W * .55)                                                       # turntable
    g = g + box(.2, .15, zt, tw, D - .3, .16, "#d9d9d4", "#e6e6e1")
    r = min(.42, tw * .32)
    g = g + cyl(.2 + tw * .42, D / 2, zt + .16, r, .03, P["ink"], n=18) + cyl(.2 + tw * .42, D / 2, zt + .19, r * .32, .01, P["red"], n=10)
    g = g + rod((.2 + tw * .85, D * .3, zt + .2), (.2 + tw * .6, D * .55, zt + .22), .025, CHROME, 6)
    lid = box(0, 0, 0, tw, .03, D - .3, "#6b6870").rot("x", 22, (0, 0, 0)).move(.2, .15, zt + .16)       # smoked lid, propped open
    g = g + lid
    return g + mushroom(W - .45, D / 2, zt, 1.0, ORANGE)


def f_counter(W, D):
    g = box(0, 0, 0, W, D, 2.2, "#efe7d8", P["walT"]) + poly([(.1, D + .01, .25), (W - .1, D + .01, .25), (W - .1, D + .01, 1.95), (.1, D + .01, 1.95)], "#e3d8c5")
    g = g + box(.4, .2, 2.2, .8, .7, 1.0, P["char"]) + box(.5, .7, 2.9, .6, .25, .15, P["chr"])
    g = g + cyl(W * .5, D * .5, 2.2, .22, .55, P["red"], n=8) + cyl(W * .65, D * .55, 2.2, .14, .3, P["cream"], n=8) + cyl(W * .72, D * .4, 2.2, .14, .3, P["mus"], n=8)
    return g + fiddle(W - .55, D * .5).scale(.45, .45, .5, (W - .55, D * .5, 0)).move(0, 0, 2.2)


def aalto_frame(W, D, h=1.75, col=BIRCH, colT=BIRCH_T, top=None):
    """bent-plywood desk: four legs that curve into aprons under the top, a birch edge with a linoleum inlay"""
    g = Part()
    for (u, v) in [(.12, .12), (W - .26, .12), (.12, D - .26), (W - .26, D - .26)]:
        g = g + box(u, v, 0, .14, .14, h - .3, col, colT)
    for v in (.1, D - .24):                                                       # aprons, rounded into the legs
        g = g + box(.12, v, h - .32, W - .24, .14, .2, col, colT)
        for u in (.12, W - .4):
            g = g + cbox(u + .14, v + .07, h - .32, .14, .07, .1, .07, col)
    g = g + box(0, 0, h - .12, W, D, .12, col, colT)
    if top:
        g = g + poly([(.08, .08, h + .002), (W - .08, .08, h + .002), (W - .08, D - .08, h + .002), (.08, D - .08, h + .002)], top)
    return g


def anglepoise(u, v, z, reach=1.0, arm="#2f4a7a", shade="#9c9ea2"):
    g = cyl(u, v, z, .2, .08, "#2b2b2e", n=10)
    j1 = (u + .05, v + .1, z + 1.1 * reach); j2 = (u + .1, v + .75 * reach, z + 1.45 * reach)
    g = g + rod((u, v, z + .08), j1, .035, arm, 6) + rod(j1, j2, .035, arm, 6) + ico(j1, .06, "#2b2b2e", 0)
    tip = (j2[0], j2[1] + .28, j2[2] - .22)
    return g + cone(j2, tip, .08, .26, shade, 10) + disc(0, 0, 0, .22, "#ffe7b0", 10, emis=True).rot("x", -55).move(tip[0], tip[1] + .02, tip[2] - .02)


def f_desk(W, D, var):
    if var == "pc":
        return f_desk_old(W, D, var)
    z = 1.75 + .002
    if var == "lab":     # workbench: birch top on white steel, three colour screens, a parts tray
        g = Part()
        for (lu, lv) in [(.1, .1), (W - .25, .1), (.1, D - .25), (W - .25, D - .25)]:
            g = g + box(lu, lv, 0, .15, .15, 1.75, "#ecebe6")
        g = g + box(.1, .1, .35, W - .2, D - .2, .06, "#ecebe6") + box(0, 0, 1.63, W, D, .12, BIRCH, BIRCH_T)
        for i, c in enumerate([P["cob"], P["red"], P["mus"]]):
            u0 = .3 + i * (W - .6) / 3
            g = g + box(u0, .2, z, .8, .2, 1.2, P["ink"]) + poly([(u0 + .08, .41, z + .1), (u0 + .72, .41, z + .1), (u0 + .72, .41, z + 1.1), (u0 + .08, .41, z + 1.1)], c, True)
        return g + box(W * .62, D - .55, z, .7, .35, .08, "#3f9a5a") + box(.4, D - .5, z, .5, .3, .2, "#d9d9d4")
    # studio: Aalto-style desk with a blue linoleum top, silver all-in-one, keyboard, anglepoise, green crate
    g = aalto_frame(W, D, col=P["wal"], colT=P["walT"], top=LINO)                                                       # walnut frame
    mu = W * .48
    g = g + box(mu - .22, .3, z, .44, .32, .03, "#d9dadc") + box(mu - .18, .4, z + .03, .36, .06, .32, "#d9dadc")       # slim stand
    sw, sz0, sz1 = 2.1, z + .3, z + 1.62                                                                                # big silver all-in-one
    g = g + box(mu - sw / 2, .38, sz0, sw, .07, sz1 - sz0, "#e2e3e5")
    g = g + poly([(mu - sw / 2 + .06, .455, sz0 + .22), (mu + sw / 2 - .06, .455, sz0 + .22), (mu + sw / 2 - .06, .455, sz1 - .06), (mu - sw / 2 + .06, .455, sz1 - .06)], "#2c3f66", True)
    g = g + poly([(mu - .9, .46, sz0 + .5), (mu + .05, .46, sz0 + .5), (mu + .05, .46, sz1 - .2), (mu - .9, .46, sz1 - .2)], "#e8b04a", True)
    g = g + poly([(mu + .18, .46, sz0 + .36), (mu + .88, .46, sz0 + .36), (mu + .88, .46, sz1 - .2), (mu + .18, .46, sz1 - .2)], "#cfe0f5", True)
    g = g + poly([(mu - .9, .46, sz0 + .32), (mu + .05, .46, sz0 + .32), (mu + .05, .46, sz0 + .42), (mu - .9, .46, sz0 + .42)], "#e7e9ee", True)
    g = g + box(mu - .45, D - .75, z, .9, .28, .04, "#f1f1ee") + box(mu + .6, D - .7, z, .14, .22, .04, "#f1f1ee")       # keyboard, mouse
    g = g + anglepoise(.3, .3, z, 1.0)
    g = g + box(W - .62, .2, z, .5, .38, .3, "#3f9a5a", "#55b06e") + box(W - .57, .25, z + .3, .4, .28, .02, "#2f7a45")   # green crate
    return g + cyl(W - .35, D - .45, z, .1, .2, "#f3f1ec", n=8)                                                           # mug


def f_desk_old(W, D, var):
    top = BIRCH if var == "pc" else (P["cream"] if var == "lab" else P["wal"])
    g = box(0, 0, 1.75, W, D, .12, top, BIRCH_T if var == "pc" else (top if var != "studio" else P["walT"]))
    for (lu, lv) in [(.1, .1), (W - .25, .1), (.1, D - .25), (W - .25, D - .25)]:
        g = g + box(lu, lv, 0, .15, .15, 1.75, "#1d1d1f" if var == "pc" else P["chr"])
    z = 1.87
    if var == "pc":
        g = g + box(.1, .1, 0, 1.4, D - .2, 1.75, P["navy"]) + poly([(.15, D - .09, .2), (1.45, D - .09, .2), (1.45, D - .09, 1.6), (.15, D - .09, 1.6)], "#3b4b70")
        g = g + box(W - 1.0, .12, z, .7, 1.2, 1.25, P["white"]) + poly([(W - .99, 1.33, z + .1), (W - .31, 1.33, z + .1), (W - .31, 1.33, z + 1.15), (W - .99, 1.33, z + 1.15)], "#1c272b")
        g = g + disc(0, 0, 0, .2, P["cyan"], 14, emis=True).rot("x", 90).move(W - .65, 1.34, z + .75) + disc(0, 0, 0, .2, P["cyan"], 14, emis=True).rot("x", 90).move(W - .65, 1.34, z + .35)
        # main monitor: 27-inch 16:9 (about 61 x 35 cm), thin bezels, between the portrait screen and the tower
        mw, bz = m(.61), .07
        sw_ = mw - 2 * bz; sh_ = sw_ * 9 / 16
        mh = sh_ + 2 * bz
        zc = z + 1.2                                     # shared vertical centre for both screens
        mu_ = W / 2 + .08
        mz0 = zc - mh / 2
        g = g + box(mu_ - mw / 2, .45, mz0, mw, .1, mh, "#151517")
        g = g + poly([(mu_ - sw_ / 2, .555, mz0 + bz), (mu_ + sw_ / 2, .555, mz0 + bz), (mu_ + sw_ / 2, .555, mz0 + bz + sh_), (mu_ - sw_ / 2, .555, mz0 + bz + sh_)], "#2a3a64", True)
        g = g + poly([(mu_ - sw_ / 2, .56, mz0 + bz), (mu_ + sw_ / 2, .56, mz0 + bz), (mu_ + sw_ / 2, .56, mz0 + bz + sh_ * .38), (mu_ - sw_ / 2, .56, mz0 + bz + sh_ * .38)], "#3f6b4a", True)
        g = g + poly([(mu_ + sw_ * .18, .565, mz0 + bz + sh_ * .55), (mu_ + sw_ * .3, .565, mz0 + bz + sh_ * .55), (mu_ + sw_ * .3, .565, mz0 + bz + sh_ * .75), (mu_ + sw_ * .18, .565, mz0 + bz + sh_ * .75)], P["mus"], True)
        # side monitor: 24-inch 16:9 turned portrait (about 30 x 53 cm), same vertical centre, angled toward the chair
        pw_, ph_ = m(.30), m(.53)
        side = box(-pw_, 0, -ph_ / 2, pw_, .1, ph_, "#151517")
        side = side + poly([(-pw_ + bz, .105, -ph_ / 2 + bz), (-bz, .105, -ph_ / 2 + bz), (-bz, .105, ph_ / 2 - bz), (-pw_ + bz, .105, ph_ / 2 - bz)], "#1f2b35", True)
        for k_ in range(6):                                                           # chat list on the side screen
            zz = ph_ / 2 - .22 - k_ * .17
            side = side + ico((-pw_ + .17, .12, zz), .045, ["#9a8cf0", "#6fc3b2", "#e0a72e", "#9a8cf0", "#cfe0f5", "#6fc3b2"][k_], 0)
            side = side + poly([(-pw_ + .26, .11, zz - .03), (-.18, .11, zz - .03), (-.18, .11, zz + .03), (-pw_ + .26, .11, zz + .03)], "#5a6680", True)
        side = side.rot("z", -22)
        sx = mu_ - mw / 2 - .06                                                       # inner edge just left of the main screen
        g = g + side.move(sx, .45, zc)
        # dual monitor arm: one pole clamped to the back edge between the screens, an arm to each
        ARM = "#1d1d1f"
        pu = (sx + mu_ - mw / 2) / 2 - .02
        g = g + box(pu - .12, 0, z - .2, .24, .32, .2, ARM) + box(pu - .07, .08, z, .14, .14, .25, ARM)         # clamp
        g = g + cyl(pu, .15, z, .07, zc - z + .45, ARM, n=8)                                                      # pole
        ra = math.radians(-22)
        cx_s, cy_s = sx + (-pw_ / 2) * math.cos(ra), .45 + (-pw_ / 2) * math.sin(ra)                             # side screen centre (front face)
        bk_s = (cx_s + .12 * math.sin(ra), cy_s - .12 * math.cos(ra))                                            # just behind it
        for (tx, ty) in [(mu_, .38), bk_s]:
            elbow = ((pu + tx) / 2, .2, zc + .08)
            g = g + rod((pu, .15, zc + .05), elbow, .045, ARM, 6) + ico(elbow, .06, ARM, 0) + rod(elbow, (tx, ty, zc), .045, ARM, 6)
            g = g + box(tx - .12, ty - .04, zc - .12, .24, .06, .24, ARM)                                         # VESA plate
        g = g + box(W / 2 - .7, D - .75, z, 1.4, .4, .06, "#2a2a2c")
        g = g + cyl(0.3, D - .3, z, .18, .05, "#e9e5dc", n=8) + rod((0.3, D - .3, z), (0.1, D - .7, z + 1.0), .04, "#e9e5dc", 6) + rod((0.1, D - .7, z + 1.0), (0.45, D - .3, z + 1.35), .04, "#e9e5dc", 6)
        g = g + cone((0.45, D - .28, z + 1.35), (0.55, D - .02, z + 1.05), .07, .22, "#ece8df", 8) + disc(0, 0, 0, .18, "#ffe7b0", 10, emis=True).rot("x", -60).move(0.57, D + .01, z + 1.03)
    elif var == "lab":
        for i, c in enumerate([P["cob"], P["red"], P["mus"]]):
            u0 = .3 + i * (W - .6) / 3
            g = g + box(u0, .2, z, .8, .2, 1.2, P["ink"]) + poly([(u0 + .08, .41, z + .1), (u0 + .72, .41, z + .1), (u0 + .72, .41, z + 1.1), (u0 + .08, .41, z + 1.1)], c, True)
    else:
        g = g + box(.35, .15, z, 1.6, 1.0, 1.2, P["cream"]) + poly([(.5, 1.16, z + .3), (1.8, 1.16, z + .3), (1.8, 1.16, z + 1.05), (.5, 1.16, z + 1.05)], "#2a2f3a", True)
        g = g + poly([(.7, 1.17, z + .6), (1.4, 1.17, z + .6), (1.4, 1.17, z + .8), (.7, 1.17, z + .8)], P["mus"], True)
        for i, c in enumerate([P["red"], P["cob"], P["mus"]]):
            g = g + box(W * .55 + i * .2, .4 + i * .15, z + i * .1, 1.2, .8, .08, c)
    return g


def f_arcade(W, D):
    g = box(0, 0, 0, W, D, 3.8, P["red"]) + box(0, D - .05, 1.55, W, .55, .22, P["mus"])
    return g + poly([(.2, D + .01, 2.1), (W - .2, D + .01, 2.1), (W - .2, D + .01, 3.3), (.2, D + .01, 3.3)], "#86ad57", True)


def f_bed(W, D):
    """low oak platform bed, rounded upholstered headboard, sage duvet, terracotta throw at the foot"""
    oak, oakT = "#c08a52", "#cf9a62"
    g = box(0, .25, 0, W, D - .25, .5, oak, oakT) + cbox(W / 2, .16, 1.15, W / 2, .14, 1.0, .22, "#d9cdb8")
    g = g + box(.1, .35, .5, W - .2, D - .45, .42, "#f4efe6")
    g = g + cbox(W / 2, .3 + D * .6, .98, W / 2 - .02, D * .32, .1, .06, "#8a9a6c")
    g = g + box(.04, D - .7, .95, W - .08, .42, .16, "#c0623d") + box(.04, D - .7, .95, W - .08, .06, .17, "#a9532f")
    return g + cbox(W * .3, .72, 1.12, W * .19, .3, .15, .09, "#f2ece2") + cbox(W * .7, .72, 1.12, W * .19, .3, .15, .09, "#f2ece2") + cbox(W * .5, 1.0, 1.08, W * .14, .16, .12, .07, "#e8a24a")


def f_wardrobe(W, D):
    g = box(0, 0, 0, W, D, 3.9, "#efe7d8", "#f6f0e6") + box(.05, 0, 0, W - .1, D, .18, P["walD"])
    return g + poly([(W / 2 - .02, D + .01, .25), (W / 2 + .02, D + .01, .25), (W / 2 + .02, D + .01, 3.85), (W / 2 - .02, D + .01, 3.85)], "#cbbfa9") + box(W / 2 - .2, D, 1.7, .06, .06, .6, P["wal"]) + box(W / 2 + .14, D, 1.7, .06, .06, .6, P["wal"])


def f_archive(W, D):
    """low plywood credenza: doors with finger holes, an open bay of books, crates and a radio on top"""
    zb, zt = .2, 1.5
    g = box(.05, .05, 0, W - .1, D - .1, zb, "#2b2b2e") + box(0, 0, zb, W, D, zt - zb, BIRCH, BIRCH_T)
    half = W * .5
    for i in range(2):
        u0 = .06 + i * (half - .06) / 2
        g = g + poly([(u0 + .02, D + .01, zb + .06), (u0 + (half - .06) / 2 - .02, D + .01, zb + .06), (u0 + (half - .06) / 2 - .02, D + .01, zt - .06), (u0 + .02, D + .01, zt - .06)], "#cf9e5c")
        g = g + disc(0, 0, 0, .06, "#3a2a1c", 10).rot("x", 90).move(u0 + (half - .06) / 4, D + .02, zt - .3)
    g = g + poly([(half + .04, D + .01, zb + .06), (W - .06, D + .01, zb + .06), (W - .06, D + .01, zt - .06), (half + .04, D + .01, zt - .06)], "#6e4a26")
    u, k = half + .1, 0
    while u < W - .18:
        hh = zt - .14 - (k * 3 % 4) * .06
        g = g + poly([(u, D + .02, zb + .1), (u + .1, D + .02, zb + .1), (u + .1, D + .02, hh), (u, D + .02, hh)], [P["cob"], P["mus"], P["red"], P["cream"], "#3f6b4a"][k % 5]); u += .13; k += 1
    g = g + box(.25, .12, zt, .7, D - .25, .32, P["cob"], "#3b62c2") + box(.3, .17, zt + .32, .6, D - .35, .3, "#f0c33c", "#f6d35a")   # crates
    g = g + box(W * .6, .15, zt, .7, D - .3, .4, "#f3f1ec") + poly([(W * .6 + .08, D - .14, zt + .1), (W * .6 + .3, D - .14, zt + .1), (W * .6 + .3, D - .14, zt + .32), (W * .6 + .08, D - .14, zt + .32)], "#2b2b2e")
    return g + mushroom(W - .3, D / 2, zt, .8, "#a9adb2")


BOUCLE, BOUCLE_T, BOUCLE_D = "#6f8a3a", "#7f9c46", "#5f7831"


def f_sofa_l(W, D, chaise=1.95, seat_d=2.2):
    """low modular boucle sofa (after Abraham's reference): a chaise at local u=0 that runs the full depth D,
    seat modules along the back, a rounded low arm at the far end, orange + grey cushions on the chaise.
    Local frame: u along the back wall, v away from it (v=0 = back)."""
    g = Part()
    back_d, seat_h, back_h, ch = .62, 1.02, 1.9, .22
    n = 2
    mw = (W - chaise - .55) / n
    mods = [(0, chaise, D)] + [(chaise + i * mw, mw, seat_d) for i in range(n)]
    for (u0, w, d) in mods:                                     # seat blocks
        g = g + cbox(u0 + w / 2, back_d + (d - back_d) / 2, seat_h / 2, w / 2 - .03, (d - back_d) / 2 - .02, seat_h / 2, ch, BOUCLE)
    for (u0, w, d) in mods:                                     # back cushions
        g = g + cbox(u0 + w / 2, back_d / 2, back_h / 2, w / 2 - .03, back_d / 2 - .02, back_h / 2, ch, BOUCLE_D)
    ua = chaise + n * mw                                        # rounded low arm, wrapping the far end
    g = g + cbox(ua + .275, seat_d / 2, 1.4 / 2, .26, seat_d / 2 - .03, 1.4 / 2, .26, BOUCLE)
    g = g + cbox(chaise * .32, back_d + .28, seat_h + .42, .42, .14, .4, .12, "#d0632a")   # orange cushion
    g = g + cbox(chaise * .62, back_d + .4, seat_h + .36, .42, .13, .34, .12, "#cbc4b6")   # grey cushion
    return g


def f_sofa(W, D):
    g = box(0, 0, 0, W, D, .9, P["oli"], P["oliT"]) + box(0, 0, .9, W, D * .38, .95, P["oli"], P["oliT"])
    g = g + box(0, 0, .9, .5, D, .45, P["oli"], P["oliT"]) + box(W - .5, 0, .9, .5, D, .45, P["oli"], P["oliT"])
    return g + box(W * .2, D * .42, .9, W * .2, D * .45, .08, P["mus"]) + box(W * .26, D * .45, .98, .9, .2, .6, P["cob"])


def f_armchair(W, D):
    """orange corduroy swivel lounge chair (reference): chrome four-star base, one-piece seat and tall
    tufted back, no arms. Local frame: v=0 at the wall, front at v=D."""
    OR, OR_T, OR_D = "#df6a33", "#ea7c45", "#c4552a"
    cu, cv = W / 2, D / 2 + .05
    g = Part()
    for a_ in (45, 135, 225, 315):                                             # four-star chrome base
        ra = math.radians(a_)
        g = g + rod((cu, cv, .32), (cu + .62 * math.cos(ra), cv + .62 * math.sin(ra), .05), .045, CHROME, 6)
        g = g + ico((cu + .62 * math.cos(ra), cv + .62 * math.sin(ra), .04), .05, "#9b9b96", 0)
    g = g + cyl(cu, cv, .3, .07, .32, CHROME, n=8) + cyl(cu, cv, .6, .2, .06, "#9b9b96", n=10)
    g = g + cbox(cu, cv + .05, .9, W / 2 - .06, D / 2 - .12, .2, .14, OR)          # seat cushion
    g = g + box(cu - W / 2 + .14, cv + .05 - .02, 1.08, W - .28, .03, .02, OR_D)     # corduroy seam
    back = cbox(cu, .32, 1.86, W / 2 - .08, .15, .82, .14, OR)                      # tall tufted back, meeting the seat
    for (du, dz) in [(-.2, 2.25), (.2, 2.25), (-.2, 1.75), (.2, 1.75)]:
        back = back + ico((cu + du, .45, dz), .045, OR_D, 0)
    back = back + box(cu - W / 2 + .12, .44, 2.0, W - .24, .02, .03, OR_D)
    return g + back.rot("x", 12, (cu, .3, 1.0))      # + tips the top back toward the wall


def f_treadmill(W, D):
    g = box(0, 0, 0, W, D, .32, "#3b3b3e", "#4a4a4e") + poly([(.9, .2, .33), (W - .2, .2, .33), (W - .2, D - .2, .33), (.9, D - .2, .33)], "#1d1d1f")
    g = g + poly([(.9, -.01, .12), (W - .2, -.01, .12), (W - .2, -.01, .2), (.9, -.01, .2)], P["red"]) + poly([(.9, D + .01, .12), (W - .2, D + .01, .12), (W - .2, D + .01, .2), (.9, D + .01, .2)], P["red"])
    g = g + box(0, 0, 0, .9, D, .6, "#2e2e31", "#3b3b3e")
    for v in (.15, D - .15):
        g = g + rod((.5, v, .55), (.25, v, 2.5), .07, "#55555a") + rod((.3, v, 2.2), (1.9, v, 2.15), .05, "#9b9b96")
    con = box(.05, .2, 2.42, .5, D - .4, .18, "#2b2b2e") + poly([(.15, .35, 2.605), (.45, .35, 2.605), (.45, D - .35, 2.605), (.15, D - .35, 2.605)], P["mus"], True)
    return g + con


def f_shoes(W, D):
    g = box(0, 0, 0, W, D, .9, P["wal"], P["walT"])
    return g + box(W * .2, D * .2, .9, .35, .7, .25, P["red"]) + box(W * .55, D * .2, .9, .35, .7, .25, "#f3f1ec")


def f_lounger(W, D):
    g = box(.1, .1, .4, W - .2, D - .2, .15, "#c49c60") + box(.1, .1, 0, .15, .15, .4, P["walD"]) + box(W - .25, .1, 0, .15, .15, .4, P["walD"])
    back = box(.1, 0, .55, W - .2, .7, .12, "#c49c60").rot("x", 35, (0, .1, .55))
    return g + back + box(.25, .9, .58, W - .5, .9, .1, "#f3f1ec")


def f_bench(W, D):
    return box(0, 0, .55, W, D, .14, P["wal"], P["walT"]) + box(.15, .1, 0, .2, D - .2, .55, P["walD"]) + box(W - .35, .1, 0, .2, D - .2, .55, P["walD"])


def f_bookcase(W, D):
    """oxblood cube shelving (reference 2): books, records, a pair of speakers and a white mushroom lamp"""
    Hb = 3.85
    rows = [0, .95, 1.9, 2.85]
    cols_n = max(2, int(round(W / 1.1)))
    cw = W / cols_n
    g = poly([(0, .03, 0), (W, .03, 0), (W, .03, Hb), (0, .03, Hb)], OXB_D)
    for z in rows + [Hb - .1]:
        g = g + box(0, 0, z, W, D, .1, OXB, OXB_T)
    for i in range(cols_n + 1):
        g = g + box(min(i * cw, W - .1), 0, 0, .1, D, Hb, OXB, OXB_T)
    bc = [P["cream"], P["cob"], P["mus"], "#3f6b4a", P["red"], "#e9e1d0", P["char"], "#d98b6a"]
    k = 0
    for ri, z in enumerate(rows):
        for ci in range(cols_n):
            u0, z0 = ci * cw + .14, z + .1
            kind = (ri * 3 + ci * 2) % 5
            if kind == 1 and ri == 3:                                             # speaker
                g = g + box(u0 + .05, .1, z0, cw - .3, D - .18, .75, TEAK, TEAK_T)
                g = g + disc(0, 0, 0, .2, "#1d1d1f", 12).rot("x", 90).move(u0 + .05 + (cw - .3) / 2, D - .07, z0 + .3) + disc(0, 0, 0, .08, "#1d1d1f", 10).rot("x", 90).move(u0 + .05 + (cw - .3) / 2, D - .07, z0 + .62)
            elif kind == 3:                                                        # white mushroom lamp
                g = g + mushroom(u0 + (cw - .2) / 2, D / 2, z0, .75)
            elif kind == 4:                                                        # books lying flat + a small plant
                for j, c in enumerate([P["cream"], P["cob"], "#d98b6a"]):
                    g = g + box(u0 + .02 + j * .02, .15, z0 + j * .1, cw - .55, D - .28, .1, c)
                g = g + cyl(u0 + cw - .42, D / 2, z0, .1, .18, "#e9e1d0", n=8) + ico((u0 + cw - .42, D / 2, z0 + .38), .2, "#5f8f3e", 1, seed=ri)
            else:                                                                  # books
                u = u0
                while u < u0 + cw - .32:
                    bw = .1 + (k * 37 % 7) / 100
                    g = g + box(u, .14, z0, bw, D - .24, .5 + (k * 53 % 25) / 100, bc[k % len(bc)])
                    u += bw + .015; k += 1
    return g


def f_backpack(W, D):
    """hiking backpack hung on a wall peg, trekking poles leaning beside it, boots below"""
    pw = min(1.15, W * .62)
    g = box(pw / 2 - .07, 0, 3.05, .14, .45, .1, P["walD"])                                     # peg
    g = g + cbox(pw / 2, .42, 2.15, pw / 2 - .05, .33, .78, .1, "#d0582f")                      # body
    g = g + cbox(pw / 2, .5, 2.95, pw / 2 - .1, .3, .14, .06, "#9c3d22")                       # lid
    g = g + cbox(pw / 2, .76, 1.95, pw / 2 - .25, .1, .35, .05, "#b84a2a")                      # front pocket
    g = g + cyl(0, 0, 0, .2, pw + .1, "#4b6a8a", n=10).rot("y", 90).move(-.05, .45, 1.32)   # sleeping roll under it
    for du in (.22, pw - .22):
        g = g + box(du - .04, .05, 1.6, .08, .05, 1.3, "#2f2f33")                             # straps
    for i, du in enumerate((pw + .25, pw + .45)):                                               # trekking poles
        g = g + rod((du, .55 + i * .08, 0), (du - .05, .1, 3.2), .04, "#3b3b3e", 6) + rod((du - .05, .1, 3.2), (du - .06, .08, 3.5), .07, "#c8442b", 6)
    for du in (.1, .5):                                                                        # boots
        g = g + box(du, .25, 0, .32, .6, .3, "#6b4a2e", "#7d5836") + box(du, .25, .3, .32, .28, .35, "#6b4a2e", "#7d5836")
    return g


def f_suitcase(W, D):
    g = cbox(W / 2, D / 2, 1.0, W / 2 - .02, D / 2 - .02, .95, .08, "#3f6b8a")
    for (u, z, c) in [(.25, 1.4, P["mus"]), (W - .55, .7, P["red"]), (.4, .55, P["cream"]), (W - .5, 1.5, "#9db07f")]:
        g = g + poly([(u, D + .01, z), (u + .3, D + .01, z), (u + .3, D + .01, z + .28), (u, D + .01, z + .28)], c)
    return g + box(W / 2 - .3, D / 2 - .05, 1.95, .6, .1, .08, "#2b2b2e") + box(W / 2 - .3, D / 2 - .05, 1.95, .06, .1, .35, "#2b2b2e") + box(W / 2 + .24, D / 2 - .05, 1.95, .06, .1, .35, "#2b2b2e")


def gym3d(cx, cy, w, d, var):
    """small home-workout pieces for the deck"""
    X, Y = cx - w / 2, cy - d / 2
    g = Part()
    if var == "pullup":        # freestanding pull-up station, bar running along y
        top = H - .1           # stays below the wall tops, so nothing pokes out above the page
        for yy in (Y + .1, Y + d - .25):
            g = g + box(X + w / 2 - .08, yy, 0, .16, .16, top, "#2b2b2e") + box(X, yy - .05, 0, w, .26, .12, "#2b2b2e")
        g = g + rod((X + w / 2, Y + .1, top - .15), (X + w / 2, Y + d - .1, top - .15), .07, "#9b9b96", 8)
        for yy in (Y + .45, Y + d - .6):
            g = g + box(X + w / 2 - .09, yy, top - .22, .18, .15, .15, "#c8442b")
    elif var == "mat":
        g = box(X, Y, 0, w, d, .05, "#6f8f6a", "#7fa07a") + box(X, Y, .05, w * .16, d, .12, "#6f8f6a", "#86a881")
    elif var == "parallettes":
        for yy in (Y + .05, Y + d - .2):
            g = g + rod((X + .05, yy + .07, 0), (X + .05, yy + .07, .35), .05, "#2b2b2e", 6) + rod((X + w - .05, yy + .07, 0), (X + w - .05, yy + .07, .35), .05, "#2b2b2e", 6)
            g = g + rod((X, yy + .07, .38), (X + w, yy + .07, .38), .06, "#d9a066", 8)
    elif var == "kettlebell":
        r = min(w, d) / 2
        g = ico((cx, cy, r * .85), r * .85, "#2b2b2e", 1) + rod((cx - r * .5, cy, r * 1.5), (cx + r * .5, cy, r * 1.5), .06, "#2b2b2e", 6)
        g = g + rod((cx - r * .5, cy, r * 1.2), (cx - r * .5, cy, r * 1.5), .06, "#2b2b2e", 6) + rod((cx + r * .5, cy, r * 1.2), (cx + r * .5, cy, r * 1.5), .06, "#2b2b2e", 6)
    elif var == "dumbbells":
        for i in range(2):
            yy = cy - .15 + i * .3
            g = g + rod((X + .1, yy, .14), (X + w - .1, yy, .14), .05, "#9b9b96", 6) + cyl(X + .15, yy, 0, .14, .28, "#c8442b", n=8).rot("y", 90, (X + .15, yy, .14)) if False else g + rod((X + .1, yy, .14), (X + w - .1, yy, .14), .05, "#9b9b96", 6) + box(X + .05, yy - .13, 0, .18, .26, .28, "#c8442b") + box(X + w - .23, yy - .13, 0, .18, .26, .28, "#c8442b")
    return g


def dome(cx, cy, ztop, r, h, col, inner, n=18, rings=5):
    """hemispherical lamp shade, open at the bottom, warm glow inside"""
    import math as _m
    g = Part()
    prev = None
    for j in range(rings + 1):
        t = j / rings * (_m.pi / 2)
        rr, zz = r * _m.sin(t) if j else 0.0, ztop - h * (1 - _m.cos(t))
        ring = [(cx + rr * _m.cos(2 * _m.pi * i / n), cy + rr * _m.sin(2 * _m.pi * i / n), zz) for i in range(n)]
        if prev is not None:
            for i in range(n):
                p0, p1, q0, q1 = prev[i], prev[(i + 1) % n], ring[i], ring[(i + 1) % n]
                g = g + poly([p0, p1, q1, q0], col)
        prev = ring
    return g + disc(cx, cy, ztop - h + .02, r * .97, inner, n, emis=True)


def arc_lamp(bx, by, tx, ty):
    """statement arc floor lamp: round base at (bx, by), chrome stem rising straight then arcing over the
    seating, glossy orange dome hanging above (tx, ty). Units."""
    import math as _m
    chrome = "#cfd2d4"
    g = cyl(bx, by, 0, .42, .22, "#ece7de", "#f6f2ea", n=16)
    zp = 1.95             # the whole lamp stays under page level (H) so the rim never clips the arc
    g = g + rod((bx, by, .22), (bx, by, zp), .05, chrome, 8)
    dx, dy = tx - bx, ty - by
    L = _m.hypot(dx, dy); ux, uy = dx / L, dy / L
    th_end = .66 * _m.pi
    a = L / (1 - _m.cos(th_end)); b = 2.05
    pts = []
    n = 18
    for i in range(n + 1):
        th = th_end * i / n
        h = a * (1 - _m.cos(th))
        pts.append((bx + ux * h, by + uy * h, zp + b * _m.sin(th)))
    for p0, p1 in zip(pts, pts[1:]):
        g = g + rod(p0, p1, .045, chrome, 6)
    ex, ey, ez = pts[-1]
    g = g + rod((ex, ey, ez), (ex, ey, ez - .12), .04, chrome, 6) + cyl(ex, ey, ez - .2, .09, .1, chrome, n=8)
    g = g + dome(ex, ey, ez - .14, .62, .52, "#f0a23b", "#ffe2a8")
    return g


def plinth3d(cx, cy, w, var):
    """white showcase plinth with one project on top, turned to face the room diagonal"""
    h = {"Phone": 2.3, "Game": 1.8, "Laptop": 1.35}.get(var, 1.8)
    hw = w / 2
    g = box(cx - hw, cy - hw, 0, w, w, h, "#ece7de", "#f8f5ef") + box(cx - hw - .05, cy - hw - .05, h - .08, w + .1, w + .1, .08, "#f8f5ef")
    obj = Part()
    if var == "Phone":          # GokoMart on a phone stand
        obj = box(-.25, -.12, 0, .5, .3, .08, "#2b2b2e") + box(-.06, -.12, .08, .12, .1, .3, "#2b2b2e")
        ph = box(-.3, 0, 0, .6, .09, 1.15, "#1c1c1e") + poly([(-.25, .095, .07), (.25, .095, .07), (.25, .095, 1.08), (-.25, .095, 1.08)], "#f4f1ea", True)
        ph = ph + poly([(-.21, .1, .82), (.21, .1, .82), (.21, .1, 1.0), (-.21, .1, 1.0)], "#3f8f5a", True) + poly([(-.21, .1, .45), (.02, .1, .45), (.02, .1, .76), (-.21, .1, .76)], P["mus"], True)
        ph = ph + poly([(.06, .1, .45), (.21, .1, .45), (.21, .1, .76), (.06, .1, .76)], "#9db07f", True) + poly([(-.21, .1, .14), (.21, .1, .14), (.21, .1, .3), (-.21, .1, .3)], "#0a6cff", True)
        obj = obj + ph.rot("x", 12).move(0, -.05, .1)
    elif var == "Game":         # the pet game on a handheld console
        obj = box(-.38, -.08, .02, .76, .16, 1.0, "#f2efe8") + box(-.2, -.1, 0, .4, .2, .06, "#2b2b2e")
        obj = obj + poly([(-.3, .085, .45), (.3, .085, .45), (.3, .085, .92), (-.3, .085, .92)], "#2a3a28", True)
        for (px_, pz, c) in [(-.1, .6, "#ffad5c"), (0, .6, "#ffad5c"), (.1, .6, "#ffad5c"), (-.1, .7, "#151517"), (0, .7, "#ffad5c"), (.1, .7, "#151517"), (-.1, .8, "#ffad5c"), (.1, .8, "#ffad5c")]:
            obj = obj + poly([(px_ - .05, .09, pz), (px_ + .05, .09, pz), (px_ + .05, .09, pz + .1), (px_ - .05, .09, pz + .1)], c, True)
        obj = obj + poly([(-.25, .09, .22), (-.11, .09, .22), (-.11, .09, .28), (-.25, .09, .28)], "#2b2b2e") + poly([(-.21, .09, .15), (-.15, .09, .15), (-.15, .09, .35), (-.21, .09, .35)], "#2b2b2e")
        obj = obj + disc(0, 0, 0, .06, P["red"], 8).rot("x", 90).move(.17, .09, .3) + disc(0, 0, 0, .06, P["cob"], 8).rot("x", 90).move(.26, .09, .2)
    elif var == "Laptop":       # Prototype Hub open on a laptop
        obj = box(-.5, -.35, 0, 1.0, .65, .06, "#c9c9c4", "#d9d9d4")
        scr = box(-.5, 0, 0, 1.0, .05, .68, "#c9c9c4") + poly([(-.45, .055, .05), (.45, .055, .05), (.45, .055, .63), (-.45, .055, .63)], "#f7f7f9", True)
        scr = scr + poly([(-.42, .06, .52), (.42, .06, .52), (.42, .06, .6), (-.42, .06, .52 + .08)], "#0a6cff", True)
        for i in range(3):
            scr = scr + poly([(-.38 + i * .28, .06, .12), (-.16 + i * .28, .06, .12), (-.16 + i * .28, .06, .45), (-.38 + i * .28, .06, .45)], ["#dfe9ff", "#ffe9c2", "#e3f2df"][i], True)
        obj = obj + scr.rot("x", 15).move(0, -.32, .06)
    return g + obj.rot("z", -45).move(cx, cy, h)


LOCAL = dict(sofaL=lambda W, D: f_sofa_l(W, D, chaise=m(.8), seat_d=m(.9)), bookcase=f_bookcase, backpack=f_backpack, suitcase=f_suitcase, console=f_console, counter=f_counter, arcade=f_arcade, bed=f_bed, wardrobe=f_wardrobe, sofa=f_sofa, treadmill=f_treadmill, lounger=f_lounger, bench=f_bench)


def room_of(plan, px, py):
    for r in plan["rooms"]:
        if r[0] == "apron":
            continue
        for (x, y, w, d) in r[3]:
            if x <= px <= x + w and y <= py <= y + d:
                return r, (x, y, w, d)
    return None, None


def facing(plan, it):
    x, y, w, d, k, lab, sh = it
    r, rr = room_of(plan, x + w / 2, y + d / 2)
    if rr is None:
        return "py"
    rx, ry, rw, rd = rr
    gaps = {"px": x - rx, "nx": rx + rw - (x + w), "py": y - ry, "ny": ry + rd - (y + d)}
    if k in ("sofa", "sofaL"):      # face the middle of the room along the short axis
        if w >= d:
            return "py" if (y + d / 2) < ry + rd / 2 else "ny"
        return "px" if (x + w / 2) < rx + rw / 2 else "nx"
    if k == "treadmill":    # run along the long axis, console at the back end
        return "py" if w >= d else "px"
    return min(gaps, key=gaps.get)


SEGMENTS = []     # (item, first triangle, end) per furniture item, filled by furniture3d (used by the exporter)


def furniture3d(key):
    plan = PLANS[key]
    items, decos = furnish(key)
    g = Part()
    SEGMENTS.clear()
    for it in items:
        _n0 = len(g.t)
        try:
            x, y, w, d, k, lab, sh = it
            X, Y, W, D = m(x), m(y), m(w), m(d)
            cx, cy = X + W / 2, Y + D / 2
            if k == "ctable":     # bent walnut plywood coffee table (reference): leg panel at -x, magazine pocket at +x
                WAL_, WAL_T_ = "#7a4526", "#8b5530"
                h, t, Rr = m(.36), .07, .22
                L = W - m(.32)                                      # top length; the pocket takes the last 32 cm
                prof = [(0, .02)]
                for i in range(5):                                  # leg end: up, then bend into the top
                    a_ = math.radians(180 - 90 * i / 4)
                    prof.append((Rr + Rr * math.cos(a_), h - Rr + Rr * math.sin(a_)))
                for i in range(5):                                  # far end: bend down
                    a_ = math.radians(90 - 90 * i / 4)
                    prof.append((L - Rr + Rr * math.cos(a_), h - Rr + Rr * math.sin(a_)))
                for i in range(9):                                  # U-turn: down, round the bottom, up to the lip
                    a_ = math.radians(180 + 180 * i / 8)
                    rr_ = (W - L) / 2
                    prof.append((L + rr_ + rr_ * math.cos(a_), .32 + rr_ * .9 * math.sin(a_) - .0))
                prof.append((W, .32 + h * .35))
                for (p0, p1) in zip(prof, prof[1:]):
                    (x0_, z0_), (x1_, z1_) = p0, p1
                    dx_, dz_ = x1_ - x0_, z1_ - z0_
                    ln = math.hypot(dx_, dz_) or 1
                    nx_, nz_ = -dz_ / ln * t, dx_ / ln * t           # thickness toward the inside of the curve
                    A_, B_ = (X + x0_, z0_), (X + x1_, z1_)
                    C_, D_ = (X + x1_ - nx_, z1_ - nz_), (X + x0_ - nx_, z0_ - nz_)
                    for (pa, pb, col_) in [(A_, B_, WAL_T_), (D_, C_, WAL_)]:
                        g = g + poly([(pa[0], Y, pa[1]), (pb[0], Y, pb[1]), (pb[0], Y + D, pb[1]), (pa[0], Y + D, pa[1])], col_)
                    for yy in (Y, Y + D):
                        g = g + poly([(A_[0], yy, A_[1]), (B_[0], yy, B_[1]), (C_[0], yy, C_[1]), (D_[0], yy, D_[1])], "#5e3319")
                # pocket: a red book with a face and a magazine; on top: a plant in glass, a candle on a tray
                px_ = X + L + (W - L) / 2
                book = box(-.04, 0, 0, .08, D * .38, .62, "#d9412b").rot("y", -12)
                g = g + book.move(px_ - .05, Y + D * .12, .2)
                g = g + ico((px_ + .03, Y + D * .22, .66), .05, "#f3f1ec", 0) + ico((px_ + .03, Y + D * .36, .66), .05, "#f3f1ec", 0)
                g = g + box(-.03, 0, 0, .06, D * .36, .55, "#f3f1ec").rot("y", 10).move(px_ + .08, Y + D * .56, .2)
                g = g + cyl(X + W * .25, Y + D * .3, h, .26, .04, "#e2cfa8", n=12) + cyl(X + W * .22, Y + D * .3, h + .04, .1, .22, "#f4efe6", "#c9a27a", n=10)
                g = g + cyl(X + W * .45, Y + D * .65, h, .14, .22, "#a9c2b8", n=10) + ico((X + W * .45, Y + D * .65, h + .45), .26, "#7fa356", 1, seed=7)
                continue
            if k == "rug" and lab == "blob":     # cream rug with charcoal organic shapes (workspace reference)
                g = g + poly([(X, Y, .02), (X + W, Y, .02), (X + W, Y + D, .02), (X, Y + D, .02)], "#ece5d6")
                for (fx, fy, rx, ry) in [(.24, .32, .13, .17), (.56, .66, .17, .08), (.8, .3, .08, .13), (.42, .88, .06, .05), (.78, .84, .1, .06)]:
                    g = g + disc(X + W * fx, Y + D * fy, .03, W * rx, "#5b5753", 18, ry=D * ry)
                g = g + disc(X + W * .24, Y + D * .32, .035, W * .065, "#ece5d6", 14, ry=D * .085)
                continue
            if k == "rug" and lab == "check":     # cream rug with terracotta checks (Abraham's reference)
                g = g + poly([(X, Y, .02), (X + W, Y, .02), (X + W, Y + D, .02), (X, Y + D, .02)], "#ede3cf")
                c = m(.2); gap = m(.022)
                ni, nj = int(round(W / c)), int(round(D / c))
                cw, cd = W / ni, D / nj
                for i in range(ni):
                    for j in range(nj):
                        if (i + j) % 2 == 0:
                            x0_, y0_ = X + i * cw + gap, Y + j * cd + gap
                            g = g + poly([(x0_, y0_, .03), (x0_ + cw - 2 * gap, y0_, .03), (x0_ + cw - 2 * gap, y0_ + cd - 2 * gap, .03), (x0_, y0_ + cd - 2 * gap, .03)], "#b5654b")
                continue
            if k == "rug":
                g = g + poly([(X, Y, .02), (X + W, Y, .02), (X + W, Y + D, .02), (X, Y + D, .02)], P["chkA"])
                g = g + poly([(X + .3, Y + .3, .03), (X + W - .3, Y + .3, .03), (X + W - .3, Y + D - .3, .03), (X + .3, Y + D - .3, .03)], P["chkB"])
                continue
            if k == "gym":
                g = g + gym3d(cx, cy, W, D, lab); continue
            if k == "arclamp":
                # hang the shade over the middle of the nearest sofa, toward its front edge
                q = min([q for q in items if q[4] in ("sofa", "sofaL")], key=lambda q: (q[0] + q[2] / 2 - x) ** 2 + (q[1] + q[3] / 2 - y) ** 2)
                if q[4] == "sofaL":     # over the seats, not the chaise (the chaise sits at the +x end)
                    g = g + arc_lamp(cx, cy, m(q[0] + (q[2] - .8) / 2), m(q[1] + q[3] - .55)); continue
                g = g + arc_lamp(cx, cy, m(q[0] + q[2] / 2), m(q[1] + q[3] * .35)); continue
            if k == "plinth":
                g = g + plinth3d(cx, cy, min(W, D), lab); continue
            if k == "lamp":       # mid-century floor lamp: tripod legs, slim pole, angled orange cone
                for a_ in (0, 120, 240):
                    ra = math.radians(a_)
                    g = g + rod((cx, cy, .9), (cx + .38 * math.cos(ra), cy + .38 * math.sin(ra), 0), .035, "#2b2b2e", 6)
                g = g + rod((cx, cy, .9), (cx, cy, 3.2), .035, "#2b2b2e", 6)
                sg = -1 if lab == "in" else 1         # "in": shade turned back toward the room from a corner
                g = g + cone((cx, cy, 3.25), (cx + sg * .32, cy + sg * .32, 2.95), .1, .36, ORANGE, 12) + disc(0, 0, 0, .3, "#ffe7b0", 12, emis=True).rot("y", 45).rot("z", 45 if sg > 0 else 225).move(cx + sg * .3, cy + sg * .3, 2.93); continue
            if k == "plant":
                g = g + fiddle(cx, cy).scale(.6, .6, .75, (cx, cy, 0)); continue
            if k == "tree":
                g = g + tree(cx, cy, W / 3.0); continue
            if k == "shrub":
                g = g + shrub(cx, cy, W / 2); continue
            if k == "stone":
                g = g + cyl(cx, cy, 0, W / 2, .05, "#e8e0cf", n=8); continue
            if k == "pond":
                g = g + disc(cx, cy, .01, W / 2 + .25, "#cdbf9f", n=16, ry=D / 2 + .25) + disc(cx, cy, .02, W / 2, "#6fa3c4", n=16, ry=D / 2); continue
            if k == "pet":
                r = W / 2
                g = g + cyl(cx, cy, 0, r, .3, P["mus"], n=12) + cyl(cx, cy, .3, r * .78, .05, "#f0c96a", n=12) + ico((cx, cy, .3 + r * .5), r * .5, P["cream"], 1, (1, 1, .9))
                g = g + ico((cx + r * .3, cy + r * .35, .3 + r * .6), .08, P["ink"], 0) + ico((cx + r * .42, cy + r * .15, .3 + r * .6), .08, P["ink"], 0); continue
            if k == "table":
                if lab == "Voice":
                    g = g + cyl(cx, cy, 0, W / 2, 1.5, P["char"], n=8) + cyl(cx, cy, 1.5, W / 2 * .8, .8, P["cream"], n=10) + cyl(cx, cy, 2.3, W / 2 * .8, .03, "#b9d6f0", n=10, emis=True)
                elif sh == "rect":     # teak nightstand with a drawer and a white mushroom lamp
                    g = g + box(X, Y, .25, W, D, .9, TEAK, TEAK_T) + box(X + .08, Y + .08, 0, W - .16, D - .16, .25, TEAK_D)
                    g = g + poly([(X + .08, Y + D + .01, .7), (X + W - .08, Y + D + .01, .7), (X + W - .08, Y + D + .01, 1.08), (X + .08, Y + D + .01, 1.08)], TEAK_D)
                    g = g + mushroom(cx, cy, 1.15, .8)
                else:
                    g = g + cyl(cx, cy, 0, .3, .9, P["char"], n=8) + cyl(cx, cy, .9, W / 2, .2, P["wal"], P["walT"], n=8) + cyl(cx - .3, cy - .2, 1.1, .2, .4, P["pink"], n=8) + box(cx, cy - .1, 1.1, .8, .6, .12, P["cob"])
                continue
            if k == "chair":
                if sh == "round":
                    r, rr = room_of(plan, x + w / 2, y + d / 2)
                    yaw = 0
                    if rr:   # turn toward the nearest desk
                        desks = [q for q in items if q[4] == "desk" and abs((q[0] + q[2] / 2) - (x + w / 2)) + abs((q[1] + q[3] / 2) - (y + d / 2)) < 2.5]
                        if desks:
                            q = desks[0]; dx, dy = (q[0] + q[2] / 2) - (x + w / 2), (q[1] + q[3] / 2) - (y + d / 2)
                            yaw = math.degrees(math.atan2(-dx, dy))     # the seat faces local +y; turn it toward the desk
                    g = g + (office_chair(cx, cy, yaw, frame="#c8442b", seat="#dcd9d2") if lab == "Mesh" else office_chair(cx, cy, yaw))
                else:
                    f = facing(plan, it); Wl, Dl = dims(W, D, f)
                    g = g + xform(f_armchair(Wl, Dl), X, Y, W, D, f)
                continue
            if k == "shelf":
                f = facing(plan, it); Wl, Dl = dims(W, D, f)
                fn = f_records if lab == "Records" else (f_shoes if lab == "Shoes" else f_archive)
                g = g + xform(fn(Wl, Dl), X, Y, W, D, f); continue
            if k == "desk":
                f = facing(plan, it); Wl, Dl = dims(W, D, f)
                var = "pc" if "PC" in lab else ("lab" if lab == "Bench" else "studio")
                g = g + xform(f_desk(Wl, Dl, var), X, Y, W, D, f); continue
            if k in LOCAL:
                f = facing(plan, it); Wl, Dl = dims(W, D, f)
                g = g + xform(LOCAL[k](Wl, Dl), X, Y, W, D, f); continue
        finally:
            SEGMENTS.append((it, _n0, len(g.t)))
    return g, decos


def decos3d(key, decos):
    plan = PLANS[key]
    g = Part()
    for (wall, x0, y0, a, b, k) in decos:
        if wall == "top":
            mid = (x0 + (a + b) / 2, y0 - .1)
        else:
            mid = (x0 - .1, y0 + (a + b) / 2)
        r, _ = room_of(plan, *mid)
        ext = r is None
        A, Bq = m(a), m(b)
        X0, Y0 = m(x0), m(y0)
        def q(s0, s1, z0, z1, col, em=False, off=.03):
            if wall == "top":
                return poly([(X0 + s0, Y0 + off, z0), (X0 + s1, Y0 + off, z0), (X0 + s1, Y0 + off, z1), (X0 + s0, Y0 + off, z1)], col, em)
            return poly([(X0 + off, Y0 + s0, z0), (X0 + off, Y0 + s1, z0), (X0 + off, Y0 + s1, z1), (X0 + off, Y0 + s0, z1)], col, em)
        if k == "window" and ext:
            g = g + q(A, Bq, 1.2, 3.9, P["char"]) + q(A + .2, Bq - .2, 1.35, 3.75, P["glass"], True, .04) + q(A + .2, Bq - .2, 1.35, 2.3, P["glass2"], True, .045)
            mid_ = (A + Bq) / 2
            g = g + q(mid_ - .05, mid_ + .05, 1.35, 3.75, P["char"], off=.05)
        elif k == "photos":
            n = max(2, int((Bq - A) / 1.05))
            if ext:
                for i in range(n):
                    s0 = A + .1 + i * (Bq - A - .2) / n
                    for (z0, z1) in ((2.6, 3.4), (1.6, 2.3)):
                        g = g + q(s0, s0 + .75, z0, z1, ["#f3f1ec", P["ink"]][i % 2], off=.03) + q(s0 + .08, s0 + .67, z0 + .08, z1 - .08, ["#8fb3c9", "#c9a27a", "#9db07f", "#d98b6a"][(i + int(z0)) % 4], off=.04)
                rail0 = A + .1
                g = g + (box(X0 + rail0, Y0 + .02, 3.75, Bq - A - .2, .12, .12, "#1d1d1f") if wall == "top" else box(X0 + .02, Y0 + rail0, 3.75, .12, Bq - A - .2, .12, "#1d1d1f"))
            else:    # frames leaning on top of the low wall
                for i in range(n):
                    s0 = A + .15 + i * (Bq - A - .3) / n
                    fr = box(0, 0, 0, .7, .08, .85, ["#f3f1ec", P["ink"]][i % 2]) + poly([(.08, .09, .08), (.62, .09, .08), (.62, .09, .77), (.08, .09, .77)], ["#8fb3c9", "#c9a27a", "#9db07f", "#d98b6a"][i % 4])
                    fr = fr.rot("x", -8, (0, 0, 0))
                    if wall == "top":
                        g = g + fr.move(X0 + s0, Y0 - .02, HP)
                    else:
                        g = g + fr.rot("z", -90).move(X0 - .02, Y0 + s0 + .7, HP)
        elif k == "pinboard" and ext:
            g = g + q(A, Bq, 1.7, 3.5, "#c9a066")
            for i, (s, z, c) in enumerate([(.15, 2.6, P["mus"]), (.5, 2.1, P["pink"]), (.85, 2.8, P["cream"]), (.3, 1.9, P["cream"]), (.7, 2.35, P["mus"])]):
                s0 = A + s * (Bq - A)
                g = g + q(s0, s0 + .5, z, z + .45, c, off=.04)
        elif k == "movies" and ext:     # framed film posters, one bold shape each
            n = max(1, int((Bq - A + .1) / 1.6))
            for i in range(n):
                s0 = A + .1 + i * (Bq - A - .2) / n
                s1 = s0 + (Bq - A - .2) / n - .25
                bgc, sh1, sh2 = [("#1d2b44", P["mus"], "#e8e2d6"), ("#c8442b", "#151517", P["cream"]), ("#e6d9b8", P["cob"], P["red"])][i % 3]
                g = g + q(s0, s1, 1.75, 3.75, "#151517", off=.03) + q(s0 + .08, s1 - .08, 1.83, 3.67, bgc, off=.04)
                mid_ = (s0 + s1) / 2
                g = g + q(mid_ - .3, mid_ + .3, 2.5, 3.3, sh1, off=.05) + q(s0 + .2, s1 - .2, 2.0, 2.12, sh2, off=.05) + q(s0 + .2, s1 - .5, 2.2, 2.28, sh2, off=.05)
        elif k in ("gallery", "poster") and ext:      # Bauhaus / mid-century prints
            def wdisc(sc_, zc, r, col, off=.05, ry=None):
                d_ = disc(0, 0, 0, r, col, 18, ry=ry)
                if wall == "top":
                    return d_.rot("x", 90).move(X0 + sc_, Y0 + off, zc)
                return d_.rot("y", 90).move(X0 + off, Y0 + sc_, zc)
            def frame(s0, s1, z0, z1, fc="#2a201a", mat="#f4efe6"):
                return q(s0, s1, z0, z1, fc, off=.03) + q(s0 + .05, s1 - .05, z0 + .05, z1 - .05, mat, off=.035)
            prints = []
            L = Bq - A
            if k == "poster":
                prints = [("circle", A + .1, Bq - .1, 1.8, 3.8)]
            else:
                prints = [("type", A + .05 * L, A + .25 * L, 2.35, 3.55), ("dots", A + .05 * L, A + .25 * L, 1.95, 2.25),
                          ("half", A + .31 * L, A + .47 * L, 2.75, 3.75), ("green", A + .52 * L, A + .72 * L, 2.1, 3.95),
                          ("albers", A + .77 * L, A + .95 * L, 3.05, 3.85), ("star", A + .77 * L, A + .97 * L, 2.05, 2.85)]
            for (kind_, s0, s1, z0, z1) in prints:
                cs, cz, ww, hh = (s0 + s1) / 2, (z0 + z1) / 2, s1 - s0, z1 - z0
                if kind_ == "circle":      # Bauhaus exhibition poster: cream, stripes, red circle, black bar
                    g = g + frame(s0, s1, z0, z1)
                    for i in range(7):
                        x_ = s0 + .2 + i * (ww - .4) / 7
                        g = g + q(x_, x_ + .04, z0 + .5, z1 - .45, "#2a2a2a", off=.04)
                    g = g + wdisc(cs, cz + .05, min(ww, hh) * .27, "#d6492c") + q(s0 + .2, s1 - .2, z1 - .35, z1 - .25, "#1b1a17", off=.045)
                elif kind_ == "type":      # black print with white loops
                    g = g + q(s0, s1, z0, z1, "#f4efe6", off=.03) + q(s0 + .04, s1 - .04, z0 + .04, z1 - .04, "#1b1a17", off=.035)
                    g = g + wdisc(cs - ww * .15, cz + hh * .2, ww * .22, "#f4efe6", ry=hh * .16) + wdisc(cs + ww * .12, cz - hh * .18, ww * .24, "#f4efe6", ry=hh * .18)
                    g = g + wdisc(cs - ww * .15, cz + hh * .2, ww * .1, "#1b1a17", .055, ry=hh * .07) + wdisc(cs + ww * .12, cz - hh * .18, ww * .11, "#1b1a17", .055, ry=hh * .08)
                elif kind_ == "dots":      # blue panel with a grid of dots
                    g = g + q(s0, s1, z0, z1, "#2f5bc4", off=.035)
                    for i in range(3):
                        g = g + wdisc(s0 + ww * (i + .5) / 3, cz, min(ww / 7, hh / 3), "#4a77dc")
                elif kind_ == "half":      # cream print, half-black circle
                    g = g + frame(s0, s1, z0, z1, "#c9b48e")
                    g = g + wdisc(cs, cz, ww * .3, "#1b1a17") + q(cs, cs + ww * .32, cz - ww * .32, cz + ww * .32, "#f4efe6", off=.055)
                elif kind_ == "green":     # tall green colour-block print
                    g = g + frame(s0, s1, z0, z1, "#e9e4da", "#f4f1ea")
                    g = g + q(s0 + .1, s1 - .1, z0 + .35, z1 - .2, "#3f8a4a", off=.04) + q(s0 + .1, cs - .05, z0 + .35, cz, "#1f5a2e", off=.045)
                    g = g + q(cs + .05, s1 - .1, cz + .25, cz + .45, "#d8e6a0", off=.045) + q(s0 + .2, cs, z1 - .55, z1 - .4, "#f4efe6", off=.045)
                elif kind_ == "albers":    # nested squares
                    g = g + frame(s0, s1, z0, z1, "#e9e4da", "#f4f1ea")
                    for i, c in enumerate(["#2f5bc4", "#5577d6", "#e0a72e"]):
                        d_ = .1 + i * ww * .12
                        g = g + q(s0 + d_, s1 - d_, z0 + d_ - .02, z1 - d_ - .02, c, off=.04 + i * .005)
                elif kind_ == "star":      # blue print, yellow half sun
                    g = g + frame(s0, s1, z0, z1, "#e9e4da", "#2f5bc4")
                    g = g + wdisc(s0 + ww * .35, z0 + .05, ww * .3, "#f0c33c") + q(s0 + .05, s1 - .05, z0, z0 + .05, "#2f5bc4", off=.06)
                    g = g + q(s0 + .1, s1 - .1, z1 - .25, z1 - .15, "#f0c33c", off=.045)
        elif k == "poster_old" and ext:
            g = g + q(A, Bq, 1.8, 3.8, P["cream"]) + q(A + .2, A + .9, 3.2, 3.5, P["cob"], off=.04) + q(A + .2, Bq - .3, 2.5, 2.65, P["red"], off=.04) + q(Bq - .9, Bq - .3, 2.0, 2.9, P["mus"], off=.04)
    return g


# ------------------------------------------------------------ walls as specs, joined cleanly at corners
def wspec(walls, axis, x, y, z, w, d, h, col, top=None, join=True):
    """collect an axis-aligned wall piece (units). axis = the direction it runs along ('x' or 'y')."""
    walls.append(dict(axis=axis, x0=x, x1=x + w, y0=y, y1=y + d, z0=z, z1=z + h, col=col, top=top or col, join=join))


def join_walls(walls, eps=.03, keep_lone=False):
    """Extend every wall end that stops against a perpendicular piece of the same material so the
    two meet in a clean corner (fills convex corners, closes L and T joints). Free ends are left alone,
    so nothing pokes out past a corner.
    keep_lone: keep full-height walls that touch nothing. In a house sunk into the page (slot stair)
    such a wall is a side of the cut, e.g. P2's workout-deck notch, and the page hides its ends."""
    out = []
    for p in walls:
        q = dict(p)
        if p["join"]:
            lo, hi = ("x0", "x1") if p["axis"] == "x" else ("y0", "y1")
            blo, bhi = ("y0", "y1") if p["axis"] == "x" else ("x0", "x1")
            for o in walls:
                if o is p or not o["join"] or o["axis"] == p["axis"] or o["col"] != p["col"] or o["top"] != p["top"]:
                    continue
                if abs(o["z0"] - p["z0"]) > eps or abs(o["z1"] - p["z1"]) > eps:    # only same-height pieces join
                    continue
                if o[blo] > p[bhi] + eps or o[bhi] < p[blo] - eps:        # o must touch p's band across its width
                    continue
                if abs(o[lo] - p[hi]) < eps or (o[lo] < p[hi] - eps < o[hi] and o[hi] > p[hi] + eps and o[lo] > p[lo] + eps):
                    q[hi] = max(q[hi], o[hi])                           # o sits just past p's far end
                if abs(o[hi] - p[lo]) < eps or (o[lo] < p[lo] + eps < o[hi] and o[lo] < p[lo] - eps and o[hi] < p[hi] - eps):
                    q[lo] = min(q[lo], o[lo])                           # o sits just before p's near end
        out.append(q)
    # a full-height retaining wall touching nothing at either end is a lone fin left by the cutaway
    # (its partner walls are on the cut-away front side): leave it out
    def touches(a, b):
        return not (a["x0"] > b["x1"] + eps or b["x0"] > a["x1"] + eps or a["y0"] > b["y1"] + eps or b["y0"] > a["y1"] + eps)
    keep = []
    for q in out:
        if not keep_lone and q["z1"] >= H - eps and q["z0"] <= eps and q["join"] and not any(o is not q and o["z1"] >= H - eps and touches(q, o) for o in out):
            continue
        keep.append(q)
    g = Part()
    for q in keep:
        g = g + box(q["x0"], q["y0"], q["z0"], q["x1"] - q["x0"], q["y1"] - q["y0"], q["z1"] - q["z0"], q["col"], q["top"])
    return g


def internal_specs(walls, ax, k, a, b, kind, gaps, col):
    """same partitions as layouts.internal (low wall / glass with sill, posts and header), as wall specs"""
    gaps = [gp for gp in gaps if gp[1] > a and gp[0] < b]
    segs, cur = [], a
    for g0, g1 in sorted(gaps):
        segs.append((cur, max(cur, g0))); cur = min(b, g1)
    segs.append((cur, b))

    def piece(s0, s1, c0, c1, z0, z1, c, top=None, join=True):
        if ax == "x":     # wall on the line x = k, running along y
            wspec(walls, "y", c0, s0, z0, c1 - c0, s1 - s0, z1 - z0, c, top, join)
        else:
            wspec(walls, "x", s0, c0, z0, s1 - s0, c1 - c0, z1 - z0, c, top, join)
    if kind == "low":
        for s0, s1 in segs:
            if s1 > s0:
                piece(s0, s1, k - T / 2, k + T / 2, 0, HP, col, P["top"])
    elif kind == "glass":
        fr = "#ead9bf"
        for s0, s1 in segs:
            if s1 <= s0:
                continue
            piece(s0, s1, k - T / 2, k + T / 2, 0, .6, col, P["top"])
            n = max(1, int(round((s1 - s0) / 3.2)))
            for i in range(1, n):                 # inner posts only; the ends meet walls or the next frame
                p_ = s0 + (s1 - s0) * i / n
                piece(p_ - .05, p_ + .05, k - .05, k + .05, .6, H - .14, fr, join=False)
            for p_ in (s0, s1):                   # jamb posts at door openings
                if any(abs(p_ - g0) < 1e-6 or abs(p_ - g1) < 1e-6 for g0, g1 in gaps):
                    piece(p_ - .05 if p_ == s1 else p_, p_ if p_ == s1 else p_ + .05, k - .05, k + .05, .6, H - .14, fr, join=False)
        piece(a, b, k - .07, k + .07, H - .14, H, fr)


# ------------------------------------------------------------ shell: floors, walls, bank, stairs, path
def hero_rects(key):
    plan = PLANS[key]
    rects = []
    for rk, label, kind, rs in plan["rooms"]:
        if rk == "apron":
            continue
        for (x, y, w, d) in rs:
            rects.append(dict(key=rk, kind=kind, r=(x, y, w, d)))
    if "stair" in plan:
        for r in stair_rects(plan):
            rects.append(dict(key="slot", kind="stair", r=r))
        return rects, []
    # bank strip in front of every exposed front edge (rooms, gardens, decks)
    def inside(px, py):
        return any(q["r"][0] < px < q["r"][0] + q["r"][2] and q["r"][1] < py < q["r"][1] + q["r"][3] for q in rects)
    bank = []
    for q in list(rects):
        x, y, w, d = q["r"]
        for ax in ("x", "y"):
            n = int(round((d if ax == "x" else w) / .25))
            run = None
            for i in range(n + 1):
                free = i < n and not (inside(x + w + .05, y + i * .25 + .125) if ax == "x" else inside(x + i * .25 + .125, y + d + .05))
                if free and run is None:
                    run = i
                if not free and run is not None:
                    a, b = run * .25, i * .25
                    bank.append((x + w, y + a, B, b - a) if ax == "x" else (x + a, y + d, b - a, B))
                    run = None
        if not inside(x + w + .05, y + d + .05):
            bank.append((x + w, y + d, B, B))
    return rects, bank


def build_shell(key):
    plan = PLANS[key]
    rects, bank = hero_rects(key)
    doors = list(plan["doors"])
    ent = HERO_ENTRY[key]
    if "door" in ent:
        doors.append(ent["door"])
    flat = [q["r"] for q in rects]

    def who(px, py):
        for q in rects:
            x, y, w, d = q["r"]
            if x < px < x + w and y < py < y + d:
                return q
        for (x, y, w, d) in bank:
            if x < px < x + w and y < py < y + d:
                return dict(key="bank", kind="bank", r=(x, y, w, d))
        return None
    g = Part()
    # floors
    for q in rects:
        x, y, w, d = (m(v) for v in q["r"])
        if q["kind"] == "stair":
            continue
        if q["kind"] == "garden":
            g = g + poly([(x, y, 0), (x + w, y, 0), (x + w, y + d, 0), (x, y + d, 0)], GRASS)
            continue
        f = FLOOR[q["kind"]]
        g = g + poly([(x, y, 0), (x + w, y, 0), (x + w, y + d, 0), (x, y + d, 0)], f[0])
        if len(f) > 1:
            g = g + planks(x, y, x + w, y + d, f[1], alongx=len(f) > 2, step=.9 if len(f) > 2 else 1.1)
    # walls on back edges (collected as specs, joined at the end)
    walls = []
    for q in rects:
        if q["kind"] == "stair":
            continue
        x0, y0, w, d = (m(v) for v in q["r"])
        for ax, k, a0, a1 in (("x", x0, y0, y0 + d), ("y", y0, x0, x0 + w)):
            n = max(1, int(round((a1 - a0) / m(.25))))     # 25 cm cells: every room edge sits on a cell boundary
            st = (a1 - a0) / n
            labs = [(who((k - .2) / M2U, (a0 + (i + .5) * st) / M2U) if ax == "x" else who((a0 + (i + .5) * st) / M2U, (k - .2) / M2U)) for i in range(n)]
            i = 0
            while i < n:
                j = i
                while j < n and (labs[j] or {}).get("key") == (labs[i] or {}).get("key"):
                    j += 1
                a, b, nb = a0 + i * st, a0 + j * st, labs[i]
                i = j
                if nb is not None and nb["key"] == q["key"]:
                    continue
                if nb is None:
                    ea, eb = a, b      # end exactly at the corner: no stub poking into the next room
                    col, top = P["wall"], P["top"]      # garden retaining walls match the house walls
                    if ax == "x":
                        wspec(walls, "y", k - T, ea, 0, T, eb - ea, H, col, top)
                    else:
                        wspec(walls, "x", ea, k - T, 0, eb - ea, T, H, col, top)
                    continue
                if nb["kind"] == "stair":
                    continue
                if q["kind"] == "garden" and nb["kind"] == "garden":      # low hedge between two gardens
                    if ax == "x":
                        wspec(walls, "y", k - .3, a, 0, .6, b - a, 1.0, "#5a8a3a", "#6d9a48")
                    else:
                        wspec(walls, "x", a, k - .3, 0, b - a, .6, 1.0, "#5a8a3a", "#6d9a48")
                    continue
                if (q["kind"] in OPEN and nb["kind"] in OPEN) or nb["kind"] == "bank":
                    continue
                gaps = []
                for (dx, dy, dax, dw) in doors:
                    if ax == "x":
                        on, c = dax == "y" and abs(m(dx) - k) < .3, m(dy)
                    else:
                        on, c = dax == "x" and abs(m(dy) - k) < .3, m(dx)
                    if on and a - .1 <= c <= b + .1:
                        gaps.append((c - m(dw) / 2, c + m(dw) / 2))
                kind = "glass" if (q["kind"] in OPEN or nb["kind"] in OPEN) else "low"
                internal_specs(walls, ax, k, a, b, kind, gaps, P["wall"])
    if "stair" in plan:
        g2, extra = slot_entry(plan, walls)
        return g + g2 + join_walls(walls, keep_lone=True), rects, [], ("slot", extra), None, None
    g = g + join_walls(walls)
    # bank: heightfield over the bank strips, rising from the house to the page
    sx = ent["x"]
    ytop = max(y + d for (x, y, w, d) in bank + flat if x <= sx <= x + w)
    L = 1.8
    stair = (sx - .6, ytop - L, sx + .6, ytop)

    def dist_flat(px, py):
        best = 9
        for (x, y, w, d) in flat:
            dx = max(x - px, 0, px - (x + w)); dy = max(y - py, 0, py - (y + d))
            best = min(best, math.hypot(dx, dy))
        return best

    def zb(px, py):
        return H * min(1.0, dist_flat(px, py) / B)
    res = .25
    for (x, y, w, d) in bank:
        nx, ny = max(1, int(round(w / res))), max(1, int(round(d / res)))
        for i in range(nx):
            for j in range(ny):
                ax0, ay0 = x + i * w / nx, y + j * d / ny
                ax1, ay1 = ax0 + w / nx, ay0 + d / ny
                cxm, cym = (ax0 + ax1) / 2, (ay0 + ay1) / 2
                if stair[0] < cxm < stair[2] and stair[1] < cym < stair[3]:
                    continue
                pts = [(ax0, ay0), (ax1, ay0), (ax1, ay1), (ax0, ay1)]
                v = [(m(px), m(py), zb(px, py)) for (px, py) in pts]
                col = GRASS if (i + j) % 2 else GRASS2
                g = g + poly([v[0], v[1], v[2]], col) + poly([v[0], v[2], v[3]], col)
        # cut faces where a bank strip ends against open ground at its back
        for ax, k, a0, a1 in (("x", x, y, y + d), ("y", y, x, x + w)):
            n = max(1, int(round((a1 - a0) / res)))
            for i in range(n):
                s0, s1 = a0 + i * (a1 - a0) / n, a0 + (i + 1) * (a1 - a0) / n
                pm = ((k - .05, (s0 + s1) / 2) if ax == "x" else ((s0 + s1) / 2, k - .05))
                if who(*pm) is not None:
                    continue
                p0 = (k, s0) if ax == "x" else (s0, k); p1 = (k, s1) if ax == "x" else (s1, k)
                g = g + poly([(m(p0[0]), m(p0[1]), zb(*p0)), (m(p1[0]), m(p1[1]), zb(*p1)), (m(p1[0]), m(p1[1]), H), (m(p0[0]), m(p0[1]), H)], EARTH)
    # stairs: 6 risers' worth of blocks from the page down to the garden, with stone cheeks
    nst = 7
    for kk in range(nst - 1):
        y1 = ytop - kk * L / (nst - 1); y0 = y1 - L / (nst - 1)
        z = H * (nst - 1 - kk) / nst
        g = g + box(m(stair[0]), m(y0), 0, m(1.2), m(y1 - y0), z, STONE, STONE_T)
    for xs in (stair[0], stair[2]):
        n = 12
        for i in range(n):
            s0, s1 = stair[1] + i * L / n, stair[1] + (i + 1) * L / n
            z0, z1 = zb(xs, s0), zb(xs, s1)
            if max(z0, z1) < .05:
                continue
            g = g + poly([(m(xs), m(s0), 0), (m(xs), m(s1), 0), (m(xs), m(s1), z1), (m(xs), m(s0), z0)], STONE)
    # surface path, lamp and mailbox on the page
    zp = H + .02
    pathL = 3.4
    yy, k = ytop + .12, 0
    while yy < ytop + pathL:
        off = .08 if k % 2 else -.08
        g = g + box(m(sx - .5 + off), m(yy), H, m(1.0), m(.42), .08, "#e8e0cf", "#efe8da")
        yy += .55; k += 1
    g = g + box(m(stair[0] - .15), m(ytop - .05), H, m(1.5), m(.25), .1, STONE, STONE_T)       # top step lip
    lx, ly = m(sx + 1.0), m(ytop + .5)
    g = g + box(lx - .07, ly - .07, H, .14, .14, 2.4, "#2b2b2e") + ico((lx, ly, H + 2.55), .28, "#ffe7b0", 1, emis=True) + cyl(lx, ly, H + 2.75, .3, .08, "#2b2b2e", n=8)
    mx, my = m(sx - 1.05), m(ytop + 1.3)
    g = g + box(mx - .06, my - .06, H, .12, .12, 1.5, P["walD"]) + box(mx - .32, my - .22, H + 1.5, .64, .44, .42, P["red"], "#d9573a")
    g = g + shrub(m(sx + 1.2), m(ytop + 2.3), .5).move(0, 0, H) + shrub(m(sx - 1.2), m(ytop + .45), .42).move(0, 0, H)
    # garden walk from the stairs to the door
    cands = [dd for dd in doors if dd[2] == "x" and abs(dd[0] - sx) < .2 and dd[1] < stair[1]]
    door_y = (ent.get("door") or max(cands, key=lambda dd: dd[1]))[1]
    yy = stair[1] - .25
    while yy > door_y + .35:
        g = g + cyl(m(sx), m(yy), 0, m(.28), .05, "#e8e0cf", n=8)
        yy -= .6
    return g, rects, bank, stair, ytop, pathL


def stair_rects(plan):
    st = plan["stair"]
    if isinstance(st, dict):
        return list(st["rects"])
    sx0, sy0, sx1, sy1, _ = st
    return [(sx0, sy0, sx1 - sx0, sy1 - sy0)]


def slot_entry(plan, walls=None):
    """L-shaped stair cut down into the page: flight A runs west out of the entry court, a square landing,
    flight B turns toward the top-right and comes out on the page. Every piece is one 1.5 m grid cell."""
    A, Ld, Bf = plan["stair"]["rects"]
    n = 8
    rise = H / n
    g = Part()
    for (x, y, w, d) in (A, Ld, Bf):
        g = g + poly([(m(x), m(y), .01), (m(x + w), m(y), .01), (m(x + w), m(y + d), .01), (m(x), m(y + d), .01)], STONE)
    ax0, ay0, aw, ad = A
    t = aw / 3
    for i in range(1, 4):                       # flight A: three steps west, rising
        x1 = ax0 + aw - (i - 1) * t
        g = g + box(m(x1 - t), m(ay0), 0, m(t), m(ad), i * rise, STONE, STONE_T)
    lx, ly, lw, ld = Ld
    g = g + box(m(lx), m(ly), 0, m(lw), m(ld), 4 * rise, STONE, STONE_T)      # landing
    bx0, by0, bw, bd = Bf
    t = bd / 4
    for i in range(1, 4):                       # flight B: three steps toward the top-right, last rise onto the page
        y1 = by0 + bd - (i - 1) * t
        g = g + box(m(bx0), m(y1 - t), 0, m(bw), m(t), (4 + i) * rise, STONE, STONE_T)
    g = g + box(m(bx0), m(by0), 0, m(bw), m(t), 7.5 * rise, STONE, STONE_T)
    # retaining walls around the cut, except the court mouth and the top exit
    R = [A, Ld, Bf]

    def slot_at(px, py):
        return any(x < px < x + w and y < py < y + d for (x, y, w, d) in R)
    for (x, y, w, d) in R:
        for side in ("w", "e", "n", "s"):
            if side == "e" and (x, y, w, d) == A:
                continue                         # opens onto the entry court
            if side == "n" and (x, y, w, d) == Bf:
                continue                         # comes out on the page
            if side in ("w", "e"):
                X = x if side == "w" else x + w
                if slot_at(X + (-.05 if side == "w" else .05), y + d / 2):
                    continue
                wspec(walls, "y", m(X) - (T if side == "w" else 0), m(y), 0, T, m(d), H, P["wall"], P["top"])
            else:
                Y = y if side == "n" else y + d
                if slot_at(x + w / 2, Y + (-.05 if side == "n" else .05)):
                    continue
                wspec(walls, "x", m(x), m(Y) - (T if side == "n" else 0), 0, m(w), T, H, P["wall"], P["top"])
    # warm step lights on the two back walls
    g = g + poly([(m(ax0 + aw / 2) - .2, m(ay0) + .02, 2 * rise + .45), (m(ax0 + aw / 2) + .2, m(ay0) + .02, 2 * rise + .45),
                  (m(ax0 + aw / 2) + .2, m(ay0) + .02, 2 * rise + .59), (m(ax0 + aw / 2) - .2, m(ay0) + .02, 2 * rise + .59)], "#ffe7b0", True)
    g = g + poly([(m(bx0) + .02, m(by0 + bd / 2) - .2, 6 * rise + .45), (m(bx0) + .02, m(by0 + bd / 2) + .2, 6 * rise + .45),
                  (m(bx0) + .02, m(by0 + bd / 2) + .2, 6 * rise + .59), (m(bx0) + .02, m(by0 + bd / 2) - .2, 6 * rise + .59)], "#ffe7b0", True)
    return g, []


def masks(rects, bank, stair, ytop, pathL, key):
    out = []
    for (x, y, w, d) in [q["r"] for q in rects] + bank:
        out.append([(m(x), m(y), H), (m(x + w), m(y), H), (m(x + w), m(y + d), H), (m(x), m(y + d), H)])
    if isinstance(stair, tuple) and stair[0] == "slot":
        out += stair[1]
        return out
    return out_old(out, rects, bank, stair, ytop, pathL, key)


def tree_layer(key):
    """tree crowns that rise above the page, as a separate layer with its own mask"""
    items, _ = furnish(key)
    trees, out = Part(), []
    if True:
        for (x, y, w, d, k, lab, sh) in items:
            if k != "tree":
                continue
            trees = trees + tree(m(x + w / 2), m(y + d / 2), m(w) / 3.0)
            s_ = m(w) / 3.0
            cx, cy, r, top = m(x + w / 2), m(y + d / 2), 2.2 * s_, 5.3 * s_
            if top <= H:
                continue
            for zz in (H, top):
                out.append([(cx - r, cy - r, zz), (cx + r, cy - r, zz), (cx + r, cy + r, zz), (cx - r, cy + r, zz)])
            out += [[(cx - r, cy - r, H), (cx + r, cy - r, H), (cx + r, cy - r, top), (cx - r, cy - r, top)],
                    [(cx - r, cy - r, H), (cx - r, cy + r, H), (cx - r, cy + r, top), (cx - r, cy - r, top)],
                    [(cx + r, cy - r, H), (cx + r, cy + r, H), (cx + r, cy + r, top), (cx + r, cy - r, top)],
                    [(cx - r, cy + r, H), (cx + r, cy + r, H), (cx + r, cy + r, top), (cx - r, cy + r, top)]]
    return trees, out


def out_old(out, rects, bank, stair, ytop, pathL, key):
    sx = HERO_ENTRY[key]["x"]
    x0, x1, y0, y1 = m(sx - 1.8), m(sx + 1.8), m(ytop - .2), m(ytop + pathL + .3)
    for zz in (H, H + 3.2):
        out.append([(x0, y0, zz), (x1, y0, zz), (x1, y1, zz), (x0, y1, zz)])
    out.append([(x0, y0, H), (x1, y0, H), (x1, y0, H + 3.2), (x0, y0, H + 3.2)])
    out.append([(x0, y1, H), (x1, y1, H), (x1, y1, H + 3.2), (x0, y1, H + 3.2)])
    out.append([(x0, y0, H), (x0, y1, H), (x0, y1, H + 3.2), (x0, y0, H + 3.2)])
    out.append([(x1, y0, H), (x1, y1, H), (x1, y1, H + 3.2), (x1, y0, H + 3.2)])
    # trees can rise above the page
    for q in rects:
        if q["kind"] == "garden":
            x, y, w, d = (m(v) for v in q["r"])
            for zz in (0, H * 2):
                out.append([(x, y, zz), (x + w, y, zz), (x + w, y + d, zz), (x, y + d, zz)])
            out.append([(x, y, 0), (x + w, y, 0), (x + w, y, H * 2), (x, y, H * 2)])
            out.append([(x, y, 0), (x, y + d, 0), (x, y + d, H * 2), (x, y, H * 2)])
    return out


def person(key):
    plan = PLANS[key]
    r = next(rr for rr in plan["rooms"] if rr[0] == "living")
    x, y, w, d = max(r[3], key=lambda q: q[2] * q[3])
    items, _ = furnish(key)
    # a free spot in the living room, front half, away from furniture
    best = None
    for fx in np.linspace(.25, .75, 11):
        for fy in np.linspace(.3, .7, 9):
            px, py = x + w * fx, y + d * fy
            clear = min([max(abs(px - (ix + iw / 2)) - iw / 2, abs(py - (iy + idd / 2)) - idd / 2) for (ix, iy, iw, idd, k, _, _) in items if k != "rug"] + [9])
            score = clear - .15 * abs(fx - .45)
            if best is None or score > best[0]:
                best = (score, px, py)
    return character("wave", -45, (m(best[1]), m(best[2]), .04))


def build(key):
    shell, rects, bank, stair, ytop, pathL = build_shell(key)
    furn, decos = furniture3d(key)
    g = shell + furn + decos3d(key, decos) + person(key)
    return g, masks(rects, bank, stair, ytop, pathL, key)


def framing(key, W=1720, Hh=1320, pad=30):
    g, mk = build(key)
    trees, tmk = tree_layer(key) if "stair" in PLANS[key] else (Part(), [])
    cam = Cam(45, 30)
    q = cam.proj(np.array([p for pl in mk + tmk for p in pl], float))
    x0, x1, y0, y1 = q[:, 0].min(), q[:, 0].max(), q[:, 1].min(), q[:, 1].max()
    sc = min((W - 2 * pad) / (x1 - x0), (Hh - 2 * pad) / (y1 - y0))
    c = (x0 + x1) / 2 * cam.r + (y0 + y1) / 2 * cam.dn
    return g, mk, trees, tmk, cam, sc, c


def render_hero(key, W=1720, Hh=1320, ss=2, pad=30):
    from PIL import Image
    g, mk, trees, tmk, cam, sc, c = framing(key, W, Hh, pad)
    im, _ = render(g, cam, W, Hh, sc, c, ss=ss, mask_poly=mk)
    if tmk:   # tree crowns above the page drawn as their own layer, under the house where they overlap
        tl, _ = render(trees, cam, W, Hh, sc, c, ss=ss, mask_poly=tmk, shadow=False)
        im = Image.alpha_composite(tl, im)
    return im


if __name__ == "__main__":
    import sys, os
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    keys = sys.argv[2].split(",")
    W, Hh, ss = (int(v) for v in sys.argv[3:6]) if len(sys.argv) > 5 else (1720, 1320, 2)
    for k in keys:
        im = render_hero(k, W, Hh, ss)
        a = np.array(im)[..., 3]; ys, xs = np.nonzero(a > 8)
        im.crop((xs.min() - 8, ys.min() - 8, xs.max() + 8, ys.max() + 8)).save(f"{out}/hero_{k}.png")
        print(k, flush=True)


def visibility(key, ppu=6):
    """share of each room's floor the sunken hero shows (walls and rim, no furniture)."""
    from engine import raster
    from PIL import Image, ImageDraw
    shell, rects, bank, stair, ytop, pathL = build_shell(key)
    mk = masks(rects, bank, stair, ytop, pathL, key)
    plan = PLANS[key]
    floor, ids = Part(), []
    keys = []
    for r in plan["rooms"]:
        if r[0] == "apron":
            continue
        for (x, y, w, d) in r[3]:
            X, Y, W, D = m(x), m(y), m(w), m(d)
            floor = floor + poly([(X, Y, .03), (X + W, Y, .03), (X + W, Y + D, .03), (X, Y + D, .03)], "#000000")
            ids += [len(keys)] * 2; keys.append((r[0], w * d))
    allp = shell + floor
    tag = np.full(len(allp.t), -1); tag[len(shell.t):] = ids
    cam = Cam(45, 30)
    P3 = cam.proj(allp.t.reshape(-1, 3)).reshape(-1, 3, 3)
    mn = P3[..., :2].reshape(-1, 2).min(0) - 1
    xy = (P3[..., :2] - mn) * ppu
    Wd, Hd = int(xy[..., 0].max()) + 3, int(xy[..., 1].max()) + 3
    zb_, ib = raster(xy, P3[..., 2], Wd, Hd)
    mask = Image.new("L", (Wd, Hd), 0); md = ImageDraw.Draw(mask)
    for pl in mk:
        mp = cam.proj(np.asarray(pl, float)); md.polygon([tuple(((p[:2] - mn) * ppu).tolist()) for p in mp], fill=255)
    vis = (np.array(mask) > 0) & (ib >= 0)
    hit = tag[ib[vis]]
    out = {}
    for i, (k, a) in enumerate(keys):
        exp = m(1) ** 2 * a * .5 * ppu * ppu
        out.setdefault(k, [0, 0]); out[k][0] += (hit == i).sum(); out[k][1] += exp
    return {k: v[0] / v[1] for k, v in out.items()}
