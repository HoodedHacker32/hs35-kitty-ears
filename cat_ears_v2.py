"""
Puffy "hood" style snap-on cat ears for the Corsair HS35 v2 / HS35 Surround v2.
(Style inspired by soft, rounded-triangle cat ears with a thick rim and a deep inner ear.)

Run:  python cat_ears_v2.py [--band-stl corsair_hs_35_v2_headband.stl] [--place 50]
Defaults are measured from the HS35 v2 headband model (35.6 mm wide, 7.5 mm edge, 91.5 mm arch radius).
Outputs STLs + a preview .glb into ./out_v2/

Axes (as worn): X along the headband, Y across it (- = front/face side), Z up.
The wearer faces -Y, so +X is the WEARER'S LEFT. The ear modelled at +X is exported as the LEFT ear.
"""
import argparse, os
import numpy as np
import manifold3d as m3
from manifold3d import Manifold, CrossSection
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from skimage.measure import marching_cubes
import trimesh

ap = argparse.ArgumentParser()
ap.add_argument("--width", type=float, default=35.6, help="headband width, front edge to back edge (mm)")
ap.add_argument("--thick", type=float, default=7.5, help="headband edge depth: top surface to bottom of the edge lips (mm)")
ap.add_argument("--radius", type=float, default=91.5, help="headband arch radius where the ear sits (mm)")
ap.add_argument("--height", type=float, default=72.0, help="ear height above the clip (mm)")
ap.add_argument("--res", type=float, default=0.45, help="sculpt resolution (mm), smaller = smoother/slower")
ap.add_argument("--out", default="out_v2")
ap.add_argument("--band-stl", default=None, help="headband STL for the preview + collision check")
ap.add_argument("--place", type=float, default=50.0, help="ear centre distance from the top-centre of the arch, along the band (mm)")
A = ap.parse_args()

# ----------------------------------------------------------------- clip parameters
W, T, R = A.width, A.thick, A.radius
WALL, PLATE = 2.2, 2.8
HOOK, HOOK_H, CLR = 1.3, 2.0, 0.2
HOOK_L = 26.0
CHAMF = 2.6                        # fills the band's 3 mm top-edge chamfers so the clip can't rock
YO = W / 2 + CLR + WALL            # outer half-depth of clip == half-depth of the ear's base

# ----------------------------------------------------------------- ear parameters
H = A.height                       # tip height above the plate top
HW = 33.0 * H / 72                 # half-width of the base
KR = 8.0                           # puffiness (edge rounding blend), mm
RIM = 6.5                          # rim width around the inner ear
TILT = -8.0                        # deg, lean toward head centre
INS_T = 2.6                        # inner-ear insert thickness

def cs_from_shapely(poly):
    poly = orient(poly, 1.0)
    cont = [np.array(poly.exterior.coords)[:-1]] + [np.array(r.coords)[:-1] for r in poly.interiors]
    return CrossSection(cont)

def bez(p0, p1, p2, n=50):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2

def outline():
    """Front silhouette (x, z) of the right ear. Extends well below the plate so the base is full-width."""
    bl, br = np.array([-HW, -14.0]), np.array([HW, -14.0])
    tip = np.array([6.0 * H / 72, H])
    outer = bez(np.array([HW, 0.0]), np.array([HW + 1.0, H * 0.55]), tip)        # outer edge: fairly straight
    inner = bez(tip, np.array([-HW - 9.0, H * 0.50]), np.array([-HW, 0.0]))       # inner edge: full curve
    p = Polygon(np.vstack([bl, br, outer, inner[1:]]))
    return p.buffer(-7, join_style=1).buffer(7, join_style=1)   # soft, rounded tip

PROF = outline()
INNER = PROF.buffer(-RIM, join_style=1).intersection(Polygon([(-200, 13), (200, 13), (200, 400), (-200, 400)]))
INNER = INNER.buffer(-5, join_style=1).buffer(5, join_style=1)

def poly_sdf(poly, X, Z):
    """Signed distance (negative inside) to a shapely polygon on a 2D grid (vectorised)."""
    v = np.array(poly.exterior.coords)
    P = np.stack([X.ravel(), Z.ravel()], 1)
    d = np.full(len(P), np.inf); s = np.ones(len(P))
    for i in range(len(v) - 1):
        a, b = v[i], v[i + 1]
        e = b - a; w = P - a
        t = np.clip((w @ e) / (e @ e), 0, 1)
        q = w - t[:, None] * e
        d = np.minimum(d, np.einsum("ij,ij->i", q, q))
        c1 = P[:, 1] >= a[1]; c2 = P[:, 1] < b[1]; c3 = e[0] * w[:, 1] > e[1] * w[:, 0]
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s[flip] *= -1
    return (s * np.sqrt(d)).reshape(X.shape)

