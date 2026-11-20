"""BLENDER.md section 4: finish on top of the design. Run after setup_house_in_blender.py and lighting.py.

Nothing is moved, resized, recoloured or remodelled. Every setting is at the top so it can be dialled
back later; re-running the whole chain (setup -> lighting -> finish) rebuilds from house_P2.glb.

  0. Cleanup   faces lying exactly on top of another are removed first (one copy kept; for a
               cream-under-glow pair the glow face is kept). Approved by Abraham 2026-11-20.
  1. Bevel     0.7 cm, 2 segments, Harden Normals, only on edges sharper than 30°.
               Skips wall_art, page_surface, and any edge touching a screen / glow face.
  2. Lights    a small warm point light inside each lamp shade (warm glow_ islands), and a faint
               self-glow on every glow_ material (screens, fans, lamp shades).
  3. Fabric    bump only, base colours untouched: bouclé on the sofa greens, corduroy on the orange
               chair, wool on the three rugs. These materials are used only by those objects.
  4. Shading   EEVEE ambient occlusion (AO only, so the tuned brightness holds) and jittered soft sun
               shadows.
"""
import math
import bmesh
import bpy
from mathutils import Vector

BEVEL_WIDTH = 0.007          # m
BEVEL_SEGMENTS = 2
BEVEL_ANGLE = math.radians(30)
BEVEL_SKIP = {'page_surface', 'wall_art'}

GLOW_STRENGTH = 0.35         # emission on glow_ materials (adds on top of their base colour)
LAMP_GLOWS = {'glow_#ffe7b0', 'glow_#ffe2a8'}   # warm lamp-shade colours
LAMP_WATTS = 12              # per point light, low on purpose
LAMP_COLOR = (1.0, 0.86, 0.62)
LAMP_MAX_SIZE = 0.8          # m: glow islands larger than this are not lamp shades
LAMP_SKIP = {'house_shell'}  # its warm glow faces are the stair's step lights, not lamp shades

FABRIC = {
    'boucle':   {'mats': ['#6f8a3a', '#5f7831'], 'objects': ['living_sofaL_Sofa']},
    'corduroy': {'mats': ['#df6a33', '#c4552a'], 'objects': ['living_chair']},
    'wool':     {'mats': ['#ede3cf', '#b5654b', '#6a655e', '#8a847a', '#ece5d6', '#5b5753'],
                 'objects': ['living_rug_check', 'bedroom_rug', 'studio_rug_blob']},
}

AO_DISTANCE = 0.6            # m
RENDER_SAMPLES = 128         # EEVEE TAA samples; jittered soft shadows need a few dozen at least

sc = bpy.context.scene


# ---------------------------------------------------------------- 1. bevel

def dedupe(ob):
    """Remove faces lying exactly on top of another face (approved by Abraham 2026-11-20).
    Same material: keep one copy, nothing visible changes. Different materials: keep the glow_ face,
    which is what the design shows (e.g. the voice puck's light-blue top over a cream face).
    Any other mix is left alone and reported."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    groups = {}
    for f in bm.faces:
        k = tuple(sorted(tuple(round(c, 4) for c in v.co) for v in f.verts))
        groups.setdefault(k, []).append(f)
    drop, unsure = [], 0
    for fs in groups.values():
        if len(fs) < 2:
            continue
        names = [me.materials[f.material_index].name for f in fs]
        if len(set(names)) == 1:
            drop += fs[1:]
        elif sum(n.startswith('glow') for n in names) == 1:
            drop += [f for f, n in zip(fs, names) if not n.startswith('glow')]
        else:
            unsure += 1
    if drop:
        bmesh.ops.delete(bm, geom=drop, context='FACES_ONLY')
        bm.to_mesh(me)
    bm.free()
    return len(drop), unsure


def weld(ob):
    """Join the glTF's split corners so faces share edges (needed to bevel and to find lamp shades).
    Same faces, same positions; refused (returns False) if it would drop any face."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    n = len(bm.faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    ok = len(bm.faces) == n
    if ok:
        bm.to_mesh(me)
        for p in me.polygons:
            p.use_smooth = False
    bm.free()
    return ok


def bevel(ob):
    me = ob.data
    glow = {i for i, m in enumerate(me.materials) if m and m.name.startswith('glow')}
    bm = bmesh.new()
    bm.from_mesh(me)
    weights = []
    for e in bm.edges:
        w = 0.0
        if len(e.link_faces) == 2 and not any(f.material_index in glow for f in e.link_faces):
            if e.calc_face_angle(0.0) > BEVEL_ANGLE:
                w = 1.0
        weights.append(w)
    bm.free()
    attr = me.attributes.get('bevel_weight_edge') or me.attributes.new('bevel_weight_edge', 'FLOAT', 'EDGE')
    attr.data.foreach_set('value', weights)
    mod = ob.modifiers.new('Bevel', 'BEVEL')
    mod.width = BEVEL_WIDTH
    mod.segments = BEVEL_SEGMENTS
    mod.limit_method = 'WEIGHT'
    mod.harden_normals = True
    mod.use_clamp_overlap = True
    return int(sum(weights))


# ---------------------------------------------------------------- 2. lights

