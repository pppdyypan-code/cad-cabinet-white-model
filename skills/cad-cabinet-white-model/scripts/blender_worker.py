"""Run inside Blender. Generates only owned geometry or edits cameras on a copy."""
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_spec import geometry_key, validate

PREFIX = "WM_"
mesh_cache = {}
materials = {}
geo_collection = None


def material(name, grey):
    mat = bpy.data.materials.new(PREFIX+name)
    mat.diffuse_color = (grey, grey, grey, 1)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (grey, grey, grey, 1)
    bsdf.inputs["Roughness"].default_value = .72
    return mat


def mesh(name, verts, faces, parent=None, location=(0, 0, 0), tone="clay", bevel=.0007):
    # Link repeated mesh data, keeping each object's transform independently editable.
    verts = [tuple(round(float(v),10) for v in vertex) for vertex in verts]
    key = hashlib.sha256(repr((verts, faces, tone)).encode()).hexdigest()
    data = mesh_cache.get(key)
    if data is None:
        data = bpy.data.meshes.new(PREFIX+name)
        data.from_pydata(verts, [], faces)
        data.update()
        bm = bmesh.new(); bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(data); bm.free()
        data.materials.append(materials[tone])
        mesh_cache[key] = data
    ob = bpy.data.objects.new(PREFIX+name, data)
    geo_collection.objects.link(ob)
    ob.parent = parent
    ob.location = location
    ob["wm_component"] = parent.get("wm_component", "room") if parent else "room"
    if bevel:
        mod = ob.modifiers.new("EdgeHighlight", "BEVEL")
        mod.width = bevel; mod.segments = 2
        mod.limit_method = "ANGLE"; mod.use_clamp_overlap = True
    return ob


def box(name, low, high, parent=None, tone="clay", bevel=.0007):
    dims = [b-a for a, b in zip(low, high)]
    if min(dims) <= 0:
        raise ValueError("Non-positive box: " + name)
    x, y, z = dims
    verts = [(0,0,0),(x,0,0),(x,y,0),(0,y,0),(0,0,z),(x,0,z),(x,y,z),(0,y,z)]
    faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return mesh(name, verts, faces, parent, low, tone, bevel)


