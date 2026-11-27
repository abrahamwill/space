"""Export a plan's furnished house (exactly what the hero render shows) to glTF binary (.glb) for Blender / three.js.

- Metres, Y up (glTF). Plan x -> glTF +X, plan y (down the plan) -> glTF +Z, height -> +Y.
- One node per object: shell (floors, walls, stair), every furniture item, wall art, the character, the page slab.
- One material per flat colour (named by its hex), emissive where the scene glows. Flat-shaded, double-sided.
- An orthographic camera named "HeroCamera" that reproduces the website hero view (azimuth 45, elevation 30).
Usage: python3 export_glb.py P2 out.glb
"""
import json, math, struct, sys
import numpy as np
import hero3d
from hero3d import m, room_of, H
from engine import Part, Cam
from plans import PLANS, M2U

U2M = 1 / M2U   # scene units -> metres


def to_gltf(p):
    """scene units (x, y, z-up) -> glTF metres (X, Y-up, Z)"""
    p = np.asarray(p, float) * U2M
    return np.stack([p[..., 0], p[..., 2], p[..., 1]], -1)


def slug(t):
    return "".join(c if c.isalnum() else "_" for c in t).strip("_") or "item"


def page_slab(key):
    """the page surface at wall-top height with the house cut out of it (0.5 m cells)"""
    rects, _ = hero3d.hero_rects(key)
    R = [q["r"] for q in rects]
    x0 = min(r[0] for r in R) - 3; x1 = max(r[0] + r[2] for r in R) + 3
    y0 = min(r[1] for r in R) - 3; y1 = max(r[1] + r[3] for r in R) + 3
    c = .5
    def inside(px, py):
        return any(r[0] < px < r[0] + r[2] and r[1] < py < r[1] + r[3] for r in R)
    tris = []
    ny, nx = int(round((y1 - y0) / c)), int(round((x1 - x0) / c))
    for j in range(ny):
        i = 0
        while i < nx:
            if inside(x0 + (i + .5) * c, y0 + (j + .5) * c):
                i += 1; continue
            k = i
            while k < nx and not inside(x0 + (k + .5) * c, y0 + (j + .5) * c):
                k += 1
            a, b, yy0, yy1 = m(x0 + i * c), m(x0 + k * c), m(y0 + j * c), m(y0 + (j + 1) * c)
            tris += [[(a, yy0, H), (b, yy0, H), (b, yy1, H)], [(a, yy0, H), (b, yy1, H), (a, yy1, H)]]
            i = k
    t = np.array(tris, float)
    return Part(t, np.tile([0xf3 / 255, 0xf3 / 255, 0xf5 / 255], (len(t), 1)), np.zeros(len(t), bool))


def objects(key):
    plan = PLANS[key]
    shell, rects, bank, stair, ytop, pathL = hero3d.build_shell(key)
    furn, decos = hero3d.furniture3d(key)
    out = [("house_shell", shell)]
    seen = {}
    for (it, a, b) in hero3d.SEGMENTS:
        if b <= a:
            continue
        x, y, w, d, k, lab, sh = it
        r, _ = room_of(plan, x + w / 2, y + d / 2)
        name = slug(f"{r[0] if r else 'outside'}_{k}" + (f"_{lab}" if lab else ""))
        seen[name] = seen.get(name, 0) + 1
        if seen[name] > 1:
            name += f"_{seen[name]}"
        out.append((name, Part(furn.t[a:b], furn.c[a:b], furn.e[a:b])))
    out.append(("wall_art", hero3d.decos3d(key, decos)))
    out.append(("character_abraham", hero3d.person(key)))
    out.append(("page_surface", page_slab(key)))
    return out


def hero_camera(key):
    """orthographic camera matching hero3d.render_hero(key, 1720, 1320)"""
    W, Hh = 1720, 1320
    g, mk, trees, tmk, cam, sc, c = hero3d.framing(key, W, Hh)
    right, up, back = cam.r, -cam.dn, cam.c            # camera looks along -back
    R = np.stack([to_gltf(right) * M2U, to_gltf(up) * M2U, to_gltf(back) * M2U], 1)   # columns, unit vectors in glTF space
    pos = to_gltf(np.asarray(c) + cam.c * m(40))
    # rotation matrix -> quaternion (x, y, z, w)
    t = np.trace(R)
    if t > 0:
        s_ = math.sqrt(t + 1) * 2; q = [(R[2, 1] - R[1, 2]) / s_, (R[0, 2] - R[2, 0]) / s_, (R[1, 0] - R[0, 1]) / s_, .25 * s_]
    else:
        i = int(np.argmax(np.diag(R))); j, k = (i + 1) % 3, (i + 2) % 3
        s_ = math.sqrt(R[i, i] - R[j, j] - R[k, k] + 1) * 2
        q = [0, 0, 0, 0]; q[i] = .25 * s_; q[j] = (R[j, i] + R[i, j]) / s_; q[k] = (R[k, i] + R[i, k]) / s_; q[3] = (R[k, j] - R[j, k]) / s_
    return dict(xmag=W / 2 / sc * U2M, ymag=Hh / 2 / sc * U2M, translation=pos.tolist(), rotation=[float(v) for v in q],
                light_dir=None, center=to_gltf(c).tolist())


