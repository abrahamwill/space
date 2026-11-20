"""Tiny low-poly renderer: orthographic camera, z-buffer, flat shading, soft sun shadows.
Geometry is built from Parts (triangle soups). numpy + scipy + Pillow only."""
import math
import numpy as np
from scipy.spatial import ConvexHull
from PIL import Image, ImageDraw


def hx(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


class Part:
    def __init__(s, t=None, c=None, e=None):
        s.t = np.zeros((0, 3, 3)) if t is None else np.asarray(t, float)
        s.c = np.zeros((0, 3)) if c is None else np.asarray(c, float)
        s.e = np.zeros(0, bool) if e is None else np.asarray(e, bool)

    def __add__(s, o):
        return Part(np.concatenate([s.t, o.t]), np.concatenate([s.c, o.c]), np.concatenate([s.e, o.e]))

    def rot(s, axis, deg, pivot=(0, 0, 0)):
        a = math.radians(deg); c, n = math.cos(a), math.sin(a)
        R = {"x": [[1, 0, 0], [0, c, -n], [0, n, c]], "y": [[c, 0, n], [0, 1, 0], [-n, 0, c]], "z": [[c, -n, 0], [n, c, 0], [0, 0, 1]]}[axis]
        p = np.asarray(pivot, float)
        return Part((s.t - p) @ np.array(R).T + p, s.c, s.e)

    def move(s, dx, dy, dz):
        return Part(s.t + np.array([dx, dy, dz]), s.c, s.e)

    def scale(s, sx, sy, sz, pivot=(0, 0, 0)):
        p = np.asarray(pivot, float)
        return Part((s.t - p) * np.array([sx, sy, sz]) + p, s.c, s.e)


def _mk(tris, col, emis=False):
    tris = np.asarray(tris, float).reshape(-1, 3, 3)
    return Part(tris, np.tile(hx(col), (len(tris), 1)), np.full(len(tris), emis))


def poly(pts, col, emis=False):
    pts = [tuple(p) for p in pts]
    return _mk([[pts[0], pts[i], pts[i + 1]] for i in range(1, len(pts) - 1)], col, emis)


def box(x, y, z, w, d, h, col, top=None, emis=False):
    X, Y, Z = x + w, y + d, z + h
    v = lambda a, b, c: (a, b, c)
    faces = [([v(x, y, Z), v(X, y, Z), v(X, Y, Z), v(x, Y, Z)], top or col),
             ([v(x, y, z), v(X, y, z), v(X, Y, z), v(x, Y, z)], col),
             ([v(x, y, z), v(X, y, z), v(X, y, Z), v(x, y, Z)], col),
             ([v(x, Y, z), v(X, Y, z), v(X, Y, Z), v(x, Y, Z)], col),
             ([v(x, y, z), v(x, Y, z), v(x, Y, Z), v(x, y, Z)], col),
             ([v(X, y, z), v(X, Y, z), v(X, Y, Z), v(X, y, Z)], col)]
    out = Part()
    for f, c in faces:
        out = out + poly(f, c, emis)
    return out


def hull(pts, col, emis=False):
    pts = np.asarray(pts, float)
    h = ConvexHull(pts)
    return _mk(pts[h.simplices], col, emis)


def cham(cx, cy, cz, hxs, hys, hzs, ch):
    """points of a box with chamfered corners (feed to hull)"""
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                pts += [(cx + sx * hxs, cy + sy * (hys - ch), cz + sz * (hzs - ch)),
                        (cx + sx * (hxs - ch), cy + sy * hys, cz + sz * (hzs - ch)),
                        (cx + sx * (hxs - ch), cy + sy * (hys - ch), cz + sz * hzs)]
    return pts


def cbox(cx, cy, cz, hxs, hys, hzs, ch, col, emis=False):
    return hull(cham(cx, cy, cz, hxs, hys, hzs, ch), col, emis)


def cyl(cx, cy, z, r, h, col, top=None, n=12, ry=None, emis=False):
    ry = r if ry is None else ry
    ang = [i * 2 * math.pi / n for i in range(n)]
    b = [(cx + r * math.cos(a), cy + ry * math.sin(a), z) for a in ang]
    t = [(cx + r * math.cos(a), cy + ry * math.sin(a), z + h) for a in ang]
    out = poly(t, top or col, emis) + poly(b, col, emis)
    for i in range(n):
        j = (i + 1) % n
        out = out + poly([b[i], b[j], t[j], t[i]], col, emis)
    return out


def disc(cx, cy, z, r, col, n=20, ry=None, emis=False):
    ry = r if ry is None else ry
    return poly([(cx + r * math.cos(a), cy + ry * math.sin(a), z) for a in [i * 2 * math.pi / n for i in range(n)]], col, emis)


def _perp(d):
    d = d / np.linalg.norm(d)
    a = np.array([0, 0, 1.0]) if abs(d[2]) < .9 else np.array([1.0, 0, 0])
    u = np.cross(d, a); u /= np.linalg.norm(u)
    return u, np.cross(d, u)


def cone(p0, p1, r0, r1, col, n=10, emis=False):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    u, v = _perp(p1 - p0)
    pts = []
    for i in range(n):
        a = i * 2 * math.pi / n
        o = u * math.cos(a) + v * math.sin(a)
        pts += [p0 + o * r0, p1 + o * r1]
    return hull(pts, col, emis)


def rod(p0, p1, r, col, n=8, emis=False):
    return cone(p0, p1, r, r, col, n, emis)


_ICO = None


def ico(c, r, col, sub=1, sc=(1, 1, 1), emis=False, seed=None, jit=0.0):
    global _ICO
    t = (1 + 5 ** .5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    V = [np.array(v, float) / np.linalg.norm(v) for v in V]
    for _ in range(sub):
        mid = {}
        def m(a, b):
            k = tuple(sorted((a, b)))
            if k not in mid:
                p = V[a] + V[b]; V.append(p / np.linalg.norm(p)); mid[k] = len(V) - 1
            return mid[k]
        F2 = []
        for a, b, cc in F:
            ab, bc, ca = m(a, b), m(b, cc), m(cc, a)
            F2 += [(a, ab, ca), (b, bc, ab), (cc, ca, bc), (ab, bc, ca)]
        F = F2
    V = np.array(V)
    if jit:
        rng = np.random.default_rng(seed)
        V = V * (1 + rng.uniform(-jit, jit, (len(V), 1)))
    V = V * r * np.array(sc) + np.asarray(c, float)
    return _mk(V[np.array(F)], col, emis)


# --- planar decals on walls
def qx(X, y0, y1, z0, z1, col, emis=False):
    return poly([(X, y0, z0), (X, y1, z0), (X, y1, z1), (X, y0, z1)], col, emis)


def qy(Y, x0, x1, z0, z1, col, emis=False):
    return poly([(x0, Y, z0), (x1, Y, z0), (x1, Y, z1), (x0, Y, z1)], col, emis)


def cx_(X, cy, cz, r, col, n=20, rz=None, emis=False):
    rz = r if rz is None else rz
    return poly([(X, cy + r * math.cos(a), cz + rz * math.sin(a)) for a in [i * 2 * math.pi / n for i in range(n)]], col, emis)


def cy_(Y, cxx, cz, r, col, n=20, rz=None, emis=False):
    rz = r if rz is None else rz
    return poly([(cxx + r * math.cos(a), Y, cz + rz * math.sin(a)) for a in [i * 2 * math.pi / n for i in range(n)]], col, emis)


# ---------------- camera + raster ----------------
class Cam:
    def __init__(s, az, el):
        a, e = math.radians(az), math.radians(el)
        s.c = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
        s.r = np.array([math.sin(a), -math.cos(a), 0.0])
        s.dn = np.array([math.sin(e) * math.cos(a), math.sin(e) * math.sin(a), -math.cos(e)])
        s.horiz = np.array([math.cos(a), math.sin(a)])

    def proj(s, P):
        P = np.asarray(P, float)
        return np.stack([P @ s.r, P @ s.dn, P @ s.c], -1)


def raster(xy, z, W, H):
    zb = np.full((H, W), -np.inf, np.float32)
    ib = np.full((H, W), -1, np.int32)
    XY = xy.tolist(); Z = z.tolist()
    for i in range(len(XY)):
        (x0, y0), (x1, y1), (x2, y2) = XY[i]
        mnx = max(int(math.floor(min(x0, x1, x2))), 0); mxx = min(int(math.ceil(max(x0, x1, x2))), W - 1)
        mny = max(int(math.floor(min(y0, y1, y2))), 0); mxy = min(int(math.ceil(max(y0, y1, y2))), H - 1)
        if mnx > mxx or mny > mxy:
            continue
        A = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(A) < 1e-9:
            continue
        px = np.arange(mnx, mxx + 1, dtype=np.float32) + .5
        py = (np.arange(mny, mxy + 1, dtype=np.float32) + .5)[:, None]
        w0 = ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py)) / A
        w1 = ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py)) / A
        w2 = 1 - w0 - w1
        ins = (w0 >= -1e-5) & (w1 >= -1e-5) & (w2 >= -1e-5)
        if not ins.any():
            continue
        z0, z1, z2 = Z[i]
        zz = w0 * z0 + w1 * z1 + w2 * z2
        sub = zb[mny:mxy + 1, mnx:mxx + 1]
        m = ins & (zz > sub)
        sub[m] = zz[m]
        ib[mny:mxy + 1, mnx:mxx + 1][m] = i
    return zb, ib


