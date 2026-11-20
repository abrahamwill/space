"""BLENDER.md section 6: export the finished house for the website.

Run on the finished scene (house_P2.blend, built by setup -> lighting -> finish):
  blender -b house3d/house_P2.blend -P house3d/export_web.py -- public/house3d/house_P2.glb

- Apply Modifiers (keeps the bevels), Draco compression, +Y up, object names kept.
- HeroCamera is kept so the page can frame the house exactly like hero_P2.png.
- Lights are kept (Sun and the lamp-shade point lights); the page re-scales their strength.
- page_surface is kept: the page draws it as an invisible depth mask, like the holdout in Blender.
- Fabric bump, AO and soft shadows are Blender render settings and don't travel in a GLB.
"""
import os
import sys
import bpy

out = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else os.path.join(os.path.dirname(bpy.data.filepath), 'house_P2.web.glb')
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

bpy.ops.export_scene.gltf(
    filepath=out,
    export_format='GLB',
    export_apply=True,
    export_yup=True,
    export_cameras=True,
    export_lights=True,
    export_import_convert_lighting_mode='SPEC',
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
    export_materials='EXPORT',
    export_extras=False,
    export_animations=False,
)
print('EXPORT_OK', out, os.path.getsize(out), 'bytes')
