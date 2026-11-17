"""
v3: SPLIT, SUPPORT-FREE cat ears for the Corsair HS35 v2 / HS35 Surround v2.

Per side: 1 ear (prints flat on its back, no supports), 1 clip (prints standing on its end so the
snap hooks flex ALONG the layer lines), 1 inner-ear insert (prints flat). NO GLUE:
  * ear -> clip: the ear slides onto a dovetail rail from the outer end until the rail hits the groove's
    closed end, and a spring finger in the back of the ear's base clicks a ridge into a notch in the clip.
    The finger lies in the ear's layer plane, so it flexes along the layers. Pull firmly outward to remove it.
  * insert -> ear: the insert pushes into an exact pocket past three small retaining tabs (click).
    To remove it, pry it out at the lip with a fingernail.

Run:  python cat_ears_v3.py [--band-stl corsair_hs_35_v2_headband.stl] [--place 50]
Defaults are measured from the HS35 v2 headband model (35.6 mm wide, 7.5 mm edge, 91.5 mm arch radius).
Outputs print-oriented STLs + an as-worn preview .glb + placement.json into ./out_v3/

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
ap.add_argument("--height", type=float, default=58.0, help="ear height above the clip (mm); base width scales with it")
ap.add_argument("--res", type=float, default=0.45, help="sculpt resolution (mm), smaller = smoother/slower")
ap.add_argument("--out", default="out_v3")
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
zs = np.arange(-16.0, H + 10, r)
X2, Z2 = np.meshgrid(xs, zs, indexing="ij")
d_prof = poly_sdf(PROF, X2, Z2)[:, None, :]           # (nx, 1, nz)
d_in = poly_sdf(INNER, X2, Z2)[:, None, :]
X = xs[:, None, None]; Y = ys[None, :, None]; Z = zs[None, None, :]

zc = np.clip(Z, 0, None)
front = -YO + 0.20 * zc                               # front face leans back toward the tip
ZMIN_EAR = -12.0                                      # lowest point the ear base needs to reach
back = YO - 0.19 * (Z - ZMIN_EAR)                     # ONE flat plane: the ear prints lying on it
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
body = round_inter([d_prof, d_front], RR)             # soft, puffy front and sides
CH = 2.5                                              # 45-degree chamfer around the flat back (prints without support)
body = np.maximum(np.maximum(body, d_back), 0.574 * d_back + 0.819 * d_prof + CH * 0.7)   # 35 deg from vertical when printed
body = np.maximum(body, -YO - Y)                      # never wider than the clip at the front

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
INS_POCKET = 0.08                                      # radial clearance of the insert in its pocket
TAB_IN = 0.12                                          # how far the retaining tabs overlap the insert edge
ins_cs = cs_from_shapely(INNER.buffer(0.0, join_style=1))
def slab_rounded(cs, t, rr=0.8, steps=5):
    parts = [cs.extrude(t - rr)]
    for i in range(steps):
        a1 = (i + 1) / steps
        inset = rr * (1 - np.sqrt(1 - a1 ** 2))
        s = cs.offset(-inset, m3.JoinType.Round)
        parts.append(s.extrude(rr / steps).translate([0, 0, t - rr + rr * i / steps]))
    return Manifold.batch_boolean(parts, m3.OpType.Add)
insert_flat = slab_rounded(ins_cs, INS_T)              # (u=x, v=z, w=thickness) front face at w=INS_T
lead = Manifold.batch_boolean([ins_cs.offset(-0.4 + 0.1 * i, m3.JoinType.Round).extrude(0.1).translate([0, 0, 0.1 * i])
                               for i in range(4)], m3.OpType.Add)
edge_ring = ins_cs.offset(5, m3.JoinType.Round).extrude(0.4) - ins_cs.offset(-0.4, m3.JoinType.Round).extrude(0.4)
insert_flat = (insert_flat - edge_ring) + lead      # 0.4 mm chamfer on the back edge = lead-in past the tabs
# as worn: back face on the floor (y=FLOOR), front face toward -y ; map (u,v,w)->(u, FLOOR - w, v)  (det +1)
to_worn = lambda m: m.warp_batch(lambda p: np.column_stack([p[:, 0], FLOOR - p[:, 2], p[:, 1]]))
insert_worn = to_worn(insert_flat)

# exact pocket for the insert (CSG, so the 0.1 mm fits are not blurred by the sculpt grid) ...
pocket = cs_from_shapely(INNER.buffer(INS_POCKET, join_style=1)).extrude(INS_T + 0.12).translate([0, 0, -0.02])
# ... and three short retaining tabs just in front of it (tip + both lower corners), stepped like a chamfer
ib = np.array(INNER.exterior.coords)
tab_at = [ib[np.argmax(ib[:, 1])], ib[np.argmin(ib[:, 0] + 0.6 * ib[:, 1])], ib[np.argmax(ib[:, 0] - 0.6 * ib[:, 1])]]
tab_zone = CrossSection.batch_boolean([CrossSection.circle(3.5, 32).translate(list(c)) for c in tab_at], m3.OpType.Add)
tabs = []
w0 = INS_T + 0.1
for off, t0, t1 in ((-TAB_IN, 0.0, 0.5), (-TAB_IN / 2, 0.5, 0.8)):
    ring = cs_from_shapely(INNER.buffer(1.2, join_style=1)) - cs_from_shapely(INNER.buffer(off, join_style=1))
    tabs.append((ring ^ tab_zone).extrude(t1 - t0).translate([0, 0, w0 + t0]))
tabs = Manifold.batch_boolean(tabs, m3.OpType.Add)
ear = ear - to_worn(pocket) + to_worn(tabs)
print("ear pocket+tabs", ear.status(), "tabs at", np.round(tab_at, 1).tolist())

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
# 45-degree chamfered corners (not rounded): the clip prints standing on its end, and a chamfer needs no support
c4 = 4.0; L2 = CLIP_L / 2
plan = cs_from_shapely(Polygon([(-L2 + c4, -YO), (L2 - c4, -YO), (L2, -YO + c4), (L2, YO - c4), (L2 - c4, YO), (-L2 + c4, YO), (-L2, YO - c4), (-L2, -YO + c4)]))
clip = clip ^ plan.extrude(100).translate([0, 0, -50])
# dovetail rail on top of the clip; the ear has the matching groove (0.15 mm side / 0.25 mm top clearance)
# Asymmetric key: the +Y flank is a true dovetail undercut (it faces the bed when the ear prints, so its angle is free);
# the -Y flank tapers in at 45 deg, so in the ear's print orientation the groove's "ceiling" is self-supporting.
def key(gap, top, z0):
    zz = lambda zr: PLATE + zr
    return cs_from_shapely(Polygon([(-(5.0 - gap - z0), zz(z0)), (4.0 - gap + 0.6 * z0, zz(z0)),
                                    (4.0 - gap + 0.6 * top, zz(top)), (-(5.0 - gap - top), zz(top))]))
rail = along_x(key(0.15, 2.95, -0.3).extrude(CLIP_L, n_divisions=40), CLIP_L) ^ plan.extrude(100).translate([0, 0, -50])
GEND = CLIP_L / 2 + 0.15                     # groove is CLOSED at the ear's outer (+x) end: the rail end is the stop
groove = along_x(key(0.0, 3.2, -0.02).extrude(100 + GEND, n_divisions=80), 100 + GEND).translate([(GEND - 100) / 2, 0, 0])
clip = clip + rail

# ---- ear click: a spring finger in the back of the ear's base (ear frame after placement) + a notch in the clip
XA = 10.0                                   # ridge apex, x from the ear centre (outer half of the LEFT ear)
YF, FT, FS, FG = 13.0, 2.0, 1.0, 1.0        # finger front edge y, thickness, slot above it, end/side gaps
FX0, FX1 = -4.0, 12.0                       # finger root / free end
RH = 0.6                                    # ridge height
ZT = PLATE + FT + FS
def xz_prism(pts, y0, y1):
    """Polygon in (x, z) extruded along y from y0 to y1."""
    return cs_from_shapely(Polygon(pts)).extrude(y1 - y0).warp_batch(lambda p: np.column_stack([p[:, 0], y1 - p[:, 2], p[:, 1]]))   # det +1
def yz_prism(pts, x0, x1):
    """Polygon in (y, z) extruded along x from x0 to x1."""
    return cs_from_shapely(Polygon(pts)).extrude(x1 - x0).warp_batch(lambda p: np.column_stack([p[:, 2] + x0, p[:, 0], p[:, 1]]))
# void around the finger; its front wall leans 45 deg so it prints without support
f_void = yz_prism([(YF - FG - (ZT - PLATE + 1), PLATE - 1), (60, PLATE - 1), (60, ZT), (YF - FG, ZT)], FX0, FX1 + FG) -          Manifold.cube([FX1 - FX0 + 1, 60 - YF, FT + 1]).translate([FX0 - 1, YF, PLATE - 1])
t35, t40 = np.tan(np.radians(35)), np.tan(np.radians(40))
ridge = xz_prism([(XA - RH / t35, PLATE + 0.3), (XA - RH / t35, PLATE), (XA, PLATE - RH), (XA + RH / t40, PLATE), (XA + RH / t40, PLATE + 0.3)],
                 YF + 0.4, 17.0)       # gentle 35 deg lead-in face toward the centre, 40 deg holding face outward
ND = 0.75                               # notch depth; its 40 deg outer flank preloads the ridge by 0.08 mm
XN = XA - 0.08 + (RH - ND) / t40
def notch(xc):
    return xz_prism([(xc - ND / t40, PLATE + 0.5), (xc - ND / t40, PLATE), (xc, PLATE - ND), (xc + ND / t40, PLATE), (xc + ND / t40, PLATE + 0.5)],
                    YF - 0.5, YO + 1)
clip = clip - notch(XN) - notch(-XN)        # both ends: the same printed clip serves the left and right ear


# ----------------------------------------------------------------- assemble (clip-local frame: plate top follows the arch)
def bend(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    return np.column_stack([x, y, z + np.sqrt(np.maximum(R * R - x * x, 1)) - R])

def place_ear(m):
    return m.rotate([0, TILT, 0]).translate([0, 0, PLATE - 0.4])

clip_b = clip.refine_to_length(3.0).warp_batch(bend)
below = Manifold.cube([200, 80, 80]).translate([-100, -40, PLATE - 80]).refine_to_length(3.0).warp_batch(bend)
groove_b = groove.refine_to_length(3.0).warp_batch(bend)
# the ear itself is NOT warped (so its back stays one flat plane); only its base is cut to the arch
bendm = lambda m, l=1.0: m.refine_to_length(l).warp_batch(bend)
earL = place_ear(ear) - below - groove_b - bendm(f_void) + bendm(ridge, 0.5)
earR = earL.mirror([1, 0, 0])
clipR = clip_b.mirror([1, 0, 0])
ins_L = place_ear(insert_worn)        # inserts sit on the (flat) cavity floor
ins_R = ins_L.mirror([1, 0, 0])

# ----------------------------------------------------------------- print orientations
os.makedirs(A.out, exist_ok=True)
def tm_of(man):
    mm = man.to_mesh()
    t = trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts, process=True)
    parts = t.split(only_watertight=False)
    if len(parts) > 1:      # drop zero-volume slivers left by coincident boolean faces
        t = trimesh.util.concatenate([p for p in parts if abs(p.volume) > 0.5 or len(p.faces) > 200])
    return t
def unit(v):
    v = np.asarray(v, float); return v / np.linalg.norm(v)
def ry(deg):
    a = np.radians(deg); c, s_ = np.cos(a), np.sin(a)
    return np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])
n_back = ry(TILT) @ unit([0, 1, 0.19])     # outward normal of the ear's flat back (clip-local)
PRINT = {}
def save_print(man, name, down):
    """Orient so `down` (unit vector in the part frame) points at the bed; record the print->part matrix."""
    t = tm_of(man)
    Rm = trimesh.geometry.align_vectors(unit(down), [0, 0, -1])
    t.apply_transform(Rm)
    c = t.bounds.mean(0); sh = np.array([-c[0], -c[1], -t.bounds[0][2]])
    t.apply_translation(sh)
    Mprint = trimesh.transformations.translation_matrix(sh) @ Rm
    PRINT[name] = np.linalg.inv(Mprint).tolist()
    t.export(os.path.join(A.out, name))
    print(f"{name:30s} tris={len(t.faces):7d} watertight={t.is_watertight} size={np.round(t.extents, 1)}")

tag = f"W{W:g}_T{T:g}"
# +X is the wearer's LEFT
save_print(earL, "ear_LEFT.stl", n_back)
save_print(earR, "ear_RIGHT.stl", n_back * np.array([-1, 1, 1]))
CLIP_NAME = f"clip_{tag}_print_x2.stl"
save_print(clip_b, CLIP_NAME, [-1, 0, 0])            # stands on its end: every layer is the full clip profile
save_print(insert_flat, "inner_ear_insert_LEFT.stl", [0, 0, -1])
save_print(insert_flat.mirror([1, 0, 0]), "inner_ear_insert_RIGHT.stl", [0, 0, -1])

def overhang_report(name):
    t = trimesh.load(os.path.join(A.out, name))
    nz = t.face_normals[:, 2]; cz = t.triangles_center[:, 2]
    bad = (nz < -np.cos(np.radians(45)) - 1e-3) & (cz > 0.4)
    print(f"  {name}: downward area steeper than 45 deg (not on the bed): {t.area_faces[bad].sum():.1f} mm^2 of {t.area:.0f} mm^2")
for n in ("ear_LEFT.stl", CLIP_NAME, "inner_ear_insert_LEFT.stl"):
    overhang_report(n)

# ----------------------------------------------------------------- preview (+ collision check on the real band)
def to_mani(tmesh):
    return Manifold(m3.Mesh(vert_properties=np.asarray(tmesh.vertices, np.float32), tri_verts=np.asarray(tmesh.faces, np.uint32)))
if A.band_stl:
    bt = trimesh.load(A.band_stl)
    sec = bt.section(plane_origin=[0, 0, bt.bounds[1][2] / 2], plane_normal=[0, 0, 1])
    P = np.vstack(sec.discrete)[:, :2]
    cy = P[np.argmax(P[:, 0]), 1]; apex = bt.bounds[1][0]; v = bt.vertices
    bt = trimesh.Trimesh(np.column_stack([v[:, 1] - cy, v[:, 2] - bt.bounds[1][2] / 2, v[:, 0] - apex]), bt.faces, process=True)
    band = to_mani(bt)
    sec = bt.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])
    dense = []
    for e in sec.discrete:
        e = e[:, [0, 2]]
        for a, b in zip(e[:-1], e[1:]):
            n = max(2, int(np.hypot(*(b - a)) / 0.2))
            dense.append(a + (b - a) * np.linspace(0, 1, n, endpoint=False)[:, None])
    Q = np.vstack(dense)
    C0 = np.array([0.0, -80.0])
    ang = np.arctan2(Q[:, 0] - C0[0], Q[:, 1] - C0[1]); rad = np.hypot(Q[:, 0] - C0[0], Q[:, 1] - C0[1])
    edges = np.linspace(-1.3, 1.3, 400); pts = []
    for a0, a1 in zip(edges[:-1], edges[1:]):
        sel = (ang >= a0) & (ang < a1)
        if sel.any():
            k = np.argmax(np.where(sel, rad, -1)); pts.append(Q[k])
    pts = np.array(pts)
    rr = np.hypot(pts[:, 0] - C0[0], pts[:, 1] - C0[1])
    pts = pts[rr > np.percentile(rr, 30) - 4]
    xs_, top = pts[:, 0], pts[:, 1]
    sarc = np.concatenate([[0], np.cumsum(np.hypot(np.diff(xs_), np.diff(top)))])
    s0 = np.interp(0, xs_, sarc)
    SEAT = 0.15
    def place_matrix(side):
        s = s0 + side * A.place
        x = np.interp(s, sarc, xs_); z = np.interp(s, sarc, top)
        dx = np.interp(s + 1, sarc, xs_) - np.interp(s - 1, sarc, xs_)
        dz = np.interp(s + 1, sarc, top) - np.interp(s - 1, sarc, top)
        phi = np.degrees(np.arctan2(dz, dx))
        M = np.eye(4); M[:3, :3] = ry(-phi); M[:3, 3] = [x, 0, z]
        T0 = np.eye(4); T0[2, 3] = SEAT
        return M @ T0
else:
    band = None
    def place_matrix(side):
        th = side * A.place / R
        M = np.eye(4); M[:3, :3] = ry(np.degrees(th)); M[:3, 3] = [R * np.sin(th), 0, R * np.cos(th) - R]
        return M
def tf(man, M):
    return man.transform(np.asarray(M)[:3, :])
ML, MR = place_matrix(1), place_matrix(-1)
world = {"ear_L": tf(earL, ML), "clip_L": tf(clip_b, ML), "insert_L": tf(ins_L, ML),
         "ear_R": tf(earR, MR), "clip_R": tf(clipR, MR), "insert_R": tf(ins_R, MR)}
scene = trimesh.Scene()
if band is not None:
    scene.add_geometry(tm_of(band), node_name="band")
    for side in "LR":
        clash = ((world[f"ear_{side}"] + world[f"clip_{side}"]) ^ band).volume()
        fit = (world[f"ear_{side}"] ^ world[f"clip_{side}"]).volume()
        print(f"side {side}: clash with headband {clash:.2f} mm^3, ear/clip interference {fit:.2f} mm^3")
for k, m in world.items():
    scene.add_geometry(tm_of(m), node_name=k)
scene.export(os.path.join(A.out, "preview_as_worn.glb"))
import json
json.dump(dict(placement={"L": ML.tolist(), "R": MR.tolist()}, print_to_part=PRINT, tag=tag, clip=CLIP_NAME),
          open(os.path.join(A.out, "placement.json"), "w"), indent=1)
print("preview + placement written")
