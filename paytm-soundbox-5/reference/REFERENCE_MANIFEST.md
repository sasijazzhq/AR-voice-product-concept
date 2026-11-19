# Reference manifest — Soundbox 5.0 3D asset

Reference images are **third-party material used for design analysis only**. None of them is
stored in this repository and none is redistributed. Image IDs below are the Wix media IDs on the
PencilProto page, so each one can be re-located at the source.

**Visual authority:** PencilProto, *Paytm Sound Box Detailed*. The page describes the work as industrial design
for One97 Communications Ltd (Paytm), 2024, status *Launched*, and explicitly names it "Paytm Soundbox 5.0".
Other Soundbox generations (Pocket, Music, card-terminal variants) were **not** used for geometry.

## Sources

| # | Source | What it is | Viewing angle | Used for | Confidence |
|---|--------|-----------|---------------|----------|------------|
| R1 | https://www.pencilproto.com/paytmsoundbox — `c463af_e1f51e26…` (`Right.png`, 3840×2160) | Studio render, cobalt, orthographic right side | Pure side, horizontal | Side profile fit (front/rear slopes, rear blend radius, undercut, faceplate thickness), speaker slot positions | **High** |
| R2 | same page — `c463af_514a35c9…` (`Front.png`, 3840×2160) | Studio render, cobalt, orthographic front | Pure front, horizontal | Width/height ratio, bezel width, sticker border widths, cyan/navy split, QR size | **High** |
| R3 | same page — `c463af_0bd7aa37…` (`Pebble_5.png`, 2560×1440) | Two units: front ¾ and rear ¾ (rear unit defocused) | ~35° front-left, ~40° rear-left, elevated | Faceplate rim profile, rear layout (LEDs, LCD, 4 buttons, deboss, two grey pads) | Front: high · Rear: **medium** (out of focus) |
| R4 | same page — `c463af_dd661387…` (`Pebble_3.jpg`) | Three colourways in a row | Front ¾, elevated | CMF: Fabric Blue, Icy White, Cobalt; button row visible behind the faceplate | Medium (stylised lighting) |
| R5 | same page — `c463af_27c8f655…` (`Pebble_2.jpg`) | Grid of icy-white units plus one cobalt | Front ¾, elevated | Body form consistency; on white units the slots read as dots | Medium |
| R6 | same page — `c463af_3068e6aa…`, `c463af_3e75ca50…`, `c463af_60774562…` | In-situ product visualisations | Various, far | General proportion sanity check only | Low |
| R7 | same page — `c463af_2cb64f06…`, `c463af_1c349d72…` | Factory photos (assembly line) | Various | Confirms the real product matches the renders; rear button row seen on the line | Medium (photo of production units) |
| R8 | same page — `c463af_63191ad9…`, `c463af_75486ad2…`, `c463af_a5cab3c7…`, `c463af_cc7ef131…`, `c463af_71138658…` | Factory photos of moulded parts (side shells, base covers, button sprues) | Various | Confirms the moulded-plastic CMF and the separate base cover; button sprue shows round button caps | Low–medium |
| R9 | same page — `c463af_1d43e379…` (ideation sketches) | Sketches | — | Not used for geometry | — |
| S1 | https://www.oakter.com/collections/all | Lists "Paytm Soundbox" among its B2B products ("payment announcement devices built for retail counters") | — | Context only. Possibly the manufacturer, but the page does not say so. No dimensions published. | Low |
| S2 | https://github.com/CasualClicks/QR_Payment_Soundbox (MIT, © 2026 Shivam Singhal) | DIY ESP32 soundbox. `soundbox_shell_V1.stl` is a 130×91×58.5 mm rectangular box; `Soundbox_QR_Plate_V2.stl` is 87 mm wide | — | Plausibility check only: ~3 mm wall and plate thickness, QR plate ~85–90 mm wide. **Its geometry was not used**, because it is a different design. | n/a |
| — | User-provided photographs | None were attached to the request | — | — | — |

## Measured facts (units of overall height H, from R1/R2)

| Feature | Value | Method |
|---|---|---|
| Depth / height | 1.263–1.27 | silhouette bbox, R1 |
| Faceplate width / height | 1.049 | silhouette bbox, R2 |
| Front face inclination | **53.0° from horizontal** | least squares on silhouette rows 0.2–0.9 H |
| Rear upper slope | **38.7° from horizontal** | least squares on rows 0.80–0.97 H |
| Rear blend radius (slope → vertical back) | **0.51 H** (mean fit error 0.002 H) | circle fit, rows 0.36–0.69 H |
| Front undercut below faceplate | **34.6° from horizontal**, from base up to ≈0.09 H | least squares on rows 0.01–0.07 H |
| Faceplate visible thickness | 0.044 H (≈4 mm) | grey band width, R1 |
| Bezel rim width | ≈0.054 H (≈4.8 mm) | colour transitions, R2 |
| Sticker border | ≈0.06 H; cyan on the upper ~56 %, navy below | colour transitions, R2 |
| Speaker grille | 31 slots in rows of 2-5-6-5-6-5-2, slot ≈0.045 × 0.018 H at −37°, pitch 0.055 H × 0.048 H | connected components, R1 |
| Rear button bump | at ≈0.73–0.77 H | silhouette, R1 |

## Missing or uncertain information (documented, not invented)

* **Absolute size.** No public dimensions were found (PencilProto, Oakter or web search). All millimetre values come from
  assuming H ≈ 90 mm (the model is 91.0 mm tall), so they are **provisional ±10 %** until a physical unit is measured.
  A sanity check against typical counter QR plates (~85–90 mm wide, see S2) supports the scale.
* **Underside.** No reference shows it. The model has a plain flat base. Feet, labels and the screw pattern are unknown,
  so none were modelled.
* **Rear details.** The rear is only seen defocused (R3). LED count and position (1 + 3), LCD size and content, the button
  icons, the two grey pads (charging contacts or rubber pads?) and the deboss size are all **approximate**.
* **Base parting line.** R1 suggests a separate base cover a few mm high, and R8 shows base covers. It is not modelled
  as a separate part.
* **Left-side grille.** Only the right side is seen orthographically. The left side is assumed to be a mirror image.
* **Ports.** No USB or charging port is visible in any reference. None is modelled.
* **Exact colours.** Values were sampled from studio renders, so they depend on the lighting. They are not Pantone or RAL
  references.
* **Sticker artwork.** The real sticker carries official Paytm/UPI logos and a live merchant QR. Those are **intentionally
  not reproduced**: the model uses plain typeset text and a non-payable demo QR.
