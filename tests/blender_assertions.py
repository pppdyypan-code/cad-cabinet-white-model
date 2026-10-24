"""Run on the synthetic example model using Blender -b model.blend -P this.py."""
import math
import bpy
from mathutils import Vector

wardrobe=bpy.data.objects['WM_Wardrobe']
assert list(wardrobe['design_dimensions_mm'])==[1800,560,2360]
assert (wardrobe.location-Vector((2.4,3.5,0))).length<1e-6
assert abs(wardrobe.rotation_euler.z-math.pi)<1e-6
fronts=[o for o in bpy.data.objects if o.name.startswith('WM_Wardrobe_Front')]
assert len(fronts)==3
drawers=[o for o in bpy.data.objects if o.name.startswith('WM_Chest_Front')]
assert len(drawers)==4
assert all(abs((max(v.co.z for v in o.data.vertices)-min(v.co.z for v in o.data.vertices))-.247)<1e-6 for o in drawers)
slats=[o for o in bpy.data.objects if o.name.startswith('WM_Slats_Slat')]
assert len(slats)==10 and len({o.data.as_pointer() for o in slats})==1
mitre=bpy.data.objects['WM_Upper_Front1_0']
ys=sorted({round(v.co.y,6) for v in mitre.data.vertices})
assert abs(ys[-1]-ys[0]-.018)<1e-6
assert abs(max(v.co.x for v in mitre.data.vertices if abs(v.co.y-ys[-1])<1e-6)-max(v.co.x for v in mitre.data.vertices if abs(v.co.y-ys[0])<1e-6)-.018)<1e-6
print('@@ASSERTIONS@@ dimensional, door count, drawer count, mesh reuse and 45-degree miter checks passed',flush=True)