def glow_materials():
    for m in bpy.data.materials:
        if m.name.startswith('glow') and m.node_tree:
            bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf:
                bsdf.inputs['Emission Color'].default_value = bsdf.inputs['Base Color'].default_value
                bsdf.inputs['Emission Strength'].default_value = GLOW_STRENGTH


def lamp_islands(ob):
    """World-space centre and size of each connected patch of warm glow faces."""
    me = ob.data
    lamp = {i for i, m in enumerate(me.materials) if m and m.name in LAMP_GLOWS}
    if not lamp:
        return []
    bm = bmesh.new()
    bm.from_mesh(me)
    faces = {f for f in bm.faces if f.material_index in lamp}
    out = []
    while faces:
        seed = faces.pop()
        island, stack = [seed], [seed]
        while stack:
            f = stack.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in faces:
                        faces.remove(g)
                        island.append(g)
                        stack.append(g)
        pts = [ob.matrix_world @ v.co for f in island for v in f.verts]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        out.append(((lo + hi) / 2, max(hi - lo)))
    bm.free()
    return out


def add_lamps():
    n = 0
    for ob in list(sc.objects):
        if ob.type != 'MESH' or ob.name in BEVEL_SKIP or ob.name in LAMP_SKIP:
            continue
        for centre, size in lamp_islands(ob):
            if size > LAMP_MAX_SIZE:
                continue
            L = bpy.data.lights.new('lamp:' + ob.name, 'POINT')
            L.energy = LAMP_WATTS
            L.color = LAMP_COLOR
            L.shadow_soft_size = max(0.03, size * 0.25)
            o = bpy.data.objects.new('lamp:%s:%d' % (ob.name, n), L)
            o.location = centre
            sc.collection.objects.link(o)
            n += 1
    return n


# ---------------------------------------------------------------- 3. fabric

def fabric(kind, mat):
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    bump = nt.nodes.new('ShaderNodeBump')
    if kind == 'boucle':      # small looped nubs
        tex = nt.nodes.new('ShaderNodeTexVoronoi')
        tex.feature = 'SMOOTH_F1'
        tex.inputs['Scale'].default_value = 160
        nt.links.new(coord.outputs['Object'], tex.inputs['Vector'])
        nt.links.new(tex.outputs['Distance'], bump.inputs['Height'])
        bump.inputs['Strength'].default_value = 0.35
        bump.inputs['Distance'].default_value = 0.002
        bsdf.inputs['Roughness'].default_value = 1.0
    elif kind == 'corduroy':  # ribs about 6 mm apart
        tex = nt.nodes.new('ShaderNodeTexWave')
        tex.wave_type = 'BANDS'
        tex.bands_direction = 'Z'
        tex.inputs['Scale'].default_value = 170
        tex.inputs['Distortion'].default_value = 0.3
        nt.links.new(coord.outputs['Object'], tex.inputs['Vector'])
        nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
        bump.inputs['Strength'].default_value = 0.4
        bump.inputs['Distance'].default_value = 0.002
        bsdf.inputs['Roughness'].default_value = 0.9
    else:                     # wool: soft fibrous noise
        tex = nt.nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = 220
        tex.inputs['Detail'].default_value = 8
        tex.inputs['Roughness'].default_value = 0.7
        nt.links.new(coord.outputs['Object'], tex.inputs['Vector'])
        nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
        bump.inputs['Strength'].default_value = 0.25
        bump.inputs['Distance'].default_value = 0.003
        bsdf.inputs['Roughness'].default_value = 1.0
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])


def apply_fabrics():
    done = []
    for kind, spec in FABRIC.items():
        for name in spec['mats']:
            m = bpy.data.materials.get(name)
            if not m:
                continue
            users = [o.name for o in sc.objects if o.type == 'MESH' and m.name in [x.name for x in o.data.materials if x]]
            if set(users) - set(spec['objects']):
                print('SKIP fabric on', name, '- also used by', users)
                continue
            fabric(kind, m)
            done.append(name)
    return done


# ---------------------------------------------------------------- 4. shading

def shading():
    e = sc.eevee
    e.use_fast_gi = True
    try:
        e.fast_gi_method = 'AMBIENT_OCCLUSION_ONLY'
    except TypeError:
        pass
    e.fast_gi_distance = AO_DISTANCE
    e.use_shadows = True
    e.shadow_pool_size = '1024'
    e.taa_render_samples = RENDER_SAMPLES
    sun = sc.objects['Sun'].data
    sun.use_shadow = True
    sun.use_shadow_jitter = True


# ---------------------------------------------------------------- run

edges, unwelded = 0, []
for ob in sc.objects:
    if ob.type != 'MESH' or ob.name == 'page_surface' or any(m.type == 'BEVEL' for m in ob.modifiers):
        continue
    dropped, unsure = dedupe(ob)
    if dropped or unsure:
        print('DEDUPE %s: removed %d overlapping faces, left %d unclear overlaps' % (ob.name, dropped, unsure))
    if not weld(ob):
        unwelded.append(ob.name)  # overlapping faces: leave it exactly as imported
        continue
    if ob.name not in BEVEL_SKIP:
        edges += bevel(ob)
glow_materials()
lamps = add_lamps()
fabrics = apply_fabrics()
shading()
print('FINISH_OK bevelled edges %d, lamp lights %d, fabric materials %s' % (edges, lamps, fabrics))
print('FINISH_SKIPPED (overlapping faces, not welded or bevelled):', unwelded)
