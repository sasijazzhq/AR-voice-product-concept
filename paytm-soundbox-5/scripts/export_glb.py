"""Export the model in the currently open .blend to an (unprocessed) GLB.

    blender -b paytm-soundbox-5.blend --python scripts/export_glb.py -- --out build/hero_raw.glb

Custom object properties are exported as glTF `extras` (three.js: object.userData).
Post-processing (material variants, texture compression, quantisation) is done by
scripts/postprocess_glb.mjs.
"""
import bpy, os, sys
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.join(os.path.dirname(bpy.data.filepath), argv[argv.index("--out") + 1])
os.makedirs(os.path.dirname(out), exist_ok=True)
# only export the product collection (no studio lights/backdrop)
for o in bpy.data.objects:
    o.select_set(o.users_collection and o.users_collection[0].name == "Paytm_Soundbox_5")
bpy.ops.export_scene.gltf(
    filepath=out, export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
    export_normals=True, export_texcoords=True, export_tangents=False, export_materials="EXPORT",
    export_image_format="AUTO", export_extras=True, export_cameras=False, export_lights=False,
    export_animations=False, export_skins=False, export_morph=False,
)
print("[export] wrote", out)
