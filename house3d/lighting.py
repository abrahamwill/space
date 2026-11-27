"""Lighting for the Space house. Run after setup_house_in_blender.py (it only changes these numbers).

Change the values below and re-run to relight; nothing else in the scene is touched.

Tuned 2026-11-20 against reference/hero_P2.png: rendered a grid of sun / ambient strengths from
HeroCamera, cropped to the house and compared pixel by pixel. Best match: sun 2.5, ambient 0.32
(mean colour error 20 vs 58 with the setup script's sun 3.0 / ambient 0.9, brightness within 2 levels).
Sun direction and softness are the setup script's (from the left-back, 52° up, 8° soft edge).
"""
import bpy

SUN_STRENGTH = 2.5   # setup script default: 3.0
AMBIENT = 0.32       # world background strength; setup script default: 0.9

scene = bpy.context.scene
scene.objects['Sun'].data.energy = SUN_STRENGTH
scene.world.node_tree.nodes['Background'].inputs[1].default_value = AMBIENT
print('Lighting set: sun', SUN_STRENGTH, 'ambient', AMBIENT)
