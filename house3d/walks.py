"""Where the character walks (design/house-v2-blender.md step 5, first part): public/house3d/walks.json.

  blender -b house3d/house_P2.blend -P house3d/walks.py -- public/house3d/walks.json

Like the old house's waypoint graph (src/house/actors.ts, life.ts), but worked out from the house itself:
- Walls and doors come from the plan (source/plans.py): the floor of each room, kept a body's width away
  from its walls, joined through its doors.
- Furniture comes from the finished scene: rays from head height straight down; anything they hit above the
  floor (not a rug) blocks the floor around it. So he walks round the coffee table and under nothing lower
  than his head.
- SPOTS (below) are where he goes: stand and look, or sit. Each gets a shortest path from his mark (where
  hero3d.person() puts him) on that grid, pulled straight where the floor allows.
- Each spot also gets how much of him the HeroCamera sees there (walls and trees hide some rooms).

Coordinates in the JSON are plan metres (x, y), which in the site's three.js scene are (X, Z).
"""
import heapq
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import source_in_blender as S  # noqa: E402

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else os.path.join(HERE, '..', 'public', 'house3d', 'walks.json')
HOUSE = 'P2'
CELL = 0.05          # m
BODY = 0.25          # m: how close his centre comes to a wall or a piece of furniture
DOOR_EDGE = 0.15     # m: how close his centre comes to a door post (he turns a shoulder through tight ones)
HEAD = 1.65          # m: rays start here; anything lower than this is in his way
WALKABLE = ('living', 'bedroom', 'studio', 'lab', 'garden', 'deckS')
SIT_DEPTH = 0.31     # m: underside of his thighs above the floor in the designed "sit" pose

# name: where he stands (plan m), which way he faces (plan direction), what he does.
# sit spots: `seat` is where his root goes, `seat_top` the cushion height (probed from the scene);
# he walks to the stand point in front of it, turns his back to it and sits.
# run spots: `belt` is where his root goes on the treadmill, `lift` the belt's height (probed); he walks to
# the stand point behind it, faces the console, steps up onto the belt and runs in place.
SPOTS = {
    'records':   dict(at=(3.55, 3.85), face=(0, -1), act='look', room='living'),
    'turntable': dict(at=(6.85, 3.85), face=(0, -1), act='look', room='living'),
    'sofa':      dict(at=(4.95, 6.57), face=(0, -1), act='sit', seat=(4.95, 7.25), room='living'),
    'pet':       dict(at=(9.72, 4.15), face=(0, -1), act='pet', room='lab'),
    # in front of the arcade cabinet (10.2, 1.55, 0.75 x 0.75), facing its screen. Only when asked
    # (the arcade hotspot): `ask` spots aren't in his own routine.
    'arcade':    dict(at=(10.575, 2.62), face=(0, -1), act='look', room='lab', ask=True),
    'pc':        dict(at=(4.75, 1.85), face=(0, -1), act='look', room='bedroom'),
    'books':     dict(at=(0.95, 7.45), face=(-1, 0), act='look', room='studio'),
    # the garden bench (5.5, 11.0) sits behind the page's front edge, where the camera hardly sees him,
    # so in the garden he stands by the tree instead
    'tree':      dict(at=(4.9, 9.8), face=(.97, -.24), act='look', room='garden'),
    # the treadmill on the workout deck (x 1.05-2.9, y 8.6-9.4): console at the low-x end, belt x 1.95-2.7
    'treadmill': dict(at=(3.2, 9.0), face=(-1, 0), act='run', belt=(2.35, 9.0), room='studio'),
}
NOT_IN_THE_WAY = ('house_shell', 'page_surface', 'wall_art', 'character_abraham', 'living_rug_check', 'bedroom_rug', 'studio_rug_blob')

sc = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
plan = S.PLANS[HOUSE]
mark = S.spot(HOUSE)
MARK = (float(mark['at'][0]) / S.M2U, float(mark['at'][1]) / S.M2U)


# ------------------------------------------------------------------ floor from the plan
rooms = {r[0]: r[3] for r in plan['rooms'] if r[0] in WALKABLE}
X0, Y0 = -0.5, -0.5
NX, NY = int(13.5 / CELL), int(12.5 / CELL)
xs = X0 + (np.arange(NX) + .5) * CELL
ys = Y0 + (np.arange(NY) + .5) * CELL
GX, GY = np.meshgrid(xs, ys, indexing='ij')


def inside(rects, px, py):
    m = np.zeros_like(px, bool)
    for (x, y, w, d) in rects:
        m |= (px > x) & (px < x + w) & (py > y) & (py < y + d)
    return m


