// Post-process raw Blender GLBs with glTF-Transform.
//   node scripts/postprocess_glb.mjs <in.glb> <out.glb> <hero|ar>
// hero: adds KHR_materials_variants (Cobalt / Fabric Blue / Icy White), PNG textures, dedup/prune.
// ar:   same variants + WebP textures (EXT_texture_webp) + KHR_mesh_quantization.
//       No Draco/Meshopt, so three.js GLTFLoader needs no decoder setup.
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, KHRMaterialsVariants } from '@gltf-transform/extensions';
import { dedup, prune, quantize, textureCompress, weld } from '@gltf-transform/functions';
import sharp from 'sharp';
import fs from 'node:fs';
import path from 'node:path';

const [, , input, output, mode] = process.argv;
const params = JSON.parse(fs.readFileSync(path.join(path.dirname(new URL(import.meta.url).pathname), 'params.json')));
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.read(input);
const root = doc.getRoot();

const srgbToLin = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const hex = (h) => [1, 3, 5].map((i) => srgbToLin(parseInt(h.slice(i, i + 2), 16) / 255)).concat([1]);

// ---- material variants for the body colourways (CMF from the reference: Cobalt, Fabric Blue, Icy White)
const body = root.listMaterials().find((m) => m.getName() === 'MAT_Body_Cobalt');
if (!body) throw new Error('MAT_Body_Cobalt not found');
const ext = doc.createExtension(KHRMaterialsVariants);
const variants = {
  Cobalt: [body, null],
  'Fabric Blue': [body.clone().setName('MAT_Body_FabricBlue').setBaseColorFactor(hex(params.colours_srgb.fabric_blue_body)), null],
  'Icy White': [body.clone().setName('MAT_Body_IcyWhite').setBaseColorFactor(hex(params.colours_srgb.icy_white_body)), null],
};
for (const [name, v] of Object.entries(variants)) v[1] = ext.createVariant(name);
for (const mesh of root.listMeshes()) {
  for (const prim of mesh.listPrimitives()) {
    if (prim.getMaterial() !== body) continue;
    const mv = ext.createMappingList();
    for (const [, [mat, variant]] of Object.entries(variants)) {
      mv.addMapping(ext.createMapping().setMaterial(mat).addVariant(variant));
    }
    prim.setExtension('KHR_materials_variants', mv);
  }
}

await doc.transform(dedup(), prune({ keepAttributes: true, keepLeaves: true, keepExtras: true }));
if (mode === 'ar') {
  await doc.transform(
    textureCompress({ encoder: sharp, targetFormat: 'webp', quality: 90 }),
    quantize({ quantizePosition: 14, quantizeNormal: 10, quantizeTexcoord: 12 }),
  );
}
root.getAsset().generator = 'Blender 4.2 + glTF-Transform (paytm-soundbox-5 pipeline)';
root.getAsset().copyright = 'Original 3D asset by the Paytm Reality Lab project. Product industrial design belongs to its owners; not an official model.';
await io.write(output, doc);
console.log(`[post] ${mode} -> ${output} ${(fs.statSync(output).size / 1024).toFixed(1)} KiB`);
