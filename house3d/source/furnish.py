"""Real-size furniture for the plans in plans.py (metres). Each room type has a template laid out
against its two back walls (top and left in plan = the walls that stand in the hero). Rooms taller
than wide get the template mirrored across the diagonal, which keeps it on the back walls."""
from plans import PLANS

# item: (x, y, w, d, kind, label, shape)   shape: rect | round
ENTRY = {"P1": (1.5, 11.5, "x", .9), "P2": (3, 3.75, "y", .9), "P3": (5.5, 8, "x", 1.6), "P4": (0, 1.5, "y", .9),
         "P5": (0, 7.3, "y", .9), "P6": (2, 5.0, "y", 1.4)}


def living(W, D):
    it = [(W / 2 - 1.6, D - 3.0, 3.2, 2.1, "rug", "", "rect"),
          (.45, .05, 1.8, .4, "shelf", "Records", "rect"), (2.4, .05, 1.3, .45, "console", "Turntable", "rect"),
          (.05, .05, .35, .35, "plant", "", "round"),
          (W / 2 - 1.1, D - 1.25, 2.2, .9, "sofa", "Sofa", "rect"), (W / 2 - .38, D - 2.45, .75, .75, "table", "", "round"),
          ]
    if D >= 4:
        it += [(.35, .85, .8, .8, "chair", "", "rect"), (.05, D - 1.95, .8, 1.85, "treadmill", "Treadmill", "rect")]
    if W >= 6.2:
        it.append((W - 2.1, .05, 2.0, .6, "counter", "Coffee bar", "rect"))
    deco = [("top", .45, 2.25, "window")] + ([("left", D - 2.0, D - .2, "photos")] if D >= 4 else [])
    return it, deco


def studio(W, D):
    return ([(.3, .05, 1.6, .8, "desk", "Desk", "rect"), (.85, 1.0, .5, .5, "chair", "", "round"),
             (.05, 1.25, .45, min(1.6, D - 1.35), "shelf", "Archive", "rect"), (W - .45, D - .5, .4, .4, "plant", "", "round")],
            [("top", 2.05, min(W - .2, 3.3), "pinboard")])


def lab(W, D):
    return ([(.05, .05, 2.0, .7, "desk", "Bench", "rect"), (W - .8, .05, .75, .75, "arcade", "Arcade", "rect"),
             (.25, 1.3, .5, .5, "table", "Voice", "round"), (W - 1.35, D - 1.35, .85, .85, "pet", "Pet", "round")],
            [("top", .1, 1.9, "poster")])


def bedroom(W, D):
    dw = 1.6 if W >= 4.4 else 1.3
    it = [(.35, .05, 1.6, 2.0, "bed", "Bed", "rect"), (1.98, .05, .38, .38, "table", "", "rect"),
          (2.45, .05, dw, .7, "desk", "Desk + PC", "rect"), (2.45 + dw / 2 - .25, .9, .5, .5, "chair", "", "round")]
    if D >= 3.3:
        it.append((.05, 2.25, .6, min(1.2, D - 2.35), "wardrobe", "Wardrobe", "rect"))
    return it, [("top", .35, 1.95, "photos")]


def entry(W, D):
    return [(.1, .1, .4, .4, "plant", "", "round"), (W - .5, .1, .4, 1.2, "shelf", "Shoes", "rect")], []


def hall(W, D):
    return [(.25, .25, W - .5, D - .5, "rug", "", "rect")], []


def garden(W, D):
    it = [(W * .45 - .8, D * .4 - .8, 1.6, 1.6, "tree", "Tree", "round")]
    if W * D > 9:
        it.append((W * .72 - .5, D * .72 - .35, 1.0, .7, "pond", "", "round"))
        it.append((.3, D - .75, 1.4, .45, "bench", "Bench", "rect"))
    return it, []


def porch(W, D):
    if min(W, D) < 1.2 or max(W, D) < 2.5:
        return [], []
    return [(.4, .3, .7, .9, "lounger", "", "rect"), (1.3, .3, .7, .9, "lounger", "", "rect")], []


