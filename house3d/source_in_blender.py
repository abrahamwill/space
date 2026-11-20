"""Import the house source (source/*.py) inside Blender's Python.

source/engine.py needs scipy's ConvexHull and Pillow (for its own renderer, unused here). Blender's Python
ships numpy only, so stand in for both: the hull comes from Blender's convex hull operator.
Used by rig_character.py and walks.py:  import source_in_blender as S; S.C (character), S.hero3d, ...
"""
import os
import sys
import types

import bmesh
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


class ConvexHull:
    def __init__(self, pts):
        bm = bmesh.new()
        vs = [bm.verts.new(tuple(p)) for p in np.asarray(pts, float)]
        bm.verts.index_update()
        bmesh.ops.convex_hull(bm, input=vs)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        self.simplices = np.array([[v.index for v in f.verts] for f in bm.faces], int)
        bm.free()


try:
    import scipy.spatial  # noqa: F401
except ImportError:
    scipy = types.ModuleType('scipy')
    scipy.spatial = types.ModuleType('scipy.spatial')
    scipy.spatial.ConvexHull = ConvexHull
    sys.modules['scipy'], sys.modules['scipy.spatial'] = scipy, scipy.spatial
try:
    import PIL  # noqa: F401
except ImportError:
    pil = types.ModuleType('PIL')
    pil.Image, pil.ImageDraw = types.ModuleType('PIL.Image'), types.ModuleType('PIL.ImageDraw')
    sys.modules.update({'PIL': pil, 'PIL.Image': pil.Image, 'PIL.ImageDraw': pil.ImageDraw})

sys.path.insert(0, os.path.join(HERE, 'source'))
import character as C  # noqa: E402,F401
import hero3d  # noqa: E402,F401
from furnish import furnish  # noqa: E402,F401
from plans import M2U, PLANS  # noqa: E402,F401

U2M = 1 / M2U


def spot(key):
    """(pose, yaw, at) that hero3d.person() gives the character: catch its call instead of copying it."""
    out = {}
    orig = hero3d.character
    hero3d.character = lambda pose, yaw, at: (out.update(pose=pose, yaw=yaw, at=at), orig(pose, yaw, at))[1]
    try:
        hero3d.person(key)
    finally:
        hero3d.character = orig
    return out


def to_blender(p):
    """source units (x = his right / plan x, y = forward / plan y, z up) -> Blender metres.
    Same as export_glb.py (glTF X = x, Y = z, Z = y) followed by Blender's glTF import (Y-up -> Z-up)."""
    p = np.asarray(p, float) * U2M
    return np.stack([p[..., 0], -p[..., 1], p[..., 2]], -1)
