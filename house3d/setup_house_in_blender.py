"""Open the Space house (house_P2.glb) in Blender exactly as designed.

Run inside Blender (Scripting tab > Open > Run, or through the Blender MCP's "execute Python" tool).
It clears the scene, imports the GLB that sits next to this script, and sets up:
  - the HeroCamera (orthographic, azimuth 45, elevation 30) as the active camera, 1720 x 1320 output
  - one sun matching the design's light (from the left-back, 52 degrees up) and a soft grey world ambient
  - "Standard" colour management so the flat hex colours render as designed (Filmic/AgX would wash them out)
  - the page surface as a holdout: it hides everything below page level like the website rim, but renders transparent
  - each object's origin moved to its own centre, so pieces can be moved or animated later
Change GLB below if the file is somewhere else.
"""
import math
import os
import bpy
from mathutils import Vector

GLB = ""   # put the full path to house_P2.glb here if the script can't find it on its own
if not GLB or not os.path.exists(GLB):
    dirs = [os.path.dirname(os.path.abspath(globals().get("__file__", ""))), os.getcwd(),
            os.path.dirname(bpy.data.filepath) if bpy.data.filepath else ""]
    found = [os.path.join(d, "house_P2.glb") for d in dirs if d and os.path.exists(os.path.join(d, "house_P2.glb"))]
    if not found:
        raise FileNotFoundError("Set GLB at the top of this script to the full path of house_P2.glb")
    GLB = found[0]

# 1. clean scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
for block in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    for b in list(block):
        if b.users == 0:
            block.remove(b)

# 2. import the house
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
objs = {o.name: o for o in scene.objects}

# 3. camera
cam = objs.get("HeroCamera") or next(o for o in scene.objects if o.type == "CAMERA")
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = 1720, 1320
scene.render.film_transparent = True

# 4. light: design light points from scene direction (-0.616, 0, 0.788) in Blender axes
sun_data = bpy.data.lights.new("Sun", type="SUN")
sun_data.energy = 3.0
sun_data.angle = math.radians(8)          # soft shadow edge, like the design
sun = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun)
to_light = Vector((-math.cos(math.radians(52)), 0.0, math.sin(math.radians(52))))
sun.rotation_mode = "QUATERNION"
sun.rotation_quaternion = to_light.to_track_quat("Z", "Y")

world = scene.world or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.8, 0.8, 0.82, 1.0)
    bg.inputs[1].default_value = 0.9

# 5. colour management + engine
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue

# 6. page surface = holdout (invisible in renders, still hides what is below page level)
slab = objs.get("page_surface")
if slab:
    mat = bpy.data.materials.new("page_holdout")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    hold = nt.nodes.new("ShaderNodeHoldout")
    nt.links.new(hold.outputs[0], out.inputs[0])
    slab.data.materials.clear()
    slab.data.materials.append(mat)

# 7. origins to each object's own centre (geometry stays exactly where it is)
bpy.ops.object.select_all(action="DESELECT")
for o in scene.objects:
    if o.type == "MESH" and o.name != "page_surface":
        o.select_set(True)
if bpy.context.selected_objects:
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
bpy.ops.object.select_all(action="DESELECT")
print("Space house ready:", len([o for o in scene.objects if o.type == "MESH"]), "objects")