def prism(name, points, z0, z1, parent=None):
    count = len(points)
    verts = [(x,y,z) for z in (z0,z1) for x,y in points]
    faces = [tuple(range(count-1,-1,-1)), tuple(range(count,count*2))]
    faces += [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    return mesh(name, verts, faces, parent)


def cylinder(name, start, end, radius, parent, segments=16):
    a, b = Vector(start), Vector(end)
    axis = (b-a).normalized()
    u = axis.cross(Vector((0,0,1)))
    if u.length < .01:
        u = axis.cross(Vector((0,1,0)))
    u.normalize(); v = axis.cross(u)
    vertices = [tuple(c+radius*(math.cos(i*2*math.pi/segments)*u+math.sin(i*2*math.pi/segments)*v))
                for c in (a,b) for i in range(segments)]
    faces = [tuple(range(segments-1,-1,-1)), tuple(range(segments,segments*2))]
    faces += [(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
    return mesh(name, vertices, faces, parent, tone="hardware", bevel=.0003)


def handle(name, cfg, x0, x1, z0, z1, y, parent):
    style = cfg.get("style", "none")
    if style == "none":
        return
    side = cfg.get("side", "center")
    offset = min(.045, (x1-x0)*.2)
    x = x0+offset if side == "left" else x1-offset if side == "right" else (x0+x1)/2
    z = (z0+z1)/2
    if style == "knob":
        cylinder(name+"Stem", (x,y,z), (x,y+.018,z), .004, parent)
        cylinder(name+"Head", (x,y+.018,z), (x,y+.026,z), .011, parent, 24)
        return
    length = cfg.get("length_mm", 160)/1000
    if style == "f":
        if cfg.get("orientation", "vertical") != "vertical":
            raise ValueError("F handles are vertical; use bar for horizontal handles")
        # Extruded F section: a mounting spine and two distinct gripping flanges.
        points = [(x,y),(x+.004,y),(x+.004,y+.009),(x+.017,y+.009),
                  (x+.017,y+.013),(x+.004,y+.013),(x+.004,y+.022),
                  (x+.025,y+.022),(x+.025,y+.026),(x,y+.026)]
        prism(name, points, z-length/2, z+length/2, parent)
        return
    horizontal = cfg.get("orientation", "vertical") == "horizontal"
    delta = Vector((length/2,0,0) if horizontal else (0,0,length/2))
    center = Vector((x,y+.025,z))
    cylinder(name+"Grip", center-delta, center+delta, .005, parent)
    for i, sign in enumerate((-1,1)):
        point = center+sign*delta*.7
        cylinder(name+str(i), (point.x,y,point.z), point, .004, parent)


def cabinet(item, parent):
    name = item["id"]
    w,d,h = [item[k]/1000 for k in ("width_mm","depth_mm","height_mm")]
    t,dt,g = [item.get(k,v)/1000 for k,v in (("board_mm",18),("door_mm",18),("gap_mm",3))]
    inner_depth = d-dt-g
    box(name+"_SideL",(0,0,0),(t,inner_depth,h),parent)
    box(name+"_SideR",(w-t,0,0),(w,inner_depth,h),parent)
    box(name+"_Bottom",(t,0,0),(w-t,inner_depth,t),parent)
    box(name+"_Top",(t,0,h-t),(w-t,inner_depth,h),parent)
    box(name+"_Back",(t,0,t),(w-t,t,h-t),parent)
    cursor = 0
    for ci, col in enumerate(item["columns"]):
        width = col["width_mm"]/1000
        if ci:
            box(f"{name}_Divider{ci}",(cursor-t/2,t,t),(cursor+t/2,inner_depth,h-t),parent)
        z = 0
        for ri, row in enumerate(col.get("rows_mm",[item["height_mm"]])):
            rh = row/1000
            x0,x1 = cursor+g/2,cursor+width-g/2
            z0,z1 = z+g/2,z+rh-g/2
            left = dt if col.get("miter_left",False) else 0
            right = dt if col.get("miter_right",False) else 0
            points = [(x0,d),(x1,d),(x1-right,d-dt),(x0+left,d-dt)]
            prism(f"{name}_Front{ci}_{ri}",points,z0,z1,parent)
            handle(f"{name}_Handle{ci}_{ri}",col.get("handle",{}),x0,x1,z0,z1,d,parent)
            z += rh
        cursor += width
    parent["design_dimensions_mm"] = [item[k] for k in ("width_mm","depth_mm","height_mm")]


def build(project):
    global geo_collection, materials
    if bpy.data.filepath:
        raise ValueError("Build must start from a factory scene, not an existing document")
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.unit_settings.length_unit = "MILLIMETERS"
    geo_collection = bpy.data.collections.new(PREFIX+"Geometry")
    scene.collection.children.link(geo_collection)
    materials = {key:material(key,grey) for key,grey in (("clay",.68),("room",.73),("floor",.55),("hardware",.56))}
    room = project["room"]
    w,d,h,t = [room[k]/1000 for k in ("width_mm","depth_mm","height_mm","wall_mm")]
    box("room_floor",(0,0,-t),(w,d,0),tone="floor",bevel=0)
    sides = {"left":((-t,0,0),(0,d,h)),"right":((w,0,0),(w+t,d,h)),
             "front":((0,-t,0),(w,0,h)),"back":((0,d,0),(w,d+t,h)),
             "ceiling":((0,0,h),(w,d,h+t))}
    for side,(low,high) in sides.items():
        if side not in room.get("open_sides",["front"]):
            box("room_"+side,low,high,tone="room",bevel=0)
    for item in project.get("components",[]):
        parent = bpy.data.objects.new(PREFIX+item["id"], None)
        geo_collection.objects.link(parent)
        parent["wm_component"] = item["id"]
        parent.location = [x/1000 for x in item["position_mm"]]
        parent.rotation_euler.z = math.radians(item.get("rotation_deg",0))
        kind = item["kind"]
        if kind == "cabinet":
            cabinet(item,parent)
        elif kind == "prism":
            prism(item["id"]+"_Body",[(x/1000,y/1000) for x,y in item["polygon_mm"]],0,item["height_mm"]/1000,parent)
        elif kind == "box":
            box(item["id"]+"_Body",(0,0,0),tuple(item[k]/1000 for k in ("width_mm","depth_mm","height_mm")),parent)
        else:
            count,bar = item["count"],item["bar_mm"]/1000
            width,depth,height = [item[k]/1000 for k in ("width_mm","depth_mm","height_mm")]
            gap = (width-count*bar)/(count-1) if count>1 else 0
            for i in range(count):
                x=i*(bar+gap)
                box(f'{item["id"]}_Slat{i}',(x,0,0),(x+bar,depth,height),parent)
    world = bpy.data.worlds.new(PREFIX+"World")
    scene.world = world; world.use_nodes = True
    next(n for n in world.node_tree.nodes if n.type=="BACKGROUND").inputs["Strength"].default_value=.6
    data=bpy.data.lights.new(PREFIX+"Softbox","AREA"); data.energy=650; data.shape="DISK"; data.size=3
    light=bpy.data.objects.new(data.name,data); scene.collection.objects.link(light)
    light.location=(w/2,d*.4,h*.85)
    light.rotation_euler=(Vector((w/2,d*.8,h*.35))-light.location).to_track_quat('-Z','Y').to_euler()
    scene["wm_geometry_key"] = geometry_key(project)
    scene.view_settings.exposure = -.7
    bpy.context.view_layer.update()


def fingerprint():
    hash_value = hashlib.sha256()
    for ob in sorted((o for o in bpy.context.scene.objects if o.type=="MESH"),key=lambda x:x.name):
        hash_value.update(ob.name.encode())
        hash_value.update(str(tuple(round(v,9) for row in ob.matrix_world for v in row)).encode())
        for vertex in ob.data.vertices:
            hash_value.update(str(tuple(round(x,9) for x in vertex.co)).encode())
        for polygon in ob.data.polygons:
            hash_value.update(str(tuple(polygon.vertices)).encode())
    return hash_value.hexdigest()


def inspect_geometry():
    errors=[]; objects=0; triangles=0
    for ob in bpy.context.scene.objects:
        if ob.type!="MESH":
            continue
        objects+=1
        bm=bmesh.new(); bm.from_mesh(ob.data)
        if any(not e.is_manifold for e in bm.edges):
            errors.append({"object":ob.name,"problem":"open_or_nonmanifold_base_mesh"})
        if any(f.calc_area()<1e-12 for f in bm.faces):
            errors.append({"object":ob.name,"problem":"degenerate_face"})
        bm.free()
        triangles+=sum(max(0,len(p.vertices)-2) for p in ob.data.polygons)
    return {"base_mesh_objects":objects,"base_triangles":triangles,"errors":errors,
            "scope":"Base mesh topology only. CAD fidelity, intersections, normals and appearance require dimensional and visual review."}


def configure_engine(job):
    scene=bpy.context.scene
    engine=job["engine"]
    if engine=="WORKBENCH":
        scene.render.engine="BLENDER_WORKBENCH"
        shading=scene.display.shading
        shading.light="STUDIO"; shading.color_type="MATERIAL"
        shading.show_shadows=False; shading.show_cavity=True
        shading.cavity_type="BOTH"; shading.show_specular_highlight=False
        scene.display.render_aa="8"
        return "WORKBENCH"
    scene.render.engine=engine
    if engine!="CYCLES":
        return engine
    scene.cycles.samples=job["samples"]
    scene.cycles.use_denoising=True
    scene.cycles.use_adaptive_sampling=True
    scene.cycles.adaptive_threshold=.08 if job["stage"]=="preview" else .02
    scene.cycles.max_bounces=6; scene.cycles.diffuse_bounces=4
    scene.cycles.device="CPU"
    if job["device"]!="CPU":
        prefs=bpy.context.preferences.addons['cycles'].preferences
        for backend in ("OPTIX","CUDA","HIP","METAL","ONEAPI"):
            try:
                prefs.compute_device_type=backend; prefs.get_devices()
                devices=[d for d in prefs.devices if d.type==backend]
                if devices:
                    for device in prefs.devices:
                        device.use=device.type==backend
                    scene.cycles.device="GPU"
                    return "CYCLES/"+backend
            except (TypeError,RuntimeError):
                continue
    return "CYCLES/CPU"


def camera(cfg):
    name=PREFIX+"CAM_"+cfg["id"]
    old=bpy.data.objects.get(name)
    if old:
        if old.type!="CAMERA":
            raise ValueError("Camera name collides with a non-camera object: "+name)
        bpy.data.objects.remove(old,do_unlink=True)
    data=bpy.data.cameras.new(name)
    ob=bpy.data.objects.new(name,data); bpy.context.scene.collection.objects.link(ob)
    ob.location=[x/1000 for x in cfg["position_mm"]]
    target=Vector([x/1000 for x in cfg["target_mm"]])
    ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
    data.lens=cfg.get("lens_mm",28); data.sensor_width=36; data.sensor_fit="HORIZONTAL"
    data.shift_x=cfg.get("shift_x",0); data.shift_y=cfg.get("shift_y",0)
    data.clip_start=.01; data.clip_end=1000; data.dof.use_dof=False
    return ob


def projection_report(cam,cfg,project):
    scene=bpy.context.scene
    reports=[]
    for target in cfg.get("targets",[]):
        obs=[o for o in scene.objects if o.type=="MESH" and
             (o.get("wm_component")==target or o.name==target or o.name.startswith(target))]
        points=[world_to_camera_view(scene,cam,o.matrix_world@Vector(v)) for o in obs for v in o.bound_box]
        if not points:
            reports.append({"target":target,"status":"missing"}); continue
        complete=all(0<=p.x<=1 and 0<=p.y<=1 and p.z>0 for p in points)
        reports.append({"target":target,"status":"in_frame" if complete else "cropped_or_behind",
                        "bbox_uv":[round(min(p.x for p in points),3),round(min(p.y for p in points),3),
                                   round(max(p.x for p in points),3),round(max(p.y for p in points),3)]})
    warnings=[]
    if cam.data.lens<24:
        warnings.append("wide_lens: visually review edge stretch; focal length alone does not determine perspective")
    room=project.get("room",{})
    if room and not (0<=cam.location.x<=room["width_mm"]/1000 and 0<=cam.location.y<=room["depth_mm"]/1000):
        warnings.append("camera_outside_room: disclose the presentation position and check wall occlusion")
    return {"targets":reports,"warnings":warnings,"scope":"Projected bounding boxes, not an occlusion or distortion guarantee; inspect previews."}


def main():
    job=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
    project=validate(job["project"])
    scene=bpy.context.scene
    if job["stage"]=="build":
        build(project)
    elif project.get("mode","build")!="existing" and scene.get("wm_geometry_key")!=geometry_key(project):
        raise ValueError("Model parameters changed or source is not owned by this builder. Rebuild, or explicitly use mode=existing for imported models.")
    before=fingerprint()
    result={"cache_key":job["cache_key"],"source_sha256":job["source_sha256"],
            "blender_version":bpy.app.version_string,"geometry_before":before,"renders":[],
            "geometry_check_scope":"Base mesh coordinates, faces and world transforms; excludes evaluated modifier output and presentation visibility."}
    if job["stage"]=="build":
        result["qa"]=inspect_geometry()
        if result["qa"]["errors"]:
            raise ValueError("Base topology check failed: "+json.dumps(result["qa"]["errors"]))
    else:
        backend=configure_engine(job)
        # Timeline camera bindings can silently replace scene.camera at render time.
        # Clear bindings only in this output copy; keep marker names/frames intact.
        bindings=[{"name":m.name,"frame":m.frame,"camera":m.camera.name}
                  for m in scene.timeline_markers if m.camera]
        for marker in scene.timeline_markers:
            marker.camera=None
        result["cleared_camera_bindings"]=bindings
        scene.render.image_settings.file_format="PNG"
        scene.render.image_settings.color_mode="RGB"
        scene.render.resolution_percentage=100
        scene.render.use_file_extension=True
        scene.render.film_transparent=False
        scene.render.use_persistent_data=job["engine"]=="CYCLES"
        original_visibility={o.name:o.hide_render for o in scene.objects}
        for cfg in project["cameras"]:
            if cfg["id"] not in job["selected"]:
                continue
            for name,hidden in original_visibility.items():
                bpy.data.objects[name].hide_render=hidden
            for name in cfg.get("hide_objects",[]):
                if name not in bpy.data.objects:
                    raise ValueError("Unknown hide_objects name: "+name)
                bpy.data.objects[name].hide_render=True
            cam=camera(cfg); scene.camera=cam
            aspect=cfg.get("aspect",[4,3]); ratio=aspect[0]/aspect[1]
            scene.render.resolution_x=job["size"] if ratio>=1 else round(job["size"]*ratio)
            scene.render.resolution_y=round(job["size"]/ratio) if ratio>=1 else job["size"]
            bpy.context.view_layer.update()
            report=projection_report(cam,cfg,project)
            image=Path(job["out"])/(cfg["id"]+'.png')
            scene.render.filepath=str(image)
            bpy.ops.render.render(write_still=True)
            if scene.camera != cam:
                raise ValueError("Render changed the selected camera; check timeline bindings or handlers")
            if not image.is_file() or not image.stat().st_size:
                raise ValueError("Render did not write its output")
            result["renders"].append({"id":cfg["id"],"image":str(image),"height_mm":cfg["position_mm"][2],
                                      "lens_mm":cam.data.lens,"backend":backend,
                                      "hidden_objects":cfg.get("hide_objects",[]),"framing":report})
            print('@@WM@@'+json.dumps({"finished":cfg["id"]}),flush=True)
        # Each saved camera retains its presentation visibility choices as metadata.
        # The last selected view's visibility matches the saved active render.
    after=fingerprint()
    if before!=after:
        raise ValueError("Camera/render stage changed source geometry")
    result["geometry_after"]=after
    result["geometry_unchanged"]=True
    scene["wm_project_snapshot"]=json.dumps(project,ensure_ascii=False)
    scene["wm_render_manifest"]=json.dumps(result,ensure_ascii=False)
    bpy.ops.wm.save_as_mainfile(filepath=job["destination"],compress=True)
    target=Path(job["out"])/(job["stage"]+'-result.json')
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