def write_glb(key, path):
    objs = objects(key)
    bin_ = bytearray()
    views, accs, meshes, nodes, mats, matidx = [], [], [], [], [], {}

    def add_view(data, target):
        while len(bin_) % 4:
            bin_.append(0)
        views.append(dict(buffer=0, byteOffset=len(bin_), byteLength=len(data), target=target))
        bin_.extend(data)
        return len(views) - 1

    def material(col, emis):
        key_ = (tuple(np.round(col, 4)), bool(emis))
        if key_ not in matidx:
            hexc = "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in col)
            lin = [((v / 12.92) if v <= .04045 else ((v + .055) / 1.055) ** 2.4) for v in col]   # sRGB -> linear
            mt = dict(name=("glow_" if emis else "") + hexc, doubleSided=True,
                      pbrMetallicRoughness=dict(baseColorFactor=lin + [1.0], metallicFactor=0.0, roughnessFactor=.85))
            if emis:
                mt["emissiveFactor"] = lin
            matidx[key_] = len(mats); mats.append(mt)
        return matidx[key_]

    for name, part in objs:
        if len(part.t) == 0:
            continue
        T = to_gltf(part.t)                                   # (n, 3, 3) metres
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        ln = np.linalg.norm(n, axis=1, keepdims=True); ln[ln == 0] = 1; n = n / ln
        ok = (np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) > 1e-9)
        prims = []
        groups = {}
        for i in np.nonzero(ok)[0]:
            groups.setdefault((tuple(np.round(part.c[i], 4)), bool(part.e[i])), []).append(i)
        for (col, emis), idx in groups.items():
            idx = np.array(idx)
            pos = T[idx].reshape(-1, 3).astype(np.float32)
            nor = np.repeat(n[idx], 3, 0).astype(np.float32)
            pv = add_view(pos.tobytes(), 34962); nv = add_view(nor.tobytes(), 34962)
            accs.append(dict(bufferView=pv, componentType=5126, count=len(pos), type="VEC3", min=pos.min(0).tolist(), max=pos.max(0).tolist()))
            accs.append(dict(bufferView=nv, componentType=5126, count=len(nor), type="VEC3"))
            prims.append(dict(attributes=dict(POSITION=len(accs) - 2, NORMAL=len(accs) - 1), material=material(np.array(col), emis)))
        meshes.append(dict(name=name, primitives=prims))
        nodes.append(dict(name=name, mesh=len(meshes) - 1))
    cam = hero_camera(key)
    cameras = [dict(name="HeroCamera", type="orthographic", orthographic=dict(xmag=cam["xmag"], ymag=cam["ymag"], znear=.1, zfar=200))]
    nodes.append(dict(name="HeroCamera", camera=0, translation=cam["translation"], rotation=cam["rotation"]))
    gl = dict(asset=dict(version="2.0", generator="Space house3d exporter"), scene=0,
              scenes=[dict(name=f"house_{key}", nodes=list(range(len(nodes))))], nodes=nodes, meshes=meshes,
              materials=mats, accessors=accs, bufferViews=views, buffers=[dict(byteLength=len(bin_))], cameras=cameras)
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    while len(bin_) % 4:
        bin_.append(0)
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_))
    out += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(bin_), 0x004E4942) + bytes(bin_)
    open(path, "wb").write(out)
    return dict(objects=[o[0] for o in objs], triangles=sum(len(o[1].t) for o in objs), materials=len(mats), camera=cam, bytes=len(out))


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "P2"
    info = write_glb(key, sys.argv[2] if len(sys.argv) > 2 else f"house_{key}.glb")
    print(json.dumps({k: v for k, v in info.items() if k != "objects"}, indent=1))
    print(len(info["objects"]), "objects:", ", ".join(info["objects"]))