floor = np.zeros((NX, NY), bool)
offs = [(BODY * math.cos(a), BODY * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
for rects in rooms.values():
    m = inside(rects, GX, GY)
    for ox, oy in offs:      # keep a body's width from the room's own walls
        m &= inside(rects, GX + ox, GY + oy)
    floor |= m
room_of = lambda px, py: next((k for k, rects in rooms.items() if inside(rects, np.array(px), np.array(py))), None)
# Open edges he can walk across as well as the doors: the workout deck and the garden have no wall between
# them (both open-air), and the living room's door onto the deck is blocked by the orange chair and the sofa.
OPEN_EDGES = [(4.5, 9.3, 'y', 1.6)]     # same shape as a door: (x, y, axis of the wall, width)
for (dx, dy, axis, w) in list(plan['doors']) + OPEN_EDGES:
    a = (dx - w / 2 + DOOR_EDGE, dx + w / 2 - DOOR_EDGE) if axis == 'x' else (dy - w / 2 + DOOR_EDGE, dy + w / 2 - DOOR_EDGE)
    if axis == 'x':
        sides = (room_of(dx, dy - .3), room_of(dx, dy + .3))
        m = (GX >= a[0]) & (GX <= a[1]) & (np.abs(GY - dy) <= BODY + CELL)
    else:
        sides = (room_of(dx - .3, dy), room_of(dx + .3, dy))
        m = (GY >= a[0]) & (GY <= a[1]) & (np.abs(GX - dx) <= BODY + CELL)
    if all(sides):
        floor |= m

# ------------------------------------------------------------------ furniture from the scene
inroom = np.zeros((NX, NY), bool)
for rects in rooms.values():
    inroom |= inside(rects, GX, GY)
inroom |= floor
down = Vector((0, 0, -1))


def first_thing(px, py, top=HEAD):
    """height of the first thing under (px, py) that is in his way, or None (rugs and the shell don't count)"""
    o = Vector((px, -py, top))         # plan (x, y) -> Blender (x, -y)
    for _ in range(8):
        hit, loc, _, _, ob, _ = sc.ray_cast(dg, o, down)
        if not hit:
            return None
        if not ob.name.startswith(NOT_IN_THE_WAY) and loc.z > .05:
            return loc.z
        o = loc + down * 1e-4
    return None


occupied = np.zeros((NX, NY), bool)
for i, j in zip(*np.nonzero(inroom)):
    occupied[i, j] = first_thing(xs[i], ys[j]) is not None
# grow the furniture by a body's width
r = int(math.ceil(BODY / CELL))
blocked = occupied.copy()
oi, oj = np.nonzero(occupied)
for di in range(-r, r + 1):
    for dj in range(-r, r + 1):
        if (di * di + dj * dj) * CELL * CELL > BODY * BODY:
            continue
        ii, jj = np.clip(oi + di, 0, NX - 1), np.clip(oj + dj, 0, NY - 1)
        blocked[ii, jj] = True
walk = floor & ~blocked


# ------------------------------------------------------------------ paths
def cell(p):
    return int((p[0] - X0) / CELL), int((p[1] - Y0) / CELL)


def nearest_free(p):
    ci, cj = cell(p)
    if walk[ci, cj]:
        return ci, cj
    best = None
    for di in range(-12, 13):
        for dj in range(-12, 13):
            i, j = ci + di, cj + dj
            if 0 <= i < NX and 0 <= j < NY and walk[i, j]:
                d = di * di + dj * dj
                if best is None or d < best[0]:
                    best = (d, i, j)
    if best is None:
        raise SystemExit('no free floor near %s' % (p,))
    print('WALKS note: %s is %.2f m from free floor, path ends at the nearest free cell' % (p, math.sqrt(best[0]) * CELL))
    return best[1], best[2]


def astar(a, b):
    nb = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    g = {a: 0.0}
    came = {}
    q = [(0.0, a)]
    while q:
        _, c = heapq.heappop(q)
        if c == b:
            path = [c]
            while c in came:
                c = came[c]
                path.append(c)
            return path[::-1]
        for di, dj, w in nb:
            n = (c[0] + di, c[1] + dj)
            if not (0 <= n[0] < NX and 0 <= n[1] < NY) or not walk[n]:
                continue
            if di and dj and not (walk[c[0] + di, c[1]] and walk[c[0], c[1] + dj]):
                continue
            ng = g[c] + w
            if ng < g.get(n, 1e18):
                g[n] = ng
                came[n] = c
                heapq.heappush(q, (ng + math.hypot(n[0] - b[0], n[1] - b[1]), n))
    raise SystemExit('no path between %s and %s' % (a, b))


def centre(c):
    return (X0 + (c[0] + .5) * CELL, Y0 + (c[1] + .5) * CELL)


def clear_line(p, q):
    n = max(2, int(math.hypot(q[0] - p[0], q[1] - p[1]) / (CELL / 2)))
    for k in range(n + 1):
        x, y = p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n
        i, j = cell((x, y))
        if not walk[i, j]:
            return False
    return True


def pulled(cells):
    pts = [centre(c) for c in cells]
    out = [pts[0]]
    k = 0
    while k < len(pts) - 1:
        far = k + 1
        for m in range(len(pts) - 1, k, -1):
            if clear_line(pts[k], pts[m]):
                far = m
                break
        out.append(pts[far])
        k = far
    return out


# ------------------------------------------------------------------ how much of him the camera sees
cam = sc.objects['HeroCamera']
toward_cam = (cam.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
occluders = [(BVHTree.FromObject(o, dg), o.matrix_world.inverted()) for o in sc.objects
             if o.type == 'MESH' and not o.name.startswith('character_abraham')]
body_pts = np.unique(np.round(S.C.character('stand').t.reshape(-1, 3), 3), axis=0)[::3]


def seen(px, py, face):
    yaw = math.degrees(math.atan2(-face[0], face[1]))
    P = S.to_blender(S.C.Part(body_pts[None]).rot('z', yaw).t[0] + np.array([px * S.M2U, py * S.M2U, .04]))
    hid = 0
    for p in P:
        p = Vector(p) + toward_cam * .002
        for t, inv in occluders:
            if t.ray_cast(inv @ p, (inv.to_3x3() @ toward_cam).normalized())[0] is not None:
                hid += 1
                break
    return round(1 - hid / len(P), 2)


def seat_top(px, py):
    return first_thing(px, py, top=.9) or 0.0   # from below lamp arcs and shelves above the seat


# ------------------------------------------------------------------ run
home = nearest_free(MARK)
out = dict(
    note='Generated by house3d/walks.py. Plan metres (x, y) = three.js (X, Z).',
    mark=dict(at=[round(v, 3) for v in MARK], face=[.7071, .7071], seen=seen(*MARK, (.7071, .7071))),
    spots=[],
)
failed = []
for name, s in SPOTS.items():
    try:
        cells = astar(home, nearest_free(s['at']))
    except SystemExit as e:
        print('WALKS FAIL', name, e)
        failed.append(name)
        continue
    path = pulled(cells)
    path[0], path[-1] = MARK, s['at']
    spot = dict(name=name, act=s['act'], room=s['room'], at=list(s['at']), face=list(s['face']),
                path=[[round(x, 3), round(y, 3)] for x, y in path],
                length=round(sum(math.dist(path[k], path[k + 1]) for k in range(len(path) - 1)), 2),
                seen=seen(*s['at'], s['face']))
    if s.get('ask'):
        spot['ask'] = True
    if s['act'] == 'sit':
        top = seat_top(*s['seat'])
        spot['seat'] = list(s['seat'])
        spot['lift'] = round(top - SIT_DEPTH, 3)     # raise (or lower) the designed sit pose onto this seat
        spot['seat_top'] = round(top, 3)
    if s['act'] == 'run':
        spot['belt'] = list(s['belt'])
        spot['lift'] = round(first_thing(*s['belt'], top=.9) or 0.0, 3)   # his feet on the belt
    out['spots'].append(spot)
    print('WALKS %-9s %-8s seen %.2f  path %.1f m, %d points%s' % (name, s['room'], spot['seen'], spot['length'], len(path),
          ('  seat %.2f m, lift %+.2f m' % (spot['seat_top'], spot['lift'])) if 'seat' in spot else
          ('  belt lift %.2f m' % spot['lift']) if 'belt' in spot else ''))
# Spot to spot, for when he's asked somewhere new while at (or on the way to) another spot (life.ts ask):
# "a>b" walks from a to b; the site reverses it for b to a.
out['between'] = {}
names = [sp['name'] for sp in out['spots']]
for i, a in enumerate(names):
    for b in names[i + 1:]:
        pa, pb = SPOTS[a]['at'], SPOTS[b]['at']
        try:
            path = pulled(astar(nearest_free(pa), nearest_free(pb)))
        except SystemExit as e:
            print('WALKS FAIL', a, '>', b, e)
            failed.append('%s>%s' % (a, b))
            continue
        path[0], path[-1] = pa, pb
        out['between']['%s>%s' % (a, b)] = [[round(x, 3), round(y, 3)] for x, y in path]
print('WALKS between: %d paths' % len(out['between']))
print('WALKS mark seen', out['mark']['seen'])
if not failed:
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1)
        f.write('\n')

if '--map' in sys.argv:   # a picture of the grid, for checking
    import struct, zlib
    img = np.zeros((NY, NX, 3), np.uint8)
    img[floor.T] = (230, 220, 200)
    img[(floor & blocked).T] = (200, 120, 100)
    img[occupied.T] = (120, 60, 50)
    for s in out['spots']:
        for (a, b) in zip(s['path'], s['path'][1:]):
            for k in range(40):
                i, j = cell((a[0] + (b[0] - a[0]) * k / 40, a[1] + (b[1] - a[1]) * k / 40))
                img[j, i] = (30, 90, 220)
    raw = b''.join(b'\x00' + img[j].tobytes() for j in range(NY))
    chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', NX, NY, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')
    p = sys.argv[sys.argv.index('--map') + 1]
    open(p, 'wb').write(png)
    print('WALKS map', p)
if failed:
    raise SystemExit('WALKS FAILED: no path to %s' % failed)
print('WALKS_OK', OUT)
