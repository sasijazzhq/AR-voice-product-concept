# Soundbox 5.0 3D asset: technical report

**Status:** Phases 1–6 complete. Both GLBs pass the Khronos glTF Validator with 0 errors, 0 warnings and 0 infos.
**Important caveat:** every dimension is **provisional**. No physical unit was measured and no official dimensions were found (see §7).

## 1. Deliverables

| File | Purpose |
|---|---|
| `paytm-soundbox-5.blend` | Editable master (hero LOD). It contains the build script as a text block. Textures are linked relatively from `textures/`. Body colour variants are kept as fake-user materials. |
| `exports/paytm-soundbox-5-hero.glb` | Web product viewer model, 23,044 tris, PNG textures (2048² QR sticker) |
| `exports/paytm-soundbox-5-ar.glb` | Mobile AR model, 9,000 tris, WebP textures (1024² QR sticker), quantised geometry |
| `renders/front.png`, `left.png`, `right.png`, `rear.png`, `top.png`, `threequarter.png` | Six Cycles comparison renders (1600×1200) |
| `renders/hero.png` | Premium hero render (2400×1600, depth of field) |
| `renders/contact_sheet.jpg` | All six views on one sheet |
| `reference/REFERENCE_MANIFEST.md` | Sources, viewing angles, confidence, measured facts, missing information |
| `validation/` | Validator reports, GLB summary, silhouette metrics, three.js load check, QR decode check, per-component stats |
| `scripts/` | Fully reproducible pipeline (`./build_all.sh`) |

## 2. Model dimensions (provisional)

| | mm | Note |
|---|---|---|
| Overall width (faceplate) | **94.4** | body shell 92.7 |
| Overall depth | **114.4** | |
| Overall height | **91.0** | |
| Front face inclination | 53° from horizontal | measured |
| Rear upper slope | 38.7° | measured |
| Faceplate | 94.4 × 101 × 4.0, corner R13, rim 4.8, sticker pocket 0.9 deep | |
| QR sticker | 84.2 × 91.8 × 0.35, QR area 43 × 43 | |
| Speaker grille | 31 slots per side, 4.0 × 1.6 mm, 1.6 mm deep, at −37° | |
| Buttons | 4 × Ø8 mm, 10.5 mm pitch, 1.8 mm proud | |

**Scale assumption.** Proportions are measured from the orthographic PencilProto renders. Absolute scale assumes an overall
height of ≈90 mm (the model is 91 mm). To recalibrate after measuring a real unit, change `H` in `scripts/params.json` and
run `./build_all.sh`, or scale `Ground_Anchor` uniformly in an app.

**Origin and axes.** The origin is the centre of the flat ground-contact footprint at height 0. In glTF, +Y is up, the QR
faces +Z, and units are metres (bounds: x ±0.0472, y 0…0.0910, z −0.0533…0.0611). The origin is deliberately **not** the
bounding-box centre, because the footprint is offset under the sloping front.

### Shape fidelity (silhouette IoU against the orthographic references, normalised to equal height)

| View | IoU | Aspect (ref / model) | Mean / p95 outline deviation |
|---|---|---|---|
| Right side vs PencilProto `Right.png` | **0.977** | 1.270 / 1.260 | 0.013 H / 0.031 H |
| Front vs PencilProto `Front.png` | **0.987** | 1.048 / 1.039 | 0.011 H / 0.026 H |

The remaining outline differences are small: the button bump is slightly larger in the reference, and the model's
base corners are slightly rounder.

## 3. Polygon budget

| Component | Hero tris | AR tris |
|---|---|---|
| Soundbox_Body (incl. Rear_Contact_Pads, Rear_Logo, Apex_Seal) | 9,412 | 3,720 |
| Front_Faceplate (incl. QR_Panel) | 6,462 | 2,334 |
| Speaker_Region (62 slot walls and floors) | 3,224 | 1,736 |
| Top_Controls (4 buttons) | 3,360 | 1,040 |
| Status_Indicator (4 LEDs + LCD) | 586 | 170 |
| **Total** | **23,044** | **9,000** |

* Draw calls: 16 (one per named part, kept separate for interaction).
* The AR LOD sits slightly below the suggested 10k–30k starting budget. It was refined against visual quality: every
  vertex carries an **analytic custom normal** (computed from the exact fillet and arc geometry), so curvature shades
  smoothly even at low density. The three.js render check (`validation/threejs_ar_check.png`) shows no faceting. If
  close-up AR inspection shows silhouette stepping on the rear blend, raise `seg90` in the `ar` LOD of `build_soundbox.py`;
  this costs about 1.5k tris.