# hand placement where the template's set pieces would block a door (absolute metres)
OVERRIDE = {
    ("P2", "living"): ([(3.45, 5.0, 3.8, 2.3, "rug", "check", "rect"), (3.05, 3.05, .95, .4, "shelf", "Records", "rect"), (6.2, 3.05, 1.3, .45, "console", "Turntable", "rect"),
                        (7.6, 3.05, .35, .35, "plant", "", "round"), (4.05, 6.15, 2.5, 1.6, "sofaL", "Sofa", "rect"), (4.45, 5.62, 1.15, .62, "ctable", "", "rect"),
                        (3.05, 6.25, .8, .8, "chair", "", "rect"), (6.65, 7.25, .4, .4, "arclamp", "Arc lamp", "round")],
                       [("top", 6, 3, .2, 1.9, "window"), ("left", 3, 3, 3.05, 4.9, "photos")]),
    ("P2", "studio"): ([(.05, 4.8, .8, 1.6, "desk", "Desk", "rect"), (1.0, 5.35, .5, .5, "chair", "Mesh", "round"), (1.25, 4.55, 1.6, .45, "shelf", "Archive", "rect"),
                        (.05, 6.55, .45, 1.9, "bookcase", "Books", "rect"), (.3, 5.05, 1.9, 1.5, "rug", "blob", "rect"),
                        (2.5, 8.0, .3, .3, "lamp", "in", "round")],
                       [("left", 0, 4.5, .1, 1.95, "gallery")]),
    ("P2", "bedroom"): ([(1.85, .05, 1.6, 2.0, "bed", "Bed", "rect"), (3.48, .05, .38, .38, "table", "", "rect"), (3.95, .05, 1.6, .7, "desk", "Desk + PC", "rect"),
                         (4.5, .9, .5, .5, "chair", "", "round"), (2.0, 2.15, 1.4, .75, "rug", "", "rect")],
                        [("top", 1.5, 0, .35, 1.95, "photos"), ("left", 1.5, 0, .1, 2.05, "movies")]),
    ("P2", "lab"): ([(8.05, 1.55, 2.0, .7, "desk", "Bench", "rect"), (10.2, 1.55, .75, .75, "arcade", "Arcade", "rect"),
                     (8.25, 2.8, .5, .5, "table", "Voice", "round"), (9.3, 2.75, .85, .85, "pet", "Pet", "round"),
                     (10.4, 4.55, .5, .5, "plinth", "Phone", "rect"), (10.4, 5.4, .5, .5, "plinth", "Laptop", "rect"), (9.55, 5.4, .5, .5, "plinth", "Game", "rect")],
                    [("top", 8, 1.5, .1, 1.9, "poster")]),
    ("P2", "deckS"): ([(1.05, 8.6, 1.85, .8, "treadmill", "Treadmill", "rect"), (.1, 8.6, .75, 1.3, "gym", "pullup", "rect"),
                       (1.05, 9.5, 1.5, .5, "gym", "mat", "rect"), (1.4, 9.55, .55, .4, "gym", "parallettes", "rect"),
                       (2.6, 9.55, .35, .35, "gym", "kettlebell", "round"), (4.05, 8.6, .4, .6, "gym", "dumbbells", "rect"),
                       (3.95, 10.6, .45, .45, "plant", "", "round")], []),
    ("P2", "pocketNW"): ([(.55, 3.55, .42, .42, "stone", "", "round"), (1.35, 3.55, .42, .42, "stone", "", "round"), (2.15, 3.55, .42, .42, "stone", "", "round"),
                          (2.45, 3.08, .45, .45, "shrub", "", "round"), (2.45, 4.0, .45, .45, "shrub", "", "round")], []),
    ("P2", "pocketNE"): ([(6.35, .55, 1.3, 1.3, "tree", "Tree", "round"), (7.35, 2.3, .5, .5, "shrub", "", "round"), (6.15, 2.35, .45, .45, "shrub", "", "round")], []),
    ("P2", "pocketSE"): ([(8.25, 6.2, 1.25, 1.25, "tree", "Tree", "round"), (10.25, 6.25, .5, .5, "shrub", "", "round")], []),
    ("P3", "living"): ([(4.6, 4.9, 3.0, 2.0, "rug", "", "rect"), (3.05, 3.1, .4, 1.8, "shelf", "Records", "rect"), (6.15, 3.05, 1.3, .45, "console", "Turntable", "rect"),
                        (7.6, 3.05, .35, .35, "plant", "", "round"), (4.4, 6.85, 2.2, .9, "sofa", "Sofa", "rect"), (5.1, 5.55, .75, .75, "table", "", "round"),
                        (3.05, 6.05, .8, 1.85, "treadmill", "Treadmill", "rect")],
                       [("left", 3, 3, 3.05, 4.9, "photos")]),
    ("P5", "living"): ([(1.2, 4.3, 2.6, 2.6, "rug", "", "rect"), (.05, 3.4, .4, 1.8, "shelf", "Records", "rect"), (.05, 5.35, .45, 1.3, "console", "Turntable", "rect"),
                        (.05, 3.05, .35, .35, "plant", "", "round"), (3.3, 4.5, .9, 2.2, "sofa", "Sofa", "rect"), (2.0, 5.2, .75, .75, "table", "", "round"),
                        (2.25, 3.35, .8, .8, "chair", "", "rect"), (4.65, 3.1, .8, 1.85, "treadmill", "Treadmill", "rect")],
                       [("left", 0, 3, .4, 2.2, "window"), ("top", 0, 3, 4.65, 5.45, "photos")]),
    ("P6", "living"): ([(3.2, 5.4, 3.2, 2.1, "rug", "", "rect"), (3.3, 3.55, 1.8, .4, "shelf", "Records", "rect"), (6.25, 3.55, 1.2, .45, "console", "Turntable", "rect"),
                        (3.7, 7.35, 2.2, .9, "sofa", "Sofa", "rect"), (4.4, 6.05, .75, .75, "table", "", "round"), (2.05, 6.55, .8, 1.85, "treadmill", "Treadmill", "rect")],
                       [("left", 2, 3.5, 3.1, 4.9, "photos")]),
}

