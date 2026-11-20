"""Abraham as a low-poly character: relaxed black tee, one-wash indigo relaxed straight denim (after his
Sugar Cane 1937 model: slightly wide straight leg, single cuff showing the selvedge), barefoot, light skin,
straight middle-parted hair, rounded Lemtosh-style frames. Built facing +y, x = his right."""
import math
import numpy as np
from engine import Part, hull, cham, cbox, cyl, ico, box, rod, poly

SKIN, SKIN_D = "#f7d4ae", "#e6b98f"
DENIM, DENIM_L = "#26385e", "#3a5486"
SELV_W, SELV_R = "#eae4d6", "#c8442b"
TEE, TEE_D = "#2a2a2e", "#1f1f22"
HAIR, HAIR_L = "#2a1f19", "#33261e"
FRAME = "#141414"
INK, MOUTH, WHITE = "#1b1a17", "#6a2c24", "#ffffff"


def hulls(*groups):
    pts = []
    for g in groups:
        pts += g
    return pts


def leg(sd, hip=0.0, knee=0.0):
    x = sd * .25
    # relaxed straight: roomy thigh, no taper from knee to hem
    up = hull(hulls(cham(x, 0, 1.42, .215, .245, .09, .05), cham(x, .01, .86, .2, .225, .07, .04)), DENIM)
    lo = hull(hulls(cham(x, .01, .86, .2, .225, .07, .04), cham(x, .01, .32, .2, .225, .06, .03)), DENIM)
    lo = lo + cbox(x, .01, .25, .222, .247, .095, .03, DENIM_L)           # single wide cuff
    xo = x + sd * .224                                                    # selvedge: white line with a red stitch on the outseam
    lo = lo + poly([(xo, -.04, .16), (xo, .04, .16), (xo, .04, .34), (xo, -.04, .34)], SELV_W)
    lo = lo + poly([(xo + sd * .002, -.012, .16), (xo + sd * .002, .012, .16), (xo + sd * .002, .012, .34), (xo + sd * .002, -.012, .34)], SELV_R)
    lo = lo + hull(hulls(cham(x, .1, .075, .12, .25, .075, .035), cham(x, .3, .05, .1, .06, .05, .02)), SKIN)  # bare foot
    lo = lo.rot("x", knee, (x, 0, .86))
    return (up + lo).rot("x", hip, (x, 0, 1.42))


def arm(sd, swing=0.0, abd=0.0, elbow=0.0, twist=0.0):
    x = sd * .66
    sl = hull(hulls(cham(sd * .62, 0, 2.3, .2, .2, .08, .05), cham(sd * .7, 0, 1.86, .185, .185, .05, .04)), TEE)   # dropped shoulder, longer sleeve
    up = hull(hulls(cham(sd * .68, 0, 2.0, .115, .115, .04, .03), cham(sd * .68, 0, 1.8, .105, .105, .04, .03)), SKIN)
    lo = hull(hulls(cham(sd * .68, 0, 1.8, .105, .105, .04, .03), cham(sd * .68, 0, 1.46, .095, .095, .04, .03)), SKIN)
    lo = lo + ico((sd * .68, .015, 1.33), .135, SKIN, 1, (.8, 1, 1.15))
    lo = lo.rot("x", elbow, (sd * .68, 0, 1.8))
    a = up + lo
    if twist:
        a = a.rot("z", twist, (sd * .68, 0, 2.0))
    a = sl + a
    piv = (sd * .62, 0, 2.34)
    a = a.rot("y", -sd * abd, piv)
    return a.rot("x", swing, piv)