* AR geometry uses `KHR_mesh_quantization` (positions 14-bit, normals 10-bit, UVs 12-bit). This is supported natively by
  three.js `GLTFLoader` with no decoder. Draco and Meshopt were deliberately not used, so the app needs no decoder setup.

## 4. Render calibration and iteration log

| Iteration | Finding | Fix |
|---|---|---|
| 1 | Silhouette IoU: side 0.887 and front 0.566. The front score was a measuring bug: the reference's white sticker was treated as background. The top was 3 mm low. | Hole-filled the reference masks. Extended the faceplate to the front/rear-slope apex and lengthened it to the measured 101 mm. Result: IoU 0.976 / 0.985. |
| 2 | Notch at the apex; faceplate top corners too square | Side fillet 6.5→4.8 mm, apex and nose radii 5 mm, faceplate corner R11→R13. Result: IoU 0.977 / 0.987. |
| 3 | AgX desaturated the sticker; body read sky-blue | Switched to the Standard view transform. Calibrated exposure so the lit side matches the reference: (72,103,140) against the reference's (72,103,138). |
| 4 | Faceplate looked chrome | Changed to satin metallic paint (metallic 0.5, roughness 0.34). |
| 5 | Side-view backdrop went grey | Added a one-sided wall light. Self-illumination on the sweep was tried first and rejected, because it flooded the front face. |
| 6 | Front label clipped; QR black rendered at about 66 | Moved the key light to 70°/52° off-axis. Made the print matte. Result: QR black is 35, and cyan and navy match their texture values. |
| 7 | UV float noise (−1e-8) blocked UV quantisation | Clamped the UVs. |
| 8 | Side views showed a V-notch between the faceplate's top edge and the body's rounded apex; the reference closes this junction | Added `Apex_Seal` (12 tris), which continues the rear slope up to the faceplate's back edge and tapers out under the faceplate corners. |
| 9 | Three-quarter view: bezel read as chrome (dark on one side, white on the other) | Bezel changed to satin paint (metallic 0.25, roughness 0.45, base `#bfc2c5`). It now renders an even light grey, as in the reference. |
| 10 | Hard-edged white patch across the top of the frame and cyan band | Cause: the backdrop wall light's emitting side clipped the top-rear of the product. Moved it fully behind the product, and softened and dimmed the rim light. |

## 5. Textures and materials

| Texture | Hero | AR |
|---|---|---|
| QR sticker | 2048² PNG (205 KiB) | 1024² WebP q90 (39 KiB) |
| LCD screen | 512×256 PNG | 512×256 WebP |
| Button icon atlas | 512² PNG | 512² WebP |

* **Materials** (glTF metallic-roughness, with `KHR_materials_clearcoat` and `KHR_materials_emissive_strength`):
  * `MAT_Body_Cobalt`: moulded satin plastic, roughness 0.38, light coat
  * `MAT_Faceplate_MetallicPaint`: satin metallic paint, metallic 0.25, roughness 0.45, clearcoat 0.25
  * `MAT_QR_Print`: matte print (roughness 0.6, no coat). A glossy laminate was tried first; it reflected the studio sweep and washed the QR modules to grey, so it was dropped.
  * `MAT_Buttons`: atlas with the cobalt or cyan cap colour baked per cell
  * `MAT_Speaker_Mesh`
  * `MAT_LCD`: glossy, slightly emissive
  * `MAT_LED_Green`: emissive
  * `MAT_Contacts_Metal`
* **Colourways** are exposed through `KHR_materials_variants`: *Cobalt* (default), *Fabric Blue* and *Icy White*, matching
  the CMF names on the PencilProto page. three.js does not apply this extension automatically; read
  `gltf.parser.json.extensions.KHR_materials_variants` or swap `MAT_Body_*` colours in code. `<model-viewer>` supports it
  natively.
* **Texture compression.** WebP (`EXT_texture_webp`) was used for the AR file. KTX2/Basis was the first choice for GPU
  memory, but the KTX-Software encoder could not be installed in this build environment. To switch, run
  `npx gltf-transform uastc exports/paytm-soundbox-5-ar.glb out.glb --slots baseColorTexture` with `toktx` installed.
  WebP needs iOS 14+ or Safari 14+; the AR file lists `EXT_texture_webp` as required.
