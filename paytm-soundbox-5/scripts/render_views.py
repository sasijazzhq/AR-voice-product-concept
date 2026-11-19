"""Studio renders (Cycles) and orthographic silhouette masks.

    blender -b paytm-soundbox-5.blend --python scripts/render_views.py -- \
        --views front,left,right,rear,top,threequarter,hero --samples 128 --outdir renders [--variant cobalt]
    blender -b paytm-soundbox-5.blend --python scripts/render_views.py -- --masks --outdir validation/masks
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d
ROOT = os.path.dirname(bpy.data.filepath)
OUTDIR = os.path.join(ROOT, arg("--outdir", "renders"))
VIEWS = arg("--views", "front,left,right,rear,top,threequarter,hero").split(",")
SAMPLES = int(arg("--samples", "128"))
RES = arg("--res", "1600x1200")
VARIANT = arg("--variant", "cobalt")
MASKS = "--masks" in argv
SUFFIX = arg("--suffix", "")
os.makedirs(OUTDIR, exist_ok=True)

sc = bpy.context.scene
objs = [o for o in bpy.data.objects if o.type == "MESH"]
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in objs:
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
CEN = (mn + mx) / 2
RAD = (mx - mn).length / 2

if VARIANT != "cobalt":
    m = bpy.data.materials["MAT_Body_FabricBlue" if VARIANT == "fabric" else "MAT_Body_IcyWhite"]
    for o in objs:
        for i, s in enumerate(o.material_slots):
            if s.material and s.material.name == "MAT_Body_Cobalt":
                o.material_slots[i].material = m

# ------------------------------------------------------------------ studio
def studio():
    w = bpy.data.worlds.new("Studio") if "Studio" not in bpy.data.worlds else bpy.data.worlds["Studio"]
    sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground"); out = nt.nodes.new("ShaderNodeOutputWorld")
    grad = nt.nodes.new("ShaderNodeTexGradient"); grad.gradient_type = "LINEAR"
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, -math.pi / 2, 0)  # gradient along Z
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.18, 0.19, 0.2, 1); ramp.color_ramp.elements[1].color = (0.9, 0.92, 0.95, 1)
    nt.links.new(tc.outputs["Generated"], mp.inputs[0]); nt.links.new(mp.outputs[0], grad.inputs[0])
    nt.links.new(grad.outputs[0], ramp.inputs[0]); nt.links.new(ramp.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 0.12
    nt.links.new(bg.outputs[0], out.inputs[0])
    # cyclorama backdrop
    bm = bmesh.new(); prof = []
    for k in range(9): prof.append((-1.5 + k * 0.25, 0.0))
    R = 0.35
    for k in range(1, 13):
        a = math.pi / 2 * k / 12; prof.append((0.5 + R * math.sin(a), R - R * math.cos(a)))
    prof.append((0.5 + R, 1.2))
    rows = [[bm.verts.new((x, y, z)) for x in (-2.0, 2.0)] for (y, z) in prof]
    for i in range(len(rows) - 1):
        bm.faces.new((rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]))
    me = bpy.data.meshes.new("Cyclorama"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    cyc = bpy.data.objects.new("Cyclorama", me); sc.collection.objects.link(cyc)
    mat = bpy.data.materials.new("MAT_Studio_Backdrop"); mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.78, 0.8, 0.82, 1); b.inputs["Roughness"].default_value = 0.65
    b.inputs["Emission Color"].default_value = (0.86, 0.88, 0.9, 1); b.inputs["Emission Strength"].default_value = 0.22
    me.materials.append(mat)
    return cyc

def area(name, size, power, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA"); l.shape = "RECTANGLE"; l.size = size[0]; l.size_y = size[1]
    l.energy = power; l.color = color
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); return o

def aim(o, target):
    d = target - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

def place(o, az, el, dist, target):
    a, e = math.radians(az), math.radians(el)
    o.location = target + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
    aim(o, target)

cyc = None if MASKS else studio()
key = area("Key", (0.45, 0.35), 7.0); fill = area("Fill", (0.6, 0.4), 2.2, (0.95, 0.97, 1.0))
rim = area("Rim", (0.5, 0.12), 6.0); top = area("Top", (0.5, 0.5), 2.5)
bgl = area("Backdrop", (1.2, 0.6), 9.0)  # lifts the cyclorama so side views do not go grey
cam_d = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cam_d); sc.collection.objects.link(cam)
sc.camera = cam

# ------------------------------------------------------------------ render settings
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SAMPLES; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.01
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 8; sc.cycles.glossy_bounces = 4; sc.cycles.transparent_max_bounces = 4
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "Medium Contrast"; sc.view_settings.exposure = float(arg('--exposure', '-0.9'))
rx, ry = map(int, RES.split("x"))
sc.render.resolution_x, sc.render.resolution_y = rx, ry; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"

VIEWDEF = {  # azimuth (deg, 0 = front, +90 = product right / +X), elevation, focal mm, framing margin
    "front": (0, 6, 100, 0.82), "left": (-90, 4, 100, 0.8), "right": (90, 4, 100, 0.8),
    "rear": (180, 18, 100, 0.82), "top": (0, 88, 100, 0.8), "threequarter": (-38, 20, 100, 0.85),
    "hero": (-32, 14, 85, 0.95),
}

def frame_cam(az, el, focal, margin):
    cam_d.type = "PERSP"; cam_d.lens = focal; cam_d.sensor_width = 36
    fov = 2 * math.atan(18 / focal) * (min(rx, ry) / max(rx, ry) if rx >= ry else 1)
    dist = RAD * margin / math.sin(fov / 2)
    tgt = CEN.copy()
    place(cam, az, el, dist, tgt)
    cam_d.clip_start = 0.01; cam_d.clip_end = 20
    return dist, tgt

def light_rig(az):
    t = CEN
    place(key, az - 45, 35, 0.55, t); place(fill, az + 70, 15, 0.7, t)
    place(rim, az + 160, 30, 0.5, t); place(top, az, 85, 0.6, t)
    place(bgl, az, 30, 0.9, t + Vector((0, 0, 0.05)))
    bgl.rotation_euler = (Vector((math.sin(math.radians(az)), -math.cos(math.radians(az)), 0)) * -1 + Vector((0, 0, -0.35))).to_track_quat("-Z", "Y").to_euler()
    if cyc:
        cyc.rotation_euler = (0, 0, math.radians(az))  # backdrop always behind the product
        cyc.location = (0, 0, 0)

if MASKS:
    sc.render.film_transparent = True
    sc.cycles.samples = 4; sc.cycles.use_denoising = False
    for nm, (axis_view) in {"mask_right": (90, 0), "mask_front": (0, 0), "mask_rear": (180, 0)}.items():
        cam_d.type = "ORTHO"; cam_d.ortho_scale = RAD * 2.4
        place(cam, axis_view[0], axis_view[1], 1.0, CEN)
        light_rig(axis_view[0])
        sc.render.image_settings.color_mode = "RGBA"
        sc.render.filepath = os.path.join(OUTDIR, nm + ".png")
        bpy.ops.render.render(write_still=True)
    sys.exit(0)

for v in VIEWS:
    az, el, focal, margin = VIEWDEF[v]
    if v == "hero":
        sc.render.resolution_x, sc.render.resolution_y = 2400, 1600
        sc.cycles.samples = max(SAMPLES, 256)
        cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 8.0
    else:
        sc.render.resolution_x, sc.render.resolution_y = rx, ry
        cam_d.dof.use_dof = False
    dist, tgt = frame_cam(az, el, focal, margin)
    if v == "hero":
        cam_d.dof.focus_distance = dist * 0.97
    light_rig(az)
    sc.render.filepath = os.path.join(OUTDIR, f"{v}{SUFFIX}.png")
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", sc.render.filepath)
