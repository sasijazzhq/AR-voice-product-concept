"""Procedural, fully editable Blender model of the Soundbox 5.0 industrial design.

Run (Blender 4.2 LTS):
    blender -b --factory-startup --python scripts/build_soundbox.py -- --lod hero --out paytm-soundbox-5.blend
    blender -b --factory-startup --python scripts/build_soundbox.py -- --lod ar   --out build/ar.blend

Conventions
  * metres, Blender Z-up, product front faces -Y  (glTF export: +Y up, front faces +Z)
  * origin = centre of the flat ground-contact footprint (z = 0)
  * every surface gets analytic custom normals -> no shading artefacts on the low-poly AR LOD

Geometry is driven by scripts/params.json (fitted to the PencilProto orthographic renders).
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
P = json.load(open(os.path.join(HERE, "params.json")))

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default
LOD = arg("--lod", "hero")
OUT = os.path.join(ROOT, arg("--out", "paytm-soundbox-5.blend"))

Q = {  # tessellation per level of detail
    "hero": dict(seg90=28, fillet=14, fp_corner=20, fp_round=8, slot_end=8, button=40, led=16, tex=2048),
    "ar":   dict(seg90=14, fillet=8, fp_corner=12, fp_round=4, slot_end=4, button=20, led=8, tex=1024),
}[LOD]

MM = 0.001
H = P["H"]

# ----------------------------------------------------------------------------- utils
def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def hexcol(h, a=1.0):
    h = h.lstrip("#")
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (a,)

COL = {k: hexcol(v) for k, v in P["colours_srgb"].items()}

def fillet(Vp, Vc, Vn, r, seg90):
    """Arc points (pos, normal) rounding corner Vc between Vp and Vn with radius r (2D)."""
    u1 = (Vp - Vc).normalized(); u2 = (Vn - Vc).normalized()
    ang = math.acos(max(-1, min(1, u1.dot(u2))))
    half = ang / 2
    t = r / math.tan(half)
    bis = (u1 + u2).normalized()
    C = Vc + bis * (r / math.sin(half))
    T1 = Vc + u1 * t; T2 = Vc + u2 * t
    a1 = math.atan2(T1.y - C.y, T1.x - C.x); a2 = math.atan2(T2.y - C.y, T2.x - C.x)
    da = a2 - a1
    while da > math.pi: da -= 2 * math.pi
    while da < -math.pi: da += 2 * math.pi
    n = max(2, math.ceil(abs(da) / (math.pi / 2) * seg90))
    pts = []
    for i in range(n + 1):
        a = a1 + da * i / n
        d = Vector((math.cos(a), math.sin(a)))
        pts.append((C + d * r, d.copy()))
    return pts

def line_y(z, L):  # profile lines are expressed as y = slope*z + y0 (units of mm)
    return L[0] * z + L[1]

def intersect(L1, L2):
    z = (L2[1] - L1[1]) / (L1[0] - L2[0])
    return Vector((line_y(z, L1), z))

def set_custom_normals(me, loop_normals):
    me.shade_smooth() if hasattr(me, "shade_smooth") else None
    for p in me.polygons: p.use_smooth = True
    me.normals_split_custom_set(loop_normals)

def new_obj(name, me, parent=None, coll=None):
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    if parent: ob.parent = parent
    return ob

# ----------------------------------------------------------------------------- side profile
pr = P["profile_units_H"]
t_fp = P["faceplate"]["thickness"]
Lf_out = (pr["front_outer_line"]["slope_dy_dz"], pr["front_outer_line"]["y0"] * H)
nrm = math.hypot(Lf_out[0], 1.0)
n_front = Vector((-1.0, Lf_out[0])) / nrm         # outward normal of front plane (y,z)
d_front = Vector((Lf_out[0], 1.0)) / nrm          # up-slope direction of front plane
p_in = Vector((Lf_out[1], 0.0)) - n_front * t_fp  # body front plane sits under the faceplate
Lf_in = (Lf_out[0], p_in.x - Lf_out[0] * p_in.y)
L_rear = (pr["rear_slope_line"]["slope_dy_dz"], pr["rear_slope_line"]["y0"] * H)
L_under = (pr["undercut_line"]["slope_dy_dz"], pr["undercut_line"]["y0"] * H)
Y_BACK = pr["back_y"] * H

corners = [  # (point, radius) clockwise in (y=depth, z=height)
    (Vector((L_under[1], 0.0)), pr["r_undercut_bottom"] * H),
    (intersect(L_under, Lf_in), pr["r_nose"] * H),
    (intersect(Lf_in, L_rear), pr["r_apex"] * H),
    (Vector((Y_BACK, (Y_BACK - L_rear[1]) / L_rear[0])), pr["r_rear"] * H),
    (Vector((Y_BACK, 0.0)), pr["r_back_bottom"] * H),
]
profile = []      # list of (pos2d, normal2d)
arc_tangents = []
for i, (V, r) in enumerate(corners):
    Vp = corners[i - 1][0]; Vn = corners[(i + 1) % len(corners)][0]
    arc = fillet(Vp, V, Vn, r, Q["seg90"])
    arc_tangents.append((arc[0][0], arc[-1][0]))
    profile += arc
assert P["side_fillet"] < min(r for _, r in corners), "profile radii must exceed the side fillet"

# footprint centre -> world origin
y_foot0 = arc_tangents[0][1].x if False else None
bottom_front = arc_tangents[0][0]   # tangent of undercut-bottom arc on the bottom line
bottom_back = arc_tangents[4][1]
Y_C = 0.5 * (bottom_front.x + bottom_back.x)

def W3(y, z, x=0.0):
    """profile (y depth, z height) + width x (mm) -> world Vector (m)."""
    return Vector((x * MM, (y - Y_C) * MM, z * MM))

# ----------------------------------------------------------------------------- materials
def principled(name, base, rough=0.5, metal=0.0, coat=0.0, coat_rough=0.05, emission=None, estr=0.0,
               tex=None, spec=0.5):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (400, 0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.location = (100, 0)
    nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs["Base Color"].default_value = base
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = coat_rough
    if emission and emission != "tex":
        b.inputs["Emission Color"].default_value = emission
        b.inputs["Emission Strength"].default_value = estr
    if tex:
        im = bpy.data.images.load(os.path.join(ROOT, "textures", tex), check_existing=True)
        it = nt.nodes.new("ShaderNodeTexImage"); it.location = (-300, 0); it.image = im
        it.interpolation = "Linear"
        nt.links.new(it.outputs["Color"], b.inputs["Base Color"])
        if emission == "tex":
            nt.links.new(it.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = estr
    m.diffuse_color = base
    return m

MAT = {
    "body": principled("MAT_Body_Cobalt", COL["cobalt_body"], rough=0.38, spec=0.5, coat=0.15, coat_rough=0.3),
    "body_fabric": principled("MAT_Body_FabricBlue", COL["fabric_blue_body"], rough=0.38, coat=0.15, coat_rough=0.3),
    "body_white": principled("MAT_Body_IcyWhite", COL["icy_white_body"], rough=0.36, coat=0.15, coat_rough=0.3),
    "plate": principled("MAT_Faceplate_MetallicPaint", COL["bezel_silver"], rough=0.34, metal=0.5, coat=0.5, coat_rough=0.12),
    "sticker": principled("MAT_QR_Print", (1, 1, 1, 1), rough=0.28, coat=0.5, coat_rough=0.1,
                          tex=f"qr_sticker_{Q['tex']}.png"),
    "slot": principled("MAT_Speaker_Mesh", hexcol("#141518"), rough=0.75),
    "buttons": principled("MAT_Buttons", (1, 1, 1, 1), rough=0.42, coat=0.3, coat_rough=0.15, tex="button_icons_512.png"),
    "lcd": principled("MAT_LCD", (1, 1, 1, 1), rough=0.12, coat=1.0, coat_rough=0.02, emission="tex", estr=0.25,
                      tex="lcd_screen_512.png"),
    "led": principled("MAT_LED_Green", hexcol("#2be36a"), rough=0.15, emission=hexcol("#2bff6e"), estr=6.0),
    "contacts": principled("MAT_Contacts_Metal", hexcol("#b9bcc0"), rough=0.32, metal=1.0),
}
# body colour variants are kept on the master file and exported as KHR_materials_variants
for m in (MAT["body_fabric"], MAT["body_white"]):
    m.use_fake_user = True

# ----------------------------------------------------------------------------- scene reset
for c in list(bpy.data.collections): bpy.data.collections.remove(c)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"; scene.unit_settings.scale_length = 1.0
scene.unit_settings.length_unit = "MILLIMETERS"
coll = bpy.data.collections.new("Paytm_Soundbox_5"); scene.collection.children.link(coll)

anchor = bpy.data.objects.new("Ground_Anchor", None)
anchor.empty_display_type = "ARROWS"; anchor.empty_display_size = 0.02
coll.objects.link(anchor)
anchor["description"] = "Root at ground-contact point (footprint centre, z=0). Place this on the AR hit-test pose."

# ----------------------------------------------------------------------------- slots (shared)
sp = P["speaker_slots"]
def slot_loop(cy, cz, n_end):
    """capsule outline in profile plane, CCW, returns list of Vector2."""
    L = sp["length_H"] * H; Wd = sp["width_H"] * H; r = Wd / 2
    a = math.radians(sp["angle_deg"])
    u = Vector((math.cos(a), math.sin(a))); v = Vector((-u.y, u.x))
    c = Vector((cy, cz)); hl = L / 2 - r
    pts = []
    for k in range(n_end + 1):  # end cap at +u
        t = -math.pi / 2 + math.pi * k / n_end
        pts.append(c + u * (hl + r * math.cos(t)) + v * (r * math.sin(t)))
    for k in range(n_end + 1):  # end cap at -u
        t = math.pi / 2 + math.pi * k / n_end
        pts.append(c + u * (-hl + r * math.cos(t)) + v * (r * math.sin(t)))
    return pts
SLOTS = [slot_loop(y * H, z * H, Q["slot_end"]) for y, z in sp["centres_H"]]

# ----------------------------------------------------------------------------- Soundbox_Body
def build_body():
    W2 = P["body_width"] / 2; rs = P["side_fillet"]
    m = Q["fillet"]
    angles = [math.pi / 2 * j / m for j in range(m + 1)]
    cols = [(-1, a) for a in reversed(angles)] + [(1, a) for a in angles]
    bm = bmesh.new()
    vnorm = {}
    grid = []
    for (p, n) in profile:
        row = []
        for s, a in cols:
            x = s * (W2 - rs + rs * math.sin(a))
            q = p - n * (rs * (1 - math.cos(a)))
            v = bm.verts.new(W3(q.x, q.y, x))
            vnorm[v] = Vector((s * math.sin(a), n.x * math.cos(a), n.y * math.cos(a))).normalized()
            row.append(v)
        grid.append(row)
    N = len(grid); C = len(cols)
    for i in range(N):
        for j in range(C - 1):
            if cols[j][0] != cols[j + 1][0] and False: pass
            a, b_, c, d = grid[i][j], grid[i][j + 1], grid[(i + 1) % N][j + 1], grid[(i + 1) % N][j]
            f = bm.faces.new((a, b_, c, d))
    bm.normal_update()
    # orient outward using analytic normals
    for f in bm.faces:
        avg = sum((vnorm[v] for v in f.verts), Vector())
        if f.normal.dot(avg) < 0: f.normal_flip()
    # side caps with speaker slot holes
    slot_rings = {}
    for s, jcap in ((-1, 0), (1, C - 1)):
        edges = []
        for i in range(N):
            e = bm.edges.get((grid[i][jcap], grid[(i + 1) % N][jcap]))
            edges.append(e)
        rings = []
        for loop in SLOTS:
            vs = [bm.verts.new(W3(pt.x, pt.y, s * W2)) for pt in loop]
            for v in vs: vnorm[v] = Vector((s, 0, 0))
            for k in range(len(vs)):
                edges.append(bm.edges.new((vs[k], vs[(k + 1) % len(vs)])))
            rings.append(vs)
        slot_rings[s] = rings
        res = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges, normal=Vector((s, 0, 0)))
        for f in res["geom"]:
            if isinstance(f, bmesh.types.BMFace) and f.normal.x * s < 0: f.normal_flip()
    me = bpy.data.meshes.new("Soundbox_Body")
    bm.to_mesh(me)
    # loop normals: analytic per vertex (cap faces get +-X)
    co_norm = {tuple(round(c, 7) for c in v.co): vnorm[v] for v in bm.verts}
    slot_info = {s: [[v.co.copy() for v in ring] for ring in rings] for s, rings in slot_rings.items()}
    bm.free()
    me.materials.append(MAT["body"])
    ln = []
    for l in me.loops:
        co = me.vertices[l.vertex_index].co
        ln.append(co_norm[tuple(round(c, 7) for c in co)])
    set_custom_normals(me, ln)
    ob = new_obj("Soundbox_Body", me, anchor, coll)
    return ob, slot_info

body, slot_info = build_body()

# ----------------------------------------------------------------------------- Speaker_Region
def build_speaker():
    depth = sp["depth"] * MM
    bm = bmesh.new(); uvs = []
    floor_faces, wall_faces = [], []
    for s, rings in slot_info.items():
        for ring in rings:
            top = [bm.verts.new(c) for c in ring]
            bot = [bm.verts.new(c - Vector((s * depth, 0, 0))) for c in ring]
            n = len(top)
            for k in range(n):
                a, b_, c, d = top[k], top[(k + 1) % n], bot[(k + 1) % n], bot[k]
                f = bm.faces.new((a, d, c, b_) if s > 0 else (a, b_, c, d))
                wall_faces.append(f)
            f = bm.faces.new(bot if s < 0 else list(reversed(bot)))
            floor_faces.append(f)
    bm.normal_update()
    for f in wall_faces:  # walls must face into the hole (towards slot centre)
        cen = sum((v.co for v in f.verts), Vector()) / 4
        # centre of the slot this face belongs to: approximate with face normal sign check vs x-axis free direction
    bmesh.ops.recalc_face_normals(bm, faces=floor_faces)
    for f in floor_faces:
        s = 1 if f.verts[0].co.x > 0 else -1
        if f.normal.x * s < 0: f.normal_flip()
    for f in wall_faces: f.material_index = 0
    for f in floor_faces: f.material_index = 1
    me = bpy.data.meshes.new("Speaker_Region"); bm.to_mesh(me); bm.free()
    # flip walls so they face the slot axis (inside of the hole)
    me.materials.append(MAT["body"]); me.materials.append(MAT["slot"])
    for p in me.polygons:
        if p.material_index == 0:
            cx = p.center
            # slot centre for this wall = nearest floor centre
    ob = new_obj("Speaker_Region", me, anchor, coll)
    for p in me.polygons: p.use_smooth = False
    return ob

speaker = build_speaker()

# ----------------------------------------------------------------------------- Front_Faceplate + QR_Panel
fp = P["faceplate"]
# The faceplate runs up to the front/rear-slope intersection (reference: frame top meets the rear slope);
# the body's apex fillet sits just behind its top edge.
v_top_world = corners[2][0] if fp.get("top_at") == "apex_vertex" else arc_tangents[2][0]
FP_ORIGIN = v_top_world - d_front * fp["length"]   # bottom back edge centre

def fp_to_world(u, v, w):
    p = FP_ORIGIN + d_front * v + n_front * w
    return W3(p.x, p.y, u)

def fp_dir(nu, nv, nw):
    d = d_front * nv + n_front * nw
    return Vector((nu, d.x, d.y)).normalized()

def rounded_rect(Wd, Ht, R, nseg, v0=0.0):
    """outline (pos2d (u,v), outward normal2d) CCW, rect centred in u, v from v0..v0+Ht."""
    out = []
    cs = [(Wd / 2 - R, v0 + Ht - R, 0), (-Wd / 2 + R, v0 + Ht - R, 90), (-Wd / 2 + R, v0 + R, 180), (Wd / 2 - R, v0 + R, 270)]
    for cx, cy, a0 in cs:
        for k in range(nseg + 1):
            a = math.radians(a0 + 90 * k / nseg)
            n = Vector((math.cos(a), math.sin(a)))
            out.append((Vector((cx, cy)) + n * R, n))
    return out

def build_faceplate():
    Wd, Lg, R = fp["width"], fp["length"], fp["corner_radius"]
    t, re, rim, pd = fp["thickness"], fp["edge_radius"], fp["rim_width"], fp["pocket_depth"]
    rb, ri = 0.6, 0.45
    outline = rounded_rect(Wd, Lg, R, Q["fp_corner"])
    # cross-section: (e = outward offset, w = height, ne, nw normal)
    cs = []
    for k in range(Q["fp_round"] + 1):          # back edge round
        a = -math.pi / 2 + (math.pi / 2) * k / Q["fp_round"]
        cs.append((-rb + rb * math.cos(a), rb + rb * math.sin(a), math.cos(a), math.sin(a)))
    for k in range(Q["fp_round"] * 2 + 1):      # front outer round (bigger)
        a = (math.pi / 2) * k / (Q["fp_round"] * 2)
        cs.append((-re + re * math.cos(a), t - re + re * math.sin(a), math.cos(a), math.sin(a)))
    for k in range(Q["fp_round"] + 1):          # inner lip round into pocket
        a = math.pi / 2 + (math.pi / 2) * k / Q["fp_round"]
        cs.append((-(rim - ri) + ri * math.cos(a), t - ri + ri * math.sin(a), math.cos(a), math.sin(a)))
    cs.append((-rim, t - pd, -1.0, 0.0))        # pocket wall bottom
    bm = bmesh.new(); vn = {}
    rings = []
    for (e, w, ne, nw) in cs:
        ring = []
        for (o, m) in outline:
            p2 = o + m * e
            v = bm.verts.new(fp_to_world(p2.x, p2.y, w))
            vn[v] = fp_dir(m.x * ne, m.y * ne, nw)
            ring.append(v)
        rings.append(ring)
    n = len(outline)
    for i in range(len(rings) - 1):
        for k in range(n):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]))
    # pocket floor (sticker bed) and back face caps
    floor = []
    for (o, m) in outline:
        p2 = o - m * rim
        v = bm.verts.new(fp_to_world(p2.x, p2.y, t - pd)); vn[v] = fp_dir(0, 0, 1); floor.append(v)
    for k in range(n):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % n], floor[(k + 1) % n], floor[k]))
    # floor cap: duplicate ring with face normal +w
    ff = bm.faces.new(floor)
    back = rings[0]
    bf = bm.faces.new(list(reversed(back)))
    bm.normal_update()
    for f in bm.faces:
        avg = sum((vn[v] for v in f.verts), Vector())
        if f.normal.dot(avg) < 0: f.normal_flip()
    bmesh.ops.triangulate(bm, faces=[ff, bf], quad_method="BEAUTY", ngon_method="BEAUTY")
    me = bpy.data.meshes.new("Front_Faceplate"); bm.to_mesh(me)
    co_n = {tuple(round(c, 7) for c in v.co): vn[v] for v in bm.verts}
    bm.free()
    ln = []
    back_n = fp_dir(0, 0, -1); floor_n = fp_dir(0, 0, 1)
    for p in me.polygons:
        flat = abs(p.normal.dot(back_n)) > 0.9999 and p.loop_total == 3
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if flat:
                ln.append(back_n if p.normal.dot(back_n) > 0 else floor_n)
            else:
                ln.append(co_n[tuple(round(c, 7) for c in co)])
    me.materials.append(MAT["plate"])
    set_custom_normals(me, ln)
    return new_obj("Front_Faceplate", me, anchor, coll)

faceplate = build_faceplate()

def build_sticker():
    st = P["sticker"]
    Wd, Ht, R, th = st["width"], st["height"], st["corner_radius"], st["thickness"]
    v0 = (fp["length"] - Ht) / 2
    w0 = fp["thickness"] - fp["pocket_depth"]
    outline = rounded_rect(Wd, Ht, R, Q["fp_corner"], v0)
    bm = bmesh.new(); uv_l = bm.loops.layers.uv.new("UVMap")
    top = [bm.verts.new(fp_to_world(o.x, o.y, w0 + th)) for o, _ in outline]
    bot = [bm.verts.new(fp_to_world(o.x, o.y, w0 + 0.02)) for o, _ in outline]
    n = len(outline)
    ft = bm.faces.new(top)
    sides = [bm.faces.new((bot[k], bot[(k + 1) % n], top[(k + 1) % n], top[k])) for k in range(n)]
    def uvof(o):
        return ((o.x + Wd / 2) / Wd, (o.y - v0) / Ht)
    tris = bmesh.ops.triangulate(bm, faces=[ft], quad_method="BEAUTY", ngon_method="BEAUTY")["faces"]
    bm.normal_update()
    for f in tris:
        if f.normal.dot(fp_dir(0, 0, 1)) < 0: f.normal_flip()
    lookup = {v: outline[i][0] for i, v in enumerate(top)}
    lookup.update({v: outline[i][0] for i, v in enumerate(bot)})
    for f in bm.faces:
        for l in f.loops:
            l[uv_l].uv = uvof(lookup[l.vert])
    me = bpy.data.meshes.new("QR_Panel"); bm.to_mesh(me); bm.free()
    me.materials.append(MAT["sticker"])
    ln = []
    up = fp_dir(0, 0, 1)
    for p in me.polygons:
        for li in p.loop_indices:
            ln.append(up if p.loop_total == 3 else p.normal.copy())
    set_custom_normals(me, ln)
    ob = new_obj("QR_Panel", me, faceplate, coll)
    ob["qr_payload"] = "PAYTM REALITY LAB DEMO - NOT A PAYMENT CODE"
    ob["payable"] = False
    return ob

qr_panel = build_sticker()

# ----------------------------------------------------------------------------- rear slope frame
n_rear = Vector((1.0, -L_rear[0]))  # outward normal of rear slope in (y,z): y = a z + b -> (1, -a)
n_rear = Vector((-n_rear.x, -n_rear.y)) if n_rear.y < 0 else n_rear
n_rear = n_rear.normalized()
d_rear_up = Vector((n_rear.y, -n_rear.x))
if d_rear_up.y < 0: d_rear_up = -d_rear_up   # pointing up-slope (towards apex)

def rear_frame(z_mm):
    p = Vector((line_y(z_mm, L_rear), z_mm))
    origin = W3(p.x, p.y)
    nz = Vector((0, n_rear.x, n_rear.y)); up = Vector((0, d_rear_up.x, d_rear_up.y))
    xa = Vector((-1, 0, 0))   # viewed from the rear, +right of the viewer is world -X
    return origin, xa, up, nz

def revolve(profile_rh, segments, frame, name, mat, uv_cell=None, sink=0.0):
    """Lathe a (radius, height, nr, nh) profile around the frame normal. Last point must be on axis."""
    origin, xa, ya, za = frame
    bm = bmesh.new(); uv_l = bm.loops.layers.uv.new("UVMap"); vn = {}
    rings = []
    for (r, h, nr, nh) in profile_rh[:-1]:
        ring = []
        for k in range(segments):
            a = 2 * math.pi * k / segments
            radial = xa * math.cos(a) + ya * math.sin(a)
            v = bm.verts.new(origin + (radial * r + za * (h - sink)) * MM)
            vn[v] = (radial * nr + za * nh).normalized(); ring.append(v)
        rings.append(ring)
    r, h, nr, nh = profile_rh[-1]
    tip = bm.verts.new(origin + za * (h - sink) * MM); vn[tip] = za.copy()
    for i in range(len(rings) - 1):
        for k in range(segments):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % segments], rings[i + 1][(k + 1) % segments], rings[i + 1][k]))
    for k in range(segments):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % segments], tip))
    bm.normal_update()
    for f in bm.faces:
        avg = sum((vn[v] for v in f.verts), Vector())
        if f.normal.dot(avg) < 0: f.normal_flip()
    if uv_cell is not None:
        rmax = max(p[0] for p in profile_rh)
        u0, v0, cw, ch = uv_cell
        for f in bm.faces:
            for l in f.loops:
                d = l.vert.co - origin
                x = d.dot(xa) / (rmax * MM); y = d.dot(ya) / (rmax * MM)
                l[uv_l].uv = (u0 + (x * 0.5 + 0.5) * cw, v0 + (y * 0.5 + 0.5) * ch)
    if uv_cell is None:
        bm.loops.layers.uv.remove(uv_l)          # untextured: do not export an unused TEXCOORD_0
    me = bpy.data.meshes.new(name); bm.to_mesh(me)
    co_n = {tuple(round(c, 7) for c in v.co): vn[v] for v in bm.verts}
    bm.free()
    me.materials.append(mat)
    set_custom_normals(me, [co_n[tuple(round(c, 7) for c in me.vertices[l.vertex_index].co)] for l in me.loops])
    return me

# ----------------------------------------------------------------------------- Top_Controls
ct = P["controls"]
controls = bpy.data.objects.new("Top_Controls", None); coll.objects.link(controls); controls.parent = anchor
controls.empty_display_size = 0.01
def button_profile(R, Hb, seg):
    pts = [(R, 0.0, 1, 0), (R, Hb - 0.9, 1, 0)]
    for k in range(1, seg + 1):              # rounded shoulder
        a = (math.pi / 2) * k / seg
        pts.append((R - 0.9 + 0.9 * math.cos(a), Hb - 0.9 + 0.9 * math.sin(a), math.cos(a), math.sin(a)))
    rr = R - 0.9
    for k in range(1, seg + 1):              # gentle dome on top
        f = 1 - k / seg
        pts.append((rr * f, Hb + 0.25 * (1 - f * f), 0.12 * f, 1.0))
    return pts
names = ["Button_VolumeUp", "Button_VolumeDown", "Button_Repeat", "Button_Power"]
frame = rear_frame(ct["row_z_H"] * H)
for i, nm in enumerate(names):
    off = (i - 1.5) * ct["button_pitch"]
    o, xa, ya, za = frame
    fr = (o + xa * off * MM, xa, ya, za)
    cell = (i * 0.25 + 0.02, 1 - 0.25 + 0.02, 0.21, 0.21)   # atlas row 0 is the top strip of the image
    me = revolve(button_profile(ct["button_diameter"] / 2, ct["button_height"], max(3, Q["button"] // 8)),
                 Q["button"], fr, nm, MAT["buttons"], uv_cell=cell, sink=0.4)
    ob = new_obj(nm, me, controls, coll)
    ob["function"] = ["volume_up", "volume_down", "repeat_last_announcement", "power"][i]

# ----------------------------------------------------------------------------- Status_Indicator
status = bpy.data.objects.new("Status_Indicator", None); coll.objects.link(status); status.parent = anchor
status.empty_display_size = 0.01
for i, x in enumerate(ct["led_x"]):
    o, xa, ya, za = rear_frame(ct["led_z_H"] * H)
    fr = (o + Vector((x * MM, 0, 0)), xa, ya, za)
    rr = ct["led_diameter"] / 2
    seg = Q["led"] // 4
    prof = [(rr, 0.0, 1, 0)] + [(rr * math.cos(math.pi / 2 * k / seg), 0.55 * math.sin(math.pi / 2 * k / seg),
                                 math.cos(math.pi / 2 * k / seg), math.sin(math.pi / 2 * k / seg)) for k in range(seg + 1)]
    prof[-1] = (0.0, 0.55, 0, 1)
    me = revolve(prof, Q["led"], fr, f"Status_LED_{i + 1}", MAT["led"], sink=0.2)
    ob = new_obj(f"Status_LED_{i + 1}", me, status, coll)
    ob["role"] = ["power/status", "network", "network", "battery"][i]

def build_lcd():
    o, xa, ya, za = rear_frame(ct["lcd_z_H"] * H)
    w, h = ct["lcd_size"]; th = 0.6; sink = 0.5
    bm = bmesh.new(); uv_l = bm.loops.layers.uv.new("UVMap")
    corners2 = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    top = [bm.verts.new(o + (xa * x + ya * y + za * (th)) * MM) for x, y in corners2]
    bot = [bm.verts.new(o + (xa * x * 1.0 + ya * y * 1.0 - za * sink) * MM) for x, y in corners2]
    ft = bm.faces.new(top)
    for k in range(4): bm.faces.new((bot[k], bot[(k + 1) % 4], top[(k + 1) % 4], top[k]))
    bm.normal_update()
    if ft.normal.dot(za) < 0:
        for f in bm.faces: f.normal_flip()
    for f in bm.faces:
        for l in f.loops:
            d = (l.vert.co - o) / MM
            x, y = d.dot(xa), d.dot(ya)
            if f is ft:
                l[uv_l].uv = (x / w + 0.5, y / h + 0.5)  # frame is part of the texture
            else:
                l[uv_l].uv = (0.01, 0.01)   # frame colour
    me = bpy.data.meshes.new("Status_Display"); bm.to_mesh(me); bm.free()
    me.materials.append(MAT["lcd"])
    for p in me.polygons: p.use_smooth = False
    return new_obj("Status_Display", me, status, coll)
build_lcd()

# ----------------------------------------------------------------------------- rear details (body children)
rp = P["rear"]
def rear_box(name, cx, cz, w, h, depth, mat, r=1.0):
    outline = rounded_rect(w, h, min(r, w / 2 - 0.01, h / 2 - 0.01), 4, -h / 2)
    bm = bmesh.new()
    top = [bm.verts.new(W3(Y_BACK + depth, cz + o.y, cx + o.x)) for o, _ in outline]
    bot = [bm.verts.new(W3(Y_BACK - 0.3, cz + o.y, cx + o.x)) for o, _ in outline]
    n = len(outline)
    ft = bm.faces.new(top)
    for k in range(n): bm.faces.new((bot[k], bot[(k + 1) % n], top[(k + 1) % n], top[k]))
    bm.normal_update()
    if ft.normal.y < 0:
        for f in bm.faces: f.normal_flip()
    bmesh.ops.triangulate(bm, faces=[ft])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = False
    return me
pw, ph = rp["pad_size"]
me = rear_box("Rear_Contact_Pads", -(pw + rp["pad_gap"]) / 2, rp["pad_z"], pw, ph, 0.5, MAT["contacts"])
me2 = rear_box("tmp", (pw + rp["pad_gap"]) / 2, rp["pad_z"], pw, ph, 0.5, MAT["contacts"])
bm = bmesh.new(); bm.from_mesh(me); bm.from_mesh(me2); bm.to_mesh(me); bm.free(); bpy.data.meshes.remove(me2)
pads = new_obj("Rear_Contact_Pads", me, body, coll)
pads["note"] = "Two light-grey rectangular features seen on the rear lower edge; function (charging contacts / cradle pads) unconfirmed."

def rear_logo():
    font = bpy.data.fonts.load("/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf", check_existing=True)
    cu = bpy.data.curves.new("Rear_Logo", "FONT"); cu.body = "Paytm"; cu.font = font
    cu.size = rp["logo_height"] * MM * 1.35; cu.align_x = "CENTER"; cu.align_y = "CENTER"
    cu.extrude = 0.18 * MM; cu.resolution_u = 3 if LOD == "ar" else 6
    tmp = bpy.data.objects.new("Rear_Logo_tmp", cu); coll.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg)); me.name = "Rear_Logo"
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    # text lies in XY facing +Z; rotate to face +Y (rear) and read correctly from behind
    rot = Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Rotation(math.radians(180), 4, "Y")
    rot = Matrix.Rotation(math.radians(180), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X")
    me.transform(rot)
    me.transform(Matrix.Translation(W3(Y_BACK + 0.12, rp["logo_z"])))
    me.materials.clear(); me.materials.append(MAT["body"])
    while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    for p in me.polygons: p.use_smooth = False
    ob = new_obj("Rear_Logo", me, body, coll)
    ob["note"] = "Debossed brand mark seen on the rear (low-res reference); rendered as plain typeset text, not official artwork."
    return ob
rear_logo()

# ----------------------------------------------------------------------------- metadata, save
for ob in coll.objects:
    ob["lod"] = LOD
anchor["provisional_dimensions"] = True
anchor["source"] = "Fitted to PencilProto public renders (design analysis only). Not affiliated with Paytm."
bpy.data.texts.new("build_soundbox.py").from_string(open(__file__).read())
scene.render.engine = "CYCLES"
# frame / bookkeeping
dims = {}
deps = bpy.context.evaluated_depsgraph_get()
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3); tris = 0
for ob in coll.objects:
    if ob.type != "MESH": continue
    mw = ob.matrix_world
    for v in ob.data.vertices:
        w = mw @ v.co; mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
    ob.data.calc_loop_triangles(); tris += len(ob.data.loop_triangles)
size = (mx - mn) / MM
print(f"[build] LOD={LOD} bbox mm W={size.x:.1f} D={size.y:.1f} H={size.z:.1f}  minZ={mn.z/MM:.3f} tris={tris}")
json.dump({"lod": LOD, "bbox_mm": [round(size.x, 2), round(size.y, 2), round(size.z, 2)],
           "min_mm": [round(c / MM, 2) for c in mn], "max_mm": [round(c / MM, 2) for c in mx], "triangles": tris},
          open(os.path.join(ROOT, "validation", f"build_{LOD}.json"), "w"), indent=2)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True)
print("[build] saved", OUT)