def smax(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.maximum(a, b) + h * h * k * 0.25

# ----------------------------------------------------------------- sculpt the ear as a signed distance field
r = A.res
xs = np.arange(-HW - 14, HW + 14, r)
ys = np.arange(-YO - 6, YO + 6, r)
zs = np.arange(-6.0, H + 10, r)
X2, Z2 = np.meshgrid(xs, zs, indexing="ij")
d_prof = poly_sdf(PROF, X2, Z2)[:, None, :]           # (nx, 1, nz)
d_in = poly_sdf(INNER, X2, Z2)[:, None, :]
X = xs[:, None, None]; Y = ys[None, :, None]; Z = zs[None, None, :]

zc = np.clip(Z, 0, None)
front = -YO + 0.20 * zc                               # front face leans back toward the tip
back = YO - 0.19 * zc - 5.0 * (X / HW) ** 2 * np.clip(zc / 20, 0, 1)   # domed back
d_front = front - Y                                   # >0 in front of the ear
d_back = Y - back
def round_inter(ds, rr):
    """Intersection of SDFs with every edge (and the tip) filleted to radius rr."""
    ds = [d + rr for d in ds]
    pos = sum(np.maximum(d, 0) ** 2 for d in ds)
    mx = ds[0]
    for d in ds[1:]:
        mx = np.maximum(mx, d)
    return np.sqrt(pos) + np.minimum(mx, 0) - rr
RR = KR * np.clip((Z - 2.0) / 14.0, 0.02, 1.0)        # rounding fades in above the clip (no ledge)
body = round_inter([d_prof, d_front, d_back], RR)
# keep the base exactly flush with the clip right at the plate (no rounding there)
flush = np.maximum(np.maximum(d_prof, -YO - Y), Y - YO)
base_block = np.maximum(flush, Z - 3.0)              # full-depth block right at the clip
body = np.minimum(body, base_block)

# inner-ear cavity: straight walls, flat floor (so the insert can be printed flat), rounded lip at the front
FLOOR = -3.0                                          # y of the cavity floor
lip = np.maximum(0, (front + 4.0) - Y)                # 0 deep inside, grows toward the opening
cav = np.maximum(d_in - 0.12 * lip ** 2, Y - FLOOR)
body = np.maximum(body, -cav)

print("sculpt grid", body.shape)
from scipy.ndimage import gaussian_filter
vol = np.pad(gaussian_filter(body, 0.7), 1, constant_values=10.0)   # light smoothing of the field (no mesh folding)
verts, faces, _, _ = marching_cubes(vol, 0.0, spacing=(r, r, r))
verts += np.array([xs[0], ys[0], zs[0]]) - r
tm = trimesh.Trimesh(verts, faces, process=True)
if tm.volume < 0:
    tm.invert()
ear = Manifold(m3.Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
print("ear status", ear.status(), "tris", ear.num_tri())

# inner-ear insert: flat plate, front face slightly domed by a small rounding
ins_cs = cs_from_shapely(INNER.buffer(-0.2, join_style=1))
def slab_rounded(cs, t, rr=0.8, steps=5):
    parts = [cs.extrude(t - rr)]
    for i in range(steps):
        a1 = (i + 1) / steps
        inset = rr * (1 - np.sqrt(1 - a1 ** 2))
        s = cs.offset(-inset, m3.JoinType.Round)
        parts.append(s.extrude(rr / steps).translate([0, 0, t - rr + rr * i / steps]))
    return Manifold.batch_boolean(parts, m3.OpType.Add)
insert_flat = slab_rounded(ins_cs, INS_T)              # (u=x, v=z, w=thickness) front face at w=INS_T
# as worn: back face on the floor (y=FLOOR), front face toward -y ; map (u,v,w)->(u, FLOOR - w, v)  (det +1)
insert_worn = insert_flat.warp_batch(lambda p: np.column_stack([p[:, 0], FLOOR - p[:, 2], p[:, 1]]))

# ----------------------------------------------------------------- clip (same snap design as v1)
def clip_profile(with_hooks):
    yi = W / 2 + CLR; zb = -T - CLR
    outer = Polygon([(-YO, zb - (HOOK_H if with_hooks else 0)), (YO, zb - (HOOK_H if with_hooks else 0)), (YO, PLATE), (-YO, PLATE)])
    outer = outer.buffer(-1.2, join_style=1).buffer(1.2, join_style=1)
    top = Polygon([(-YO, 0), (YO, 0), (YO, PLATE + 5), (-YO, PLATE + 5)])  # square top corners (ear sits flush)
    outer = outer.union(top.intersection(Polygon([(-YO, 0), (YO, 0), (YO, PLATE), (-YO, PLATE)])))
    prof = outer.difference(Polygon([(-yi, zb), (yi, zb), (yi, 0), (-yi, 0)]))
    for s in (-1, 1):   # hug the chamfered top edges of the band
        prof = prof.union(Polygon([(s * yi, 0.01), (s * (yi - CHAMF), 0.01), (s * yi, -CHAMF)]))
    yh = yi - HOOK
    if with_hooks:
        prof = prof.difference(Polygon([(-yh, zb + 0.01), (yh, zb + 0.01), (yh + HOOK * 0.85, zb - HOOK_H + 0.6),
                                        (YO + 1, zb - HOOK_H - 1), (-YO - 1, zb - HOOK_H - 1), (-yh - HOOK * 0.85, zb - HOOK_H + 0.6)]))
    else:
        prof = prof.difference(Polygon([(-yi, zb - 5), (yi, zb - 5), (yi, zb + 0.01), (-yi, zb + 0.01)]))
    return cs_from_shapely(prof)

def along_x(man, L):
    return man.warp_batch(lambda p: p[:, [2, 0, 1]]).translate([-L / 2, 0, 0])

CLIP_L = 2 * HW - 4
clip = along_x(clip_profile(False).extrude(CLIP_L, n_divisions=40), CLIP_L) + \
       along_x(clip_profile(True).extrude(HOOK_L, n_divisions=20), HOOK_L)
plan = cs_from_shapely(Polygon([(-CLIP_L / 2, -YO), (CLIP_L / 2, -YO), (CLIP_L / 2, YO), (-CLIP_L / 2, YO)])
                       .buffer(-6, join_style=1).buffer(6, join_style=1))
clip = clip ^ plan.extrude(100).translate([0, 0, -50])

# ----------------------------------------------------------------- assemble
def bend(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    return np.column_stack([x, y, z + np.sqrt(np.maximum(R * R - x * x, 1)) - R])

def place_ear(m):
    return m.rotate([0, TILT, 0]).translate([0, 0, PLATE - 0.4])

ear_p = place_ear(ear).trim_by_plane([0, 0, 1], 0.6)
ear_p = ear_p ^ Manifold.cube([400, 2 * YO - 0.06, 400]).translate([-200, -YO + 0.03, -100])   # never wider than the clip at the base
right = (clip + ear_p).refine_to_length(3.0).warp_batch(bend)
left = right.mirror([1, 0, 0])
ins_r = place_ear(insert_worn).refine_to_length(3.0).warp_batch(bend)

# ----------------------------------------------------------------- export
os.makedirs(A.out, exist_ok=True)
def tm_of(man):
    mm = man.to_mesh()
    return trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts, process=True)
ZMIN = {}
def save(man, name):
    t = tm_of(man); ZMIN[name] = float(t.bounds[0][2]); t.apply_translation([0, 0, -t.bounds[0][2]])
    t.export(os.path.join(A.out, name))
    print(f"{name:34s} tris={len(t.faces):7d} watertight={t.is_watertight} size={np.round(t.extents, 1)}")

tag = f"W{W:g}_T{T:g}"
# `right` is built at +X = the wearer's LEFT side
save(right, f"cat_ear_LEFT_{tag}.stl")
save(left, f"cat_ear_RIGHT_{tag}.stl")
save(insert_flat, "inner_ear_insert_LEFT.stl")
save(insert_flat.mirror([1, 0, 0]), "inner_ear_insert_RIGHT.stl")

# ----------------------------------------------------------------- preview (+ collision check on the real band)
def to_mani(tmesh):
    return Manifold(m3.Mesh(vert_properties=np.asarray(tmesh.vertices, np.float32), tri_verts=np.asarray(tmesh.faces, np.uint32)))

if A.band_stl:
    bt = trimesh.load(A.band_stl)
    # STL frame: arch in XY (apex toward +X), width along Z. Fit arch centre, map to ours:
    sec = bt.section(plane_origin=[0, 0, bt.bounds[1][2] / 2], plane_normal=[0, 0, 1])
    P = np.vstack(sec.discrete)[:, :2]
    cy = P[np.argmax(P[:, 0]), 1]
    apex = bt.bounds[1][0]
    v = bt.vertices
    bt = trimesh.Trimesh(np.column_stack([v[:, 1] - cy, v[:, 2] - bt.bounds[1][2] / 2, v[:, 0] - apex]), bt.faces, process=True)
    band = to_mani(bt)
    # top-surface curve along the middle of the band
    sec = bt.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])
    dense = []
    for e in sec.discrete:   # resample every path at 0.2 mm so no angle bin is left with only inner-surface points
        e = e[:, [0, 2]]
        for a, b in zip(e[:-1], e[1:]):
            n = max(2, int(np.hypot(*(b - a)) / 0.2))
            dense.append(a + (b - a) * np.linspace(0, 1, n, endpoint=False)[:, None])
    Q = np.vstack(dense)
    # outer contour ordered by angle around a point well inside the arch (max radius per angle bin)
    C0 = np.array([0.0, -80.0])
    ang = np.arctan2(Q[:, 0] - C0[0], Q[:, 1] - C0[1]); rad = np.hypot(Q[:, 0] - C0[0], Q[:, 1] - C0[1])
    edges = np.linspace(-1.3, 1.3, 400); pts = []
    for a0, a1 in zip(edges[:-1], edges[1:]):
        sel = (ang >= a0) & (ang < a1)
        if sel.any():
            k = np.argmax(np.where(sel, rad, -1)); pts.append(Q[k])
    pts = np.array(pts)
    rr = np.hypot(pts[:, 0] - C0[0], pts[:, 1] - C0[1])
    pts = pts[rr > np.percentile(rr, 30) - 4]                      # drop stray inner points
    xs_, top = pts[:, 0], pts[:, 1]
    seg = np.hypot(np.diff(xs_), np.diff(top)); sarc = np.concatenate([[0], np.cumsum(seg)])
    s0 = np.interp(0, xs_, sarc)
    PLACEMENT = {}
    SEAT = 0.15   # plate rests on the band top; tiny lift so the check measures real clashes, not contact
    def place(man, side):
        s = s0 + side * A.place
        x = np.interp(s, sarc, xs_); z = np.interp(s, sarc, top)
        dx = np.interp(s + 1, sarc, xs_) - np.interp(s - 1, sarc, xs_)
        dz = np.interp(s + 1, sarc, top) - np.interp(s - 1, sarc, top)
        phi = np.degrees(np.arctan2(dz, dx))
        PLACEMENT[side] = dict(x=float(x), z=float(z), phi=float(phi), seat=SEAT)
        return man.translate([0, 0, SEAT]).rotate([0, -phi, 0]).translate([x, 0, z])
