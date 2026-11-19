"""Per-component triangle counts -> validation/component_stats_<lod>.json"""
import bpy, json, os, sys
lod = "ar" if "ar.blend" in bpy.data.filepath else "hero"
root = os.path.dirname(bpy.data.filepath) if lod == "hero" else os.path.dirname(os.path.dirname(bpy.data.filepath))
res = {}
for o in bpy.data.objects:
    if o.type != "MESH": continue
    o.data.calc_loop_triangles()
    top = o
    while top.parent and top.parent.name != "Ground_Anchor": top = top.parent
    res.setdefault(top.name, 0); res[top.name] += len(o.data.loop_triangles)
json.dump(res, open(os.path.join(root, "validation", f"component_stats_{lod}.json"), "w"), indent=2)
print("STATS", lod, res, sum(res.values()))