def render(part, cam, W, H, scale, center, ss=2, mask_poly=None, light_az=None, light_el=52,
           amb=.56, kd=.52, bg=None, shadow=True):
    """center: world point placed at image centre. scale: px per world unit (output px)."""
    T, C, E = part.t, part.c, part.e
    s = scale * ss; WW, HH = W * ss, H * ss
    pc = cam.proj(np.asarray(center, float)[None])[0]
    P = cam.proj(T.reshape(-1, 3)).reshape(-1, 3, 3)
    xy = np.empty((len(T), 3, 2))
    xy[..., 0] = (P[..., 0] - pc[0]) * s + WW / 2
    xy[..., 1] = (P[..., 1] - pc[1]) * s + HH / 2
    zb, ib = raster(xy, P[..., 2], WW, HH)
    # normals facing camera
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True); ln[ln == 0] = 1; n = n / ln
    n[(n @ cam.c) < 0] *= -1
    laz = (math.degrees(math.atan2(cam.c[1], cam.c[0])) + 135) if light_az is None else light_az
    L = Cam(laz, light_el)
    diff = np.clip(n @ L.c, 0, 1)
    hit = ib >= 0
    idx = ib[hit]
    vis = np.ones(idx.shape, np.float32)
    if shadow:
        # world positions of visible pixels
        yy, xx = np.nonzero(hit)
        u = (xx + .5 - WW / 2) / s + pc[0]; v = (yy + .5 - HH / 2) / s + pc[1]; d = zb[hit]
        Pw = np.outer(u, cam.r) + np.outer(v, cam.dn) + np.outer(d, cam.c)
        Pw += n[idx] * 0.03
        LP = L.proj(T.reshape(-1, 3)).reshape(-1, 3, 3)
        mn = LP[..., :2].reshape(-1, 2).min(0) - .5; mx = LP[..., :2].reshape(-1, 2).max(0) + .5
        res = 3600
        ls = res / max(mx - mn)
        lxy = (LP[..., :2] - mn) * ls
        sm, _ = raster(lxy, LP[..., 2], int((mx[0] - mn[0]) * ls) + 2, int((mx[1] - mn[1]) * ls) + 2)
        q = L.proj(Pw)
        qa = (q[:, 0] - mn[0]) * ls; qb = (q[:, 1] - mn[1]) * ls
        acc = np.zeros(len(q), np.float32)
        offs = [(0, 0), (1.3, 0), (-1.3, 0), (0, 1.3), (0, -1.3), (.9, .9), (-.9, -.9), (.9, -.9), (-.9, .9)]
        for oa, ob in offs:
            ia = np.clip((qa + oa).astype(int), 0, sm.shape[1] - 1); ibb = np.clip((qb + ob).astype(int), 0, sm.shape[0] - 1)
            acc += (q[:, 2] >= sm[ibb, ia] - 0.06)
        vis = acc / len(offs)
        vis[E[idx]] = 1
    sh = amb + kd * diff[idx] * vis
    col = C[idx] * sh[:, None]
    col[E[idx]] = C[idx][E[idx]]
    img = np.zeros((HH, WW, 4), np.float32)
    if bg is not None:
        img[..., :3] = hx(bg); img[..., 3] = 1
    img[hit, :3] = np.clip(col, 0, 1); img[hit, 3] = 1
    out = Image.fromarray((img * 255).astype(np.uint8), "RGBA")
    if mask_poly is not None:
        polys = mask_poly if np.asarray(mask_poly[0], float).ndim == 2 else [mask_poly]
        mask = Image.new("L", out.size, 0); md = ImageDraw.Draw(mask)
        for pl in polys:
            mp = cam.proj(np.asarray(pl, float))
            md.polygon([((p[0] - pc[0]) * s + WW / 2, (p[1] - pc[1]) * s + HH / 2) for p in mp], fill=255)
        a = np.minimum(np.array(out.getchannel("A")), np.array(mask))
        out.putalpha(Image.fromarray(a))
    out = out.resize((W, H), Image.LANCZOS)

    def to_px(p):
        q = cam.proj(np.asarray(p, float)[None])[0]
        return ((q[0] - pc[0]) * scale + W / 2, (q[1] - pc[1]) * scale + H / 2)
    return out, to_px