else:
    ang_len = 2 * R * 1.4
    band_cs = cs_from_shapely(Polygon([(-W / 2, -T), (W / 2, -T), (W / 2, 0), (-W / 2, 0)]).buffer(-1.5, join_style=1).buffer(1.5, join_style=1))
    band = along_x(band_cs.extrude(ang_len, n_divisions=120), ang_len).warp_batch(
        lambda p: np.column_stack([(R + p[:, 2]) * np.sin(p[:, 0] / R), p[:, 1], (R + p[:, 2]) * np.cos(p[:, 0] / R) - R]))
    th = np.degrees(A.place / R)
    def place(man, side):
        return man.translate([0, 0, R]).rotate([0, side * th, 0]).translate([0, 0, -R])

R_w, L_w = place(right, 1), place(left, -1)
for nm, part in [("right", R_w), ("left", L_w)]:
    clash = (part ^ band).volume()
    print(f"collision {nm} ear vs headband: {clash:.2f} mm^3")
scene = trimesh.Scene()
for man, name in [(band, "band"), (R_w, "right"), (place(ins_r, 1), "right_insert"),
                  (L_w, "left"), (place(ins_r.mirror([1, 0, 0]), -1), "left_insert")]:
    scene.add_geometry(tm_of(man), node_name=name)
scene.export(os.path.join(A.out, "preview_as_worn.glb"))
print("preview written")
if A.band_stl:
    import json
    json.dump(dict(placement={str(k): v for k, v in PLACEMENT.items()}, zmin=ZMIN, tag=tag),
              open(os.path.join(A.out, "placement.json"), "w"), indent=1)
