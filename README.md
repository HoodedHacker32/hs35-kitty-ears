# Snap-on cat ears: Corsair HS35 v2 / HS35 Surround v2

**Live 3D viewer:** https://hoodedhacker32.github.io/hs35-kitty-ears/ (it works on mobile; give it a few seconds to load)

Soft, rounded "hood" ears with a thick rim and a recessed inner ear. Each ear covers the full depth of the headband and snaps under both edges.

## Print these (in `out_final_v3/`)

> LEFT and RIGHT are from the wearer's point of view.

| File | Colour | Orientation | Qty |
|---|---|---|---|
| `cat_ear_RIGHT_W35.6_T7.5.stl` | Black | Upright, as exported | 1 |
| `cat_ear_LEFT_W35.6_T7.5.stl` | Black | Upright, as exported | 1 |
| `inner_ear_insert_RIGHT.stl` | Pink (or black/grey) | Flat, as exported | 1 |
| `inner_ear_insert_LEFT.stl` | Pink (or black/grey) | Flat, as exported | 1 |

## Fit
The clip is sized from the HS35 v2 headband model ([Printables 1869509](https://www.printables.com/model/1869509-corsair-hs35-v2-headband-replacement)):
- Band width: 35.6 mm
- Edge depth (top surface to bottom of the edge lips): 7.5 mm
- Top edges: 3 mm chamfers
- Arch radius where the ears sit: 91.5 mm

Clearance is 0.2 mm on each side. Each hook reaches 1.3 mm under the band's 1.6 mm edge lips. The clip also fills the chamfers so it can't rock. In a collision check against the real headband model, the overlap was effectively zero (0.34 mm³, meshing noise). The ears are designed to sit about 50 mm either side of the centre of the "CORSAIR" logo, measured along the band.

## Print settings
- **PETG recommended.** The clip side walls flex ~1.3 mm to snap on, and PLA may crack over time.
- Ears: upright as exported, in **Bambu PETG HF Black** at 0.16 mm layers (0.12 mm for an even smoother finish), with **tree supports** (for the hood over the inner-ear pocket and the gap under the curved clip walls), a brim, 3 walls and 15–20% infill.
- Inserts: flat, no supports, in **Bambu PLA Matte Sakura Pink** (or Charcoal / Ash Grey). Press them into the pocket, with a dab of glue if loose.
- **Fitting:** hold the ear over the band and press straight down until both hooks click under the edges. To remove, flex one side wall outward.
- If the fit is too tight or too loose, regenerate with e.g. `--thick 7.3` (tighter) or `--thick 7.7` (looser).

## Regenerating
```
pip install manifold3d trimesh numpy shapely scikit-image scipy matplotlib
python cat_ears_v2.py --band-stl corsair_hs_35_v2_headband.stl --out out_final_v3
```
Options: `--height 80` makes the ears taller, and `--place 55` moves them further out (used for the preview and collision check).

## Realistic preview
Open `index.html` (or the live link above) in Chrome, Edge or Safari to see the ears on the full HS35 v2 with print-accurate materials. Rebuild it with `build_viewer_scene.py` followed by `build_viewer_html.py`.

## Credits and licence
- Headband and strap-anchor geometry in the viewer, and the measurements the clip is sized from: [Corsair HS35 v2 headband replacement on Printables](https://www.printables.com/model/1869509-corsair-hs35-v2-headband-replacement), licensed CC BY-NC. Because the ears are fitted to that model, this whole project is shared under **CC BY-NC 4.0**: non-commercial use only, with attribution.
- Corsair logo outline from [Simple Icons](https://simpleicons.org/). Corsair and HS35 are trademarks of Corsair. This is a fan project and is not affiliated with Corsair.