TEMPLATES = dict(living=living, studio=studio, lab=lab, bedroom=bedroom, entry=entry, hall=hall, garden=garden, porch=porch)


def _exterior(plan, x0, y0, w, d):
    """metres of outside wall on the room's top and left edges (outside = no room or only lawn beyond)."""
    def other(px, py):
        for r in plan["rooms"]:
            if r[0] == "apron":
                continue
            for (x, y, ww, dd) in r[3]:
                if x < px < x + ww and y < py < y + dd:
                    return r
        return None
    n = 20
    top = sum(other(x0 + (i + .5) * w / n, y0 - .1) is None for i in range(n)) * w / n
    left = sum(other(x0 - .1, y0 + (i + .5) * d / n) is None for i in range(n)) * d / n
    return top, left


def furnish(key):
    plan = PLANS[key]
    items, decos = [], []
    for rk, label, kind, rects in plan["rooms"]:
        if rk == "apron" or kind not in TEMPLATES:
            continue
        if (key, rk) in OVERRIDE:
            it, de = OVERRIDE[(key, rk)]
            items += it; decos += de
            continue
        x0, y0, w, d = max(rects, key=lambda r: r[2] * r[3])
        top_ext, left_ext = _exterior(plan, x0, y0, w, d)
        swap = (left_ext > top_ext + .5) if kind not in ("garden", "porch", "hall") and (top_ext or left_ext) else d > w * 1.05
        W, D = (d, w) if swap else (w, d)
        it, de = TEMPLATES[kind](W, D)
        for (x, y, iw, idd, k, lab_, sh) in it:
            if swap:
                x, y, iw, idd = y, x, idd, iw
            items.append((x0 + x, y0 + y, iw, idd, k, lab_, sh))
        if kind == "living" and len(rects) > 1:      # L-shaped living: treadmill corner in the leg
            lx, ly, lw, ld = [r for r in rects if r != (x0, y0, w, d)][0]
            items += [(lx + .05, ly + ld - 1.95, .8, 1.85, "treadmill", "Treadmill", "rect"), (lx + 1.2, ly + .4, .8, .8, "chair", "", "rect")]
            decos.append(("left", lx, ly, ld - 2.0, ld - .2, "photos"))
        for (wall, a, b, k) in de:
            if swap:
                wall = {"top": "left", "left": "top"}[wall]
            decos.append((wall, x0, y0, a, b, k))
    return items, decos
