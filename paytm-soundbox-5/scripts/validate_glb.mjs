// Validate GLBs with the Khronos glTF Validator and report asset statistics.
//   node scripts/validate_glb.mjs a.glb [b.glb ...]   -> validation/<name>.validator.json + summary
import validator from 'gltf-validator';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { getBounds } from '@gltf-transform/core';
import fs from 'node:fs';
import path from 'node:path';

const REQUIRED = ['Ground_Anchor', 'Soundbox_Body', 'Front_Faceplate', 'QR_Panel', 'Speaker_Region', 'Top_Controls', 'Status_Indicator'];
const outDir = path.join(path.dirname(new URL(import.meta.url).pathname), '..', 'validation');
let failed = false;
const summary = {};
for (const file of process.argv.slice(2)) {
  const data = new Uint8Array(fs.readFileSync(file));
  const report = await validator.validateBytes(data, { maxIssues: 500 });
  const name = path.basename(file, '.glb');
  fs.writeFileSync(path.join(outDir, `${name}.validator.json`), JSON.stringify(report, null, 2));
  const doc = await new NodeIO().registerExtensions(ALL_EXTENSIONS).read(file);
  const root = doc.getRoot();
  let tris = 0, verts = 0;
  for (const mesh of root.listMeshes()) for (const p of mesh.listPrimitives()) {
    const idx = p.getIndices();
    tris += (idx ? idx.getCount() : p.getAttribute('POSITION').getCount()) / 3;
    verts += p.getAttribute('POSITION').getCount();
  }
  const names = root.listNodes().map((n) => n.getName());
  const missing = REQUIRED.filter((n) => !names.includes(n));
  const b = getBounds(root.listScenes()[0]);
  const textures = root.listTextures().map((t) => ({ name: t.getName() || t.getURI(), mime: t.getMimeType(), size: t.getSize(), kib: +(t.getImage().byteLength / 1024).toFixed(1) }));
  const s = {
    bytes: data.byteLength,
    kib: +(data.byteLength / 1024).toFixed(1),
    validator: { errors: report.issues.numErrors, warnings: report.issues.numWarnings, infos: report.issues.numInfos, hints: report.issues.numHints },
    issues: report.issues.messages.map((m) => `${m.severity === 0 ? 'ERROR' : m.severity === 1 ? 'WARN' : 'INFO'} ${m.code} ${m.pointer ?? ''} ${m.message}`).slice(0, 40),
    triangles: tris, vertices: verts, draw_calls: root.listMeshes().reduce((a, m) => a + m.listPrimitives().length, 0),
    materials: root.listMaterials().map((m) => m.getName()),
    extensionsUsed: root.listExtensionsUsed().map((e) => e.extensionName),
    textures,
    bounds_m: { min: b.min.map((v) => +v.toFixed(5)), max: b.max.map((v) => +v.toFixed(5)) },
    size_mm: b.max.map((v, i) => +((v - b.min[i]) * 1000).toFixed(1)),
    required_nodes_missing: missing,
    nodes: names,
  };
  if (report.issues.numErrors > 0 || missing.length) failed = true;
  summary[name] = s;
  console.log(`${name}: ${s.kib} KiB, ${tris} tris, errors=${s.validator.errors} warnings=${s.validator.warnings} infos=${s.validator.infos}, size_mm(x,y,z)=${s.size_mm}, missing=${missing}`);
  for (const i of s.issues) console.log('   ', i);
}
fs.writeFileSync(path.join(outDir, 'glb_summary.json'), JSON.stringify(summary, null, 2));
process.exit(failed ? 1 : 0);
