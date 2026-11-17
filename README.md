# Snap-on cat ears: Corsair HS35 v2 / HS35 Surround v2

**Live 3D viewer:** https://hoodedhacker32.github.io/hs35-kitty-ears/ (works on mobile; give it a few seconds to load)
**Animated assembly guide:** https://hoodedhacker32.github.io/hs35-kitty-ears/assembly.html

Soft, rounded "hood" cat ears that snap onto the headband. Each ear has three parts, and **nothing needs supports**:

| Part | File (in `out_v3/`) | Filament | Print orientation | Qty |
|---|---|---|---|---|
| Ear | `ear_LEFT.stl`, `ear_RIGHT.stl` | Bambu **PLA Matte Charcoal** | Lying on its flat back, as exported | 1 each |
| Clip | `clip_W35.6_T7.5_print_x2.stl` | Bambu **PETG Basic Black** | Standing on its end, as exported | **2** |
| Inner ear | `inner_ear_insert_LEFT.stl`, `inner_ear_insert_RIGHT.stl` | Bambu **PLA Matte Sakura Pink** | Flat, as exported | 1 each |

LEFT and RIGHT are from the wearer's point of view.

## Why it's split up
- **The clip is the only part that flexes.** It prints standing on its end, so every layer contains the whole clip profile, and the snap hooks bend *along* the layer lines rather than prying them apart. That's why it's PETG: it's tough and springy.
- **The ear doesn't flex,** so it can be matte PLA, which matches the headset's matte finish and is easier to print. Its back is one flat plane with a 35° chamfered edge, so it prints lying down with **zero supports**. The hood, inner-ear pocket and rail groove are all shaped to be self-supporting in that orientation. Checked: the overhang area needing support is effectively zero (under 3 mm² of 15,000 mm²).
- **The ear slides onto the clip** on a dovetail rail (0.15 mm side clearance, 0.25 mm top), so the two materials don't have to print together.

## Print settings (Bambu printer)
- **Ears (PLA Matte):** for speed, 0.20 mm layers, 2 walls, 10% infill (use 0.16 mm and 3 walls for a finer finish), no supports, no brim needed.
- **Clips (PETG Basic):** 0.20 mm layers, **4 walls**, 100% infill (they're small, and solid is strongest), no supports. Use a **brim** because it's tall and narrow (62 mm).
- **Inner ears (PLA Matte):** 0.16 mm, flat, no supports.
- **Filament used, both ears:** about 66 g Charcoal, 28 g black PETG and 10 g Sakura Pink.

## Assembly
1. Press each pink inner ear into its ear's pocket (a dab of glue if loose).
2. Slide each ear onto a clip's dovetail rail from one end until it's centred. A small drop of superglue or epoxy on the rail makes it permanent. Optional, but recommended.
3. Hold the ear over the headband about 50 mm out from the centre of the "CORSAIR" logo and press straight down until both hooks click under the band's edges. To remove it, flex one clip wall outward.

## Cheapest verified filament (Amazon.ie, checked 17 Nov 2026)
All 1.75 mm, so they work in any Bambu printer (Generic PLA / Generic PETG profile). Each plate uses **one filament only**, so there are no colour swaps and no purge waste, and the AMS isn't needed.

| Plate | Prints | Filament | Link | Price |
|---|---|---|---|---|
| 1 | 2 ears | Matte black PLA | [DEEPLEE Matte PLA Black 1 kg](https://www.amazon.ie/dp/B0DKNPTNDD) | €15.83 |
| 2 | 2 clips | Black PETG | [CC3D Standard PETG Black 1 kg](https://www.amazon.ie/dp/B0D91G7BDF) | €12.99 |
| 3 | 2 inner ears | Pink PETG (fine here, it doesn't flex) | [CC3D Standard PETG Pink 1 kg](https://www.amazon.ie/dp/B0F6N6JR5K) | €12.99 |

About €42 in total. **Cheapest possible (€25.98):** skip the matte PLA and print the ears in the same black PETG as the clips. Two rolls, but glossier ears.

**Filament actually used:** about 40–55 g of black PLA, 25 g of black PETG (37 g if you print one test clip first) and 5 g of pink.

Avoid: a €10.76 "CC3D PETG Pink" listing (ASIN B0FFH3984F) whose spec sheet says TPE, and a "Creality PETG" listing (B0C8NP63GD) whose brand field says YOOPAI.

## Filament notes
- **PETG HF is being discontinued** in most colours. Bambu relaunched **PETG Basic** in 2026 as the successor, and it's what the clips use. Avoid *matte* PETG for the clips: the matte additive makes it stiffer and more brittle, which is the opposite of what a snap clip wants.
- **Cheaper alternatives:** any 1.75 mm filament works on a Bambu printer. Use the "Generic PLA" or "Generic PETG" profile.
  - Matte black PLA: SUNLU or ELEGOO matte PLA run roughly $10–14/kg versus about $20+/kg for Bambu (ELEGOO's matte black is noted as especially deep and flat). JAYO is a mid-price option on plastic spools that the AMS likes.
  - PETG: SUNLU / ELEGOO PETG in black are similar savings.
  - Pink: "Sakura Pink" is a Bambu shade. Third-party pinks vary, so check photos if the exact shade matters. Only about 10 g is needed, so the Bambu spool or a friend's leftovers may be the sensible choice.
  - Check spool weight (some cheap spools are 0.65 kg, not 1 kg) and prefer plastic spools for the AMS.

## Fit
The clip is sized from the HS35 v2 headband model ([Printables 1869509](https://www.printables.com/model/1869509-corsair-hs35-v2-headband-replacement)): band 35.6 mm wide, 7.5 mm edge depth, 3 mm top chamfers, 91.5 mm arch radius. The hooks reach 1.3 mm under the 1.6 mm edge lips. A collision check against the real headband model shows no interference. If the snap is too tight or loose, regenerate with `--thick 7.3` (tighter) or `--thick 7.7` (looser).

## Regenerating
```
pip install manifold3d trimesh numpy shapely scikit-image scipy matplotlib
python cat_ears_v3.py --band-stl corsair_hs_35_v2_headband.stl --out out_v3
```
`--height 80` makes taller ears. `--place 55` moves them further out (used for the preview and collision check).

The viewer (`index.html`) is rebuilt with `build_viewer_scene.py` followed by `build_viewer_html.py`.

## Credits and licence
- Headband and strap-anchor geometry in the viewer, and the measurements the clip is sized from: [Corsair HS35 v2 headband replacement on Printables](https://www.printables.com/model/1869509-corsair-hs35-v2-headband-replacement), CC BY-NC. Because the ears are fitted to that model, this project is shared under **CC BY-NC 4.0**: non-commercial use only, with attribution.
- Corsair logo outline from [Simple Icons](https://simpleicons.org/). Corsair and HS35 are trademarks of Corsair. This is a fan project and is not affiliated with Corsair.