def head(tilt=0.0, turn=0.0, smile=True):
    h = cbox(0, 0, 3.2, .56, .5, .58, .17, SKIN)
    fy = .502
    for sd in (-1, 1):
        h = h + cbox(sd * .6, -.03, 3.12, .06, .11, .14, .03, SKIN_D)                       # ears
        h = h + box(sd * .19 - .045, fy - .015, 3.11, .09, .03, .13, INK)                     # eyes
        h = h + box(sd * .19 - .005 + sd * .012, fy + .012, 3.2, .028, .01, .03, WHITE)       # catch-light
        b = box(sd * .19 - .11, fy - .01, 3.385, .22, .03, .05, HAIR)                          # brows
        h = h + b.rot("y", sd * 7, (sd * .19, fy, 3.41))
    # nose + smile
    h = h + hull([(-.05, fy, 3.1), (.05, fy, 3.1), (-.06, fy, 2.98), (.06, fy, 2.98), (0, fy + .07, 3.0), (0, fy + .02, 3.1)], SKIN_D)
    if smile:
        h = h + poly([(-.11, fy + .01, 2.9), (.11, fy + .01, 2.9), (.07, fy + .01, 2.845), (0, fy + .01, 2.83), (-.07, fy + .01, 2.845)], MOUTH)
    else:
        h = h + box(-.08, fy - .01, 2.86, .16, .03, .03, MOUTH)
    # chunky rounded-square frames
    def ring(cxx, cz, hw, hh, r, t, ttop, y0, y1):
        def rr(w, hgt, rad, top_off=0.0):
            pts = []
            for (ox, oz, a0) in [(w - rad, hgt - rad, 0), (-(w - rad), hgt - rad, 90), (-(w - rad), -(hgt - rad), 180), (w - rad, -(hgt - rad), 270)]:
                for k in range(7):
                    a = math.radians(a0 + k * 15)
                    pts.append((cxx + ox + rad * math.cos(a), cz + oz + rad * math.sin(a)))
            return pts
        o = rr(hw, hh, r)
        inn = rr(hw - t, hh - (t + ttop) / 2, max(r - t, .02))
        inn = [(a, b - (ttop - t) / 2) for a, b in inn]
        out = Part()
        n = len(o)
        for i in range(n):
            j = (i + 1) % n
            for yy in (y0, y1):
                out = out + poly([(o[i][0], yy, o[i][1]), (o[j][0], yy, o[j][1]), (inn[j][0], yy, inn[j][1]), (inn[i][0], yy, inn[i][1])], FRAME)
            out = out + poly([(o[i][0], y0, o[i][1]), (o[j][0], y0, o[j][1]), (o[j][0], y1, o[j][1]), (o[i][0], y1, o[i][1])], FRAME)
            out = out + poly([(inn[i][0], y0, inn[i][1]), (inn[j][0], y0, inn[j][1]), (inn[j][0], y1, inn[j][1]), (inn[i][0], y1, inn[i][1])], FRAME)
        return out
    for sd in (-1, 1):
        h = h + ring(sd * .2, 3.17, .18, .158, .135, .045, .062, .515, .57)
        h = h + rod((sd * .38, .545, 3.24), (sd * .585, .34, 3.26), .028, FRAME, 6)
        h = h + rod((sd * .585, .34, 3.26), (sd * .59, -.2, 3.17), .024, FRAME, 6)
    h = h + box(-.04, .52, 3.2, .08, .05, .05, FRAME)
    # hair: straight, middle part (a soft valley on top, fringe splits in a V at the front)
    for sd in (-1, 1):
        pts = []
        for (y, rows) in [(.6, [(0, 3.78, 3.82), (.3, 3.45, 3.9), (.6, 3.34, 3.72)]),
                          (.3, [(0, 3.66, 3.83), (.32, 3.48, 3.94), (.625, 3.2, 3.75)]),
                          (-.15, [(0, 3.4, 3.88), (.32, 3.3, 3.9), (.625, 3.12, 3.73)]),
                          (-.56, [(0, 2.98, 3.79), (.32, 3.0, 3.78), (.6, 3.04, 3.6)])]:
            for (x, base, top) in rows:
                pts += [(sd * x, y, base), (sd * x, y, top)]
        pts += [(x * 1.07, y * 1.07, 3.2 + (z - 3.2) * 1.07) for (x, y, z) in cham(0, 0, 3.2, .56, .5, .58, .17)
                if z > 3.55 and y < .45 and x * sd >= 0]
        h = h + hull(pts, HAIR)
    h = h + hull([(-.33, -.12, 3.42), (.33, -.12, 3.42), (-.33, -.12, 3.9), (.33, -.12, 3.9), (-.33, -.565, 3.0), (.33, -.565, 3.0), (-.33, -.565, 3.79), (.33, -.565, 3.79)], HAIR)   # crown + back: no parting
    h = h.rot("y", tilt, (0, 0, 2.62)).rot("z", turn, (0, 0, 2.62))
    return h


def character(pose="stand", yaw=0.0, at=(0, 0, 0)):
    P = dict(stand=dict(hips=(0, 0, 0, 0), arms=((4, 6, 8), (4, 6, 8)), lean=0, tilt=0, turn=0),
             wave=dict(hips=(0, 0, 0, 0), arms=((-12, 150, 25), (6, 8, 10)), lean=0, tilt=-6, turn=0),
             run=dict(hips=(32, -18, -30, -78), arms=((-38, 10, 95), (34, 10, 80)), lean=7, tilt=0, turn=0),
             sit=dict(hips=(85, -85, 85, -85), arms=((40, 8, 45), (40, 8, 45)), lean=-4, tilt=0, turn=0))[pose]
    hr, kr, hl, kl = P["hips"]
    legs = leg(1, hr, kr) + leg(-1, hl, kl)
    body = cbox(0, 0, 1.5, .47, .255, .14, .06, DENIM)
    body = body + hull(hulls(cham(0, 0, 1.56, .57, .31, .08, .05), cham(0, 0, 2.36, .58, .315, .1, .08)), TEE)   # boxy, straight hem over the waistband
    body = body + cyl(0, 0, 2.42, .15, .22, SKIN, n=8)
    (sr, ar, er), (sl, al, el) = P["arms"]
    body = body + arm(1, sr, ar, er) + arm(-1, sl, al, el)
    body = body + head(P["tilt"], P["turn"])
    body = body.rot("x", P["lean"], (0, 0, 1.45))
    ch = legs + body
    if pose == "run":
        ch = ch.move(0, 0, .05)
    if pose == "sit":
        ch = ch.move(0, .25, -.42)
    return ch.rot("z", yaw).move(*at)