* **UVs.** Only textured parts have UVs: `QR_Panel` uses a planar 0–1 mapping over the true sticker aspect, the buttons use
  a planar mapping into atlas cells, and `Status_Display` uses a planar mapping. Untextured parts export no TEXCOORD.

### Non-payable QR

* The QR (version 4-H, 33 modules, about 1.3 mm per module) encodes the plain text
  `PAYTM REALITY LAB DEMO - NOT A PAYMENT CODE`. It is not a `upi://` URI and contains no VPA.
* The texture carries a visible **DEMO** badge and a red **"SAMPLE QR • NOT PAYABLE"** line.
* `QR_Panel` has `extras.payable = false` and `extras.qr_payload`.
* QR decode results (OpenCV) for both texture sizes and the final renders are in `validation/qr_decode.json`.

## 6. Interactive structure (glTF node names → three.js `getObjectByName`)

```
Ground_Anchor                  root, origin at ground contact (place on the AR hit-test pose)
├─ Soundbox_Body               main shell
│  ├─ Rear_Contact_Pads
│  ├─ Apex_Seal                closes the faceplate/body junction at the top
│  └─ Rear_Logo
├─ Front_Faceplate             metallic painted frame
│  └─ QR_Panel                 sticker (userData.payable=false, userData.qr_payload)
├─ Speaker_Region              both side grilles (walls + dark acoustic floor)
├─ Top_Controls
│  ├─ Button_VolumeUp / Button_VolumeDown / Button_Repeat / Button_Power   (userData.function)
└─ Status_Indicator
   ├─ Status_LED_1..4          (userData.role)
   └─ Status_Display           LCD
```

## 7. Limitations (read before production use)

1. **Dimensions are provisional.** They rest on proportions plus an assumed ~90 mm height. Calibrate them against a
   physical unit.
2. **The rear details are approximate.** The only rear reference is defocused, so these are approximate:
   * LED count and positions
   * LCD size and screen content
   * button icons
   * the two grey pads (function unknown)
   * the debossed mark
3. **The underside is unknown.** It is modelled as a plain flat base with no feet. No base-cover parting line is modelled.
4. **The left-side grille is assumed** to mirror the right side.
5. **Brand graphics are not official.**
   * The front shows "Paytm" in Inter typeface, not the official logo.
   * The UPI and "Tap & Pay" marks are omitted.
   * Swap in licensed brand artwork via `scripts/make_textures.py` if authorised.
6. **The faceplate-to-body junction is simplified.** The top junction is closed by a small seal strip rather than a
   modelled recess, and a small shadow gap (≤2 mm) remains under the faceplate's bottom edge and around its corners. The
   real part probably seats the plate in a recess; no reference shows that detail.
7. **There are no baked AO or normal maps.** Lighting relies on the viewer or environment map. For AR, add a contact-shadow
   plane or ground shadow in the app.
8. Material colours were sampled from rendered marketing images, not measured colour standards.
9. **The body's side-edge radius is a compromise.** It is 4.8 mm everywhere. The defocused rear reference suggests the
   upper rear edges may be softer (roughly 8–10 mm); this could not be measured.
10. **Phone performance has not been measured on a device.** WebGL loading was verified in three.js 0.183.2 under headless
   Chromium (SwiftShader).

## 8. Licences and provenance

* **This asset.** The geometry, textures and scripts are original work generated by the scripts in this folder. No
  third-party mesh, render or photo is included. No licence file has been chosen yet; the repository owner should add one.
* **Industrial design and trademarks.**
  * The Soundbox 5.0 industrial design is credited by PencilProto to its designer, for One97 Communications Ltd (Paytm).
  * "Paytm" and related marks belong to their owners.
  * This is an independent, illustrative reproduction for an AR learning prototype. It is not an official Paytm model, and
    no ownership of the design is claimed.
* **Reference images** (PencilProto, Oakter) were viewed for analysis only and are not redistributed. Overlays containing
  reference pixels were kept outside the repository.
* **CasualClicks/QR_Payment_Soundbox** (MIT) was inspected for wall and plate thickness only. None of its geometry is used.
* **Tools and fonts:**

  | Item | Licence | Use |
  |---|---|---|
  | Blender 4.2 LTS | GPL | Outputs are not encumbered |
  | glTF-Transform | MIT | |
  | sharp / libvips | Apache-2.0 / LGPL | |
  | Khronos glTF Validator | Apache-2.0 | |
  | segno | BSD-3 | QR generation |
  | Inter font | SIL OFL 1.1 | Rasterised into textures and the rear deboss |
