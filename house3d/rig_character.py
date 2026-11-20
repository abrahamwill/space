"""Rig and animate character_abraham for the website (design/house-v2-blender.md, steps 4 and 5).

  blender -b house3d/house_P2.blend -P house3d/rig_character.py -- public/house3d/character.glb

The mesh is not modelled again. It is built by the same source code that put character_abraham in the
house (source/character.py), in a neutral pose, and split into rigid pieces; each piece belongs to one
bone whose joint sits exactly on the pivot the source rotates that piece around. So the source's own
pose angles (character.POSES) become keyframes, and the "wave" pose lands on the same triangles as the
character_abraham in house_P2.blend (checked below; the script fails if they drift apart).

Placement, scale and materials match the house: same spot, same yaw, one material per hex colour, and
the same finish as finish.py (weld, outward faces, 0.7 cm bevel on edges sharper than 30°).

Clips (30 fps):
  idle  4 s loop    stands as designed ("stand"), breathes, glances aside. Frame 0 is the poster pose.
  wave  1.2 s loop  the designed "wave" pose, hand waving. The site crossfades idle <-> wave.
  walk  1 s loop    a walk cycle, half-way to the designed "run" pose.
  sit   2 s loop    the designed "sit" pose, breathing. Sits on whatever is at the spot it is moved to.

Writes the GLB (Draco) and house3d/character_abraham.blend next to this script.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, bvhtree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else os.path.join(HERE, '..', 'public', 'house3d', 'character.glb')
FPS = 30
HOUSE = 'P2'


# ------------------------------------------------------------------ the source, inside Blender
sys.path.insert(0, HERE)
import source_in_blender as S  # noqa: E402
from source_in_blender import C, hero3d, M2U, U2M, to_blender  # noqa: E402,F401

_spot = S.spot(HOUSE)   # where the house puts him: hero3d.person()'s spot and yaw


# That mapping mirrors y, so a source rotation about x or z turns the other way in Blender; about y it doesn't.
def rot(axis, deg):
    return Matrix.Rotation(math.radians(-deg if axis in 'xz' else deg), 4, axis.upper())


# ------------------------------------------------------------------ bones
# name: (parent, pivot in source units). Pivots are the ones character.py rotates around.
BONES = {
    'root':       (None, (0, 0, 0)),
    'thigh.R':    ('root', (.25, 0, 1.42)),
    'shin.R':     ('thigh.R', (.25, 0, .86)),
    'thigh.L':    ('root', (-.25, 0, 1.42)),
    'shin.L':     ('thigh.L', (-.25, 0, .86)),
    'spine':      ('root', (0, 0, 1.45)),
    'head':       ('spine', (0, 0, 2.62)),
    'arm.R':      ('spine', (.62, 0, 2.34)),
    'forearm.R':  ('arm.R', (.68, 0, 1.8)),
    'arm.L':      ('spine', (-.62, 0, 2.34)),
    'forearm.L':  ('arm.L', (-.68, 0, 1.8)),
}


def pose_dict(hips=(0, 0, 0, 0), arms=((0, 0, 0), (0, 0, 0)), lean=0, tilt=0, turn=0, move=(0, 0, 0)):
    return dict(hips=hips, arms=arms, lean=lean, tilt=tilt, turn=turn, move=move)


ZERO = pose_dict()


def bone_rotations(P):
    """character.py's pose angles -> each bone's rotation, composed the way the source composes them."""
    hr, kr, hl, kl = P['hips']
    (sr, ar, er), (sl, al, el) = P['arms']
    R = {
        'root': Matrix.Identity(4),
        'thigh.R': rot('x', hr), 'shin.R': rot('x', kr),
        'thigh.L': rot('x', hl), 'shin.L': rot('x', kl),
        'spine': rot('x', P['lean']),
        'head': rot('z', P['turn']) @ rot('y', P['tilt']),          # head(): rot y (tilt), then rot z (turn)
        # arm(): rot y by -sd * abduction, then rot x (swing), around the shoulder
        'arm.R': rot('x', sr) @ rot('y', -1 * ar), 'forearm.R': rot('x', er),
        'arm.L': rot('x', sl) @ rot('y', 1 * al), 'forearm.L': rot('x', el),
    }
    return R


# ------------------------------------------------------------------ split the mesh into rigid pieces
def tris(P):
    return C.character(P).t


def label_triangles():
    """Which bone moves each triangle: nudge one joint at a time and see what moves with it.
    The most specific joint wins (forearm before arm, shin before thigh, arm/head before spine)."""
    base = tris(ZERO)
    n = len(base)

    def moved(**kw):
        P = dict(ZERO, **kw)
        return np.abs(tris(P) - base).max(axis=(1, 2)) > 1e-9

    tests = [
        ('forearm.R', dict(arms=((0, 0, 30), (0, 0, 0)))),
        ('forearm.L', dict(arms=((0, 0, 0), (0, 0, 30)))),
        ('arm.R', dict(arms=((30, 0, 0), (0, 0, 0)))),
        ('arm.L', dict(arms=((0, 0, 0), (30, 0, 0)))),
        ('head', dict(tilt=30)),
        ('spine', dict(lean=30)),
        ('shin.R', dict(hips=(0, 30, 0, 0))),
        ('shin.L', dict(hips=(0, 0, 0, 30))),
        ('thigh.R', dict(hips=(30, 0, 0, 0))),
        ('thigh.L', dict(hips=(0, 0, 30, 0))),
    ]
    label = np.array([''] * n, dtype=object)
    for bone, kw in tests:
        m = moved(**kw) & (label == '')
        label[m] = bone
    label[label == ''] = 'root'
    return base, label


# ------------------------------------------------------------------ build
def material(hexc):
    m = bpy.data.materials.get(hexc)
    if m:
        return m
    m = bpy.data.materials.new(hexc)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    rgb = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    b.inputs['Base Color'].default_value = [(v / 12.92) if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb] + [1]
    b.inputs['Metallic'].default_value = 0
    b.inputs['Roughness'].default_value = .85
    m.use_backface_culling = False
    return m


def finish_tools():
    """weld / fix_winding / bevel / dedupe from finish.py, without running finish.py itself."""
    src = open(os.path.join(HERE, 'finish.py'), encoding='utf-8').read()
    src = src.split('# ---------------------------------------------------------------- run')[0]
    ns = {}
    exec(compile(src, 'finish.py', 'exec'), ns)
    return ns


def build():
    base, label = label_triangles()
    part = C.character(ZERO)
    cols = ['#%02x%02x%02x' % tuple(int(round(v * 255)) for v in c) for c in part.c]
    F = finish_tools()
    sc = bpy.context.scene
    pieces = []
    for bone in BONES:
        idx = np.nonzero(label == bone)[0]
        if not len(idx):
            continue
        t = to_blender(base[idx]).reshape(-1, 3)
        me = bpy.data.meshes.new('character_' + bone)
        me.from_pydata([tuple(v) for v in t], [], [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(idx))])
        names = sorted({cols[i] for i in idx})
        for nme in names:
            me.materials.append(material(nme))
        me.polygons.foreach_set('material_index', [names.index(cols[i]) for i in idx])
        ob = bpy.data.objects.new('character_' + bone, me)
        sc.collection.objects.link(ob)
        F['dedupe'](ob)
        if F['weld'](ob):
            F['fix_winding'](ob)
            F['bevel'](ob)
        ob.vertex_groups.new(name=bone).add(range(len(me.vertices)), 1.0, 'REPLACE')
        pieces.append(ob)

    # apply the bevel, then join the pieces into one mesh (each keeps its own vertex group)
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in pieces:
        if ob.modifiers:
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            old = ob.data
            ob.modifiers.clear()
            ob.data = me
            bpy.data.meshes.remove(old)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in pieces:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    body.name = body.data.name = 'character_abraham'

    # armature, every bone along +Y with no roll, so its axes are the character's own
    arm_data = bpy.data.armatures.new('rig_abraham')
    rig = bpy.data.objects.new('rig_abraham', arm_data)
    sc.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for name, (parent, piv) in BONES.items():
        b = arm_data.edit_bones.new(name)
        b.head = Vector(to_blender(piv))
        b.tail = b.head + Vector((0, .08, 0))
        b.roll = 0
        if parent:
            b.parent = arm_data.edit_bones[parent]
            b.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')

    body.parent = rig
    mod = body.modifiers.new('Armature', 'ARMATURE')
    mod.object = rig

    # placement: the spot and yaw hero3d.person() gives him
    rig.location = Vector(to_blender(_spot['at']))
    rig.rotation_mode = 'XYZ'
    rig.rotation_euler = rot('z', _spot['yaw']).to_euler()
    return rig, body


def set_pose(rig, P):
    R = bone_rotations(P)
    for name, pb in rig.pose.bones.items():
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = R[name].to_quaternion()
        pb.location = Vector(to_blender(P.get('move', (0, 0, 0)))) if name == 'root' else Vector()


def key_pose(rig, P, frame):
    set_pose(rig, P)
    for name, pb in rig.pose.bones.items():
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        if name == 'root':
            pb.keyframe_insert('location', frame=frame)


# ------------------------------------------------------------------ clips
def mix(a, b, k):
    """blend two pose dicts (k = 0 -> a, 1 -> b)"""
    f = lambda x, y: x + (y - x) * k
    return pose_dict(hips=tuple(f(x, y) for x, y in zip(a['hips'], b['hips'])),
                     arms=tuple(tuple(f(x, y) for x, y in zip(sa, sb)) for sa, sb in zip(a['arms'], b['arms'])),
                     lean=f(a['lean'], b['lean']), tilt=f(a['tilt'], b['tilt']), turn=f(a['turn'], b['turn']),
                     move=tuple(f(x, y) for x, y in zip(a.get('move', (0, 0, 0)), b.get('move', (0, 0, 0)))))


def designed(name):
    return pose_dict(**{k: v for k, v in C.POSES[name].items()})


def tweak(P, **kw):
    out = dict(P)
    out.update(kw)
    return out


def clips():
    stand, wave, run, sit = designed('stand'), designed('wave'), designed('run'), designed('sit')
    (wr, wl) = wave['arms']
    idle = [
        (0, stand),
        (36, tweak(stand, lean=1.2, tilt=2, arms=((5, 7, 11), (5, 7, 11)), move=(0, 0, -.008))),     # breathe in
        (66, tweak(stand, turn=-12, tilt=1, arms=((4, 6, 9), (4, 6, 9)))),                            # glance aside
        (92, tweak(stand, turn=-10, lean=.6, tilt=-1, arms=((5, 7, 10), (5, 7, 10)), move=(0, 0, -.004))),
        (120, stand),
    ]
    hand = lambda ab, el: tweak(wave, arms=((wr[0], ab, el), wl))
    wave_k = [(0, wave), (9, hand(wr[1] - 18, wr[2] + 25)), (18, wave), (27, hand(wr[1] - 18, wr[2] + 25)), (36, wave)]
    # walk: contact and passing positions, half-way to the designed run
    def stride(hr, kr, hl, kl, sw, bob):
        return pose_dict(hips=(hr, kr, hl, kl), arms=((-sw, 6, 18 + max(0, -sw) * .4), (sw, 6, 18 + max(0, sw) * .4)),
                         lean=run['lean'] * .4, tilt=0, turn=0, move=(0, 0, bob))
    walk = [
        (0, stride(22, -6, -20, -18, 18, 0)),
        (8, stride(4, -10, -6, -48, 4, .04)),
        (15, stride(-20, -18, 22, -6, -18, 0)),
        (23, stride(-6, -48, 4, -10, -4, .04)),
        (30, stride(22, -6, -20, -18, 18, 0)),
    ]
    sit_k = [(0, sit), (30, tweak(sit, lean=sit['lean'] + 1.2, tilt=2, move=(sit['move'][0], sit['move'][1], sit['move'][2] - .006))), (60, sit)]
    return {'idle': idle, 'wave': wave_k, 'walk': walk, 'sit': sit_k}


def animate(rig):
    sc = bpy.context.scene
    sc.render.fps = FPS
    rig.animation_data_create()
    for name, keys in clips().items():
        act = bpy.data.actions.new(name)
        rig.animation_data.action = act
        for frame, P in keys:
            key_pose(rig, P, frame)
        tr = rig.animation_data.nla_tracks.new()
        tr.name = name
        strip = tr.strips.new(name, int(keys[0][0]), act)
        strip.name = name
        rig.animation_data.action = None
    set_pose(rig, designed('stand'))


# ------------------------------------------------------------------ check against the house
def check(rig, body):
    """Pose "wave" and compare with character_abraham in house_P2.blend (which is the wave pose)."""
    ref = bpy.data.objects.get('character_abraham.001') or next(
        (o for o in bpy.data.objects if o.name.startswith('character_abraham') and o is not body), None)
    if ref is None:
        print('CHECK skipped: no character_abraham in the open file')
        return
    set_pose(rig, designed('wave'))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    # Distance from each rigged vertex to the house character's (bevelled) surface. Before the bevel the
    # two meshes are vertex-for-vertex identical; the bevel differs a little because the house welds the
    # whole figure and the rig welds each rigid piece on its own.
    bvh = bvhtree.BVHTree.FromObject(ref, dg)
    inv = ref.matrix_world.inverted()
    d = sorted(bvh.find_nearest(inv @ (body.matrix_world @ v.co))[3] for v in body.evaluated_get(dg).to_mesh().vertices)
    mean, p95, mx = sum(d) / len(d), d[int(.95 * len(d))], d[-1]
    print('CHECK wave vs house character_abraham: mean %.4f m, 95%% %.4f m, max %.4f m (%d verts)' % (mean, p95, mx, len(d)))
    if p95 > .002 or mx > .01:
        raise SystemExit('CHECK FAILED: the rigged character does not match the house one')
    set_pose(rig, designed('stand'))


# ------------------------------------------------------------------ run
old = bpy.data.objects.get('character_abraham')
if old:
    old.name = 'character_abraham.001'    # the house's own copy, kept only to check against
rig, body = build()
check(rig, body)   # before the clips, so no NLA track overrides the test pose
animate(rig)

# export only the rig and its mesh
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = rig
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format='GLB',
    use_selection=True,
    export_yup=True,
    export_apply=False,
    export_skins=True,
    export_animations=True,
    export_animation_mode='NLA_TRACKS',
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
    export_materials='EXPORT',
    export_cameras=False,
    export_lights=False,
    export_extras=False,
)
print('EXPORT_OK', OUT, os.path.getsize(OUT), 'bytes')

# a small .blend with just the rig, for opening in Blender
for o in list(bpy.data.objects):
    if o not in (rig, body):
        bpy.data.objects.remove(o)
bpy.ops.outliner.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'character_abraham.blend'), copy=True)
print('RIG_OK')
