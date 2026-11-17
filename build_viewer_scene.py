"""
Builds the data for the realistic viewer: real headband + strap anchors (from the Printables
HS35 v2 STLs), the cat ears in their PRINT orientation with a placement matrix (so the viewer
can draw true layer lines), the inner-ear inserts, and measured attachment points.

python build_viewer_scene.py --band band.stl --velcro-l velcro_l.stl --velcro-r velcro_r.stl \
    --ears out_final_v3 --out viewer_scene.glb
"""
import argparse, json, os
import numpy as np
import trimesh

ap = argparse.ArgumentParser()
ap.add_argument("--band", required=True)
ap.add_argument("--velcro-l", required=True)
ap.add_argument("--velcro-r", required=True)
ap.add_argument("--ears", default="out_final_v3")
ap.add_argument("--out", default="viewer_scene.glb")
ap.add_argument("--ear-faces", type=int, default=110000)
ap.add_argument("--public", action="store_true", help="replace the Printables headband/anchor meshes with a stand-in rebuilt from measurements")
A = ap.parse_args()

# ---- STL frame -> viewer frame (X across head, Y front(-)/back(+), Z up, band apex top at origin)
raw = trimesh.load(A.band)
sec = raw.section(plane_origin=[0, 0, raw.bounds[1][2] / 2], plane_normal=[0, 0, 1])
P = np.vstack(sec.discrete)[:, :2]
CY = P[np.argmax(P[:, 0]), 1]
APEX = raw.bounds[1][0]
HALFW = raw.bounds[1][2] / 2
def to_view(v):
    return np.column_stack([v[:, 1] - CY, v[:, 2] - HALFW, v[:, 0] - APEX])

def conv(path):
    m = trimesh.load(path)
    return trimesh.Trimesh(to_view(m.vertices), m.faces, process=True)

band = conv(A.band)
vel_l, vel_r = conv(A.velcro_l), conv(A.velcro_r)
# The STL "velcro_r" sits at -X (wearer's right) - sanity check
assert vel_r.vertices[:, 0].mean() < 0 < vel_l.vertices[:, 0].mean()

R0 = 88.0
def arch_uv(m):
    v = m.vertices
    ang = np.arctan2(v[:, 0], v[:, 2] + R0)
    return np.column_stack([ang * R0, v[:, 1]])           # mm along the band, mm across

meta = {}
# ---- band top curve (for the CORSAIR print) and band-end / anchor geometry
s = band.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])
dense = []
for e in s.discrete:
    e = e[:, [0, 2]]
    for a, b in zip(e[:-1], e[1:]):
        n = max(2, int(np.hypot(*(b - a)) / 0.25))
        dense.append(a + (b - a) * np.linspace(0, 1, n, endpoint=False)[:, None])
Q = np.vstack(dense)
C0 = np.array([0, -80.0])
ang = np.arctan2(Q[:, 0] - C0[0], Q[:, 1] - C0[1]); rad = np.hypot(Q[:, 0] - C0[0], Q[:, 1] - C0[1])
top = []
for a0 in np.linspace(-1.45, 1.45, 300):
    sel = np.abs(ang - a0) < 0.006
    if sel.any():
        k = np.argmax(np.where(sel, rad, -1)); top.append(Q[k].tolist())
meta["band_top_curve_xz"] = top

for side, vm in (("L", vel_l), ("R", vel_r)):
    v = vm.vertices
    sx = 1 if side == "L" else -1
    tipx = v[:, 0] * sx
    tip = v[tipx < tipx.min() + 1.0].mean(0)                 # inner (strap) end of the anchor
    # local direction of the anchor near its tip
    near = v[(tipx > tipx.min() + 4) & (tipx < tipx.min() + 9)].mean(0)
    meta[f"anchor_tip_{side}"] = tip.tolist()
    meta[f"anchor_dir_{side}"] = (tip - near).tolist()
    bv = band.vertices[band.vertices[:, 0] * sx > 0]
    end = bv[np.argmin(bv[:, 2])]
    meta[f"band_end_{side}"] = end.tolist()
    lowz = bv[:, 2].min()
    meta[f"band_end_box_{side}"] = [bv[bv[:, 2] < lowz + 15].min(0).tolist(), bv[bv[:, 2] < lowz + 15].max(0).tolist()]

# ---- ears: print-frame meshes + placement matrices
pl = json.load(open(os.path.join(A.ears, "placement.json")))
tag = pl["tag"]
def ry(deg):
    a = np.radians(deg); c, s_ = np.cos(a), np.sin(a)
    M = np.eye(4); M[0, 0] = c; M[0, 2] = s_; M[2, 0] = -s_; M[2, 2] = c
    return M
def tr(x, y, z):
    M = np.eye(4); M[:3, 3] = [x, y, z]; return M

scene = trimesh.Scene()
def add(m, name, uv=None, matrix=None):
    if uv is not None:
        m.visual = trimesh.visual.TextureVisuals(uv=uv)
    scene.add_geometry(m, node_name=name, geom_name=name, transform=matrix)

def sweep(path_xz, profile, close_ends=True):
    """Sweep a 2D profile [(u across Y, d depth below the path)] along a planar XZ path.
    Depth goes against the outward normal (away from the arch centre)."""
    from shapely.geometry import Polygon as SP
    P = np.asarray(path_xz, float)
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    N = np.column_stack([T[:, 1], -T[:, 0]])
    flip = np.einsum("ij,ij->i", N, P - np.array([0.0, -95.0])) < 0
    N[flip] *= -1
    prof = np.asarray(profile, float); k = len(prof)
    verts, uvs, faces = [], [], []
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    for i in range(len(P)):
        for u, d in prof:
            x, z = P[i] - N[i] * d
            verts.append([x, u, z]); uvs.append([s[i], u])
    for i in range(len(P) - 1):
        for j in range(k):
            a, b = i * k + j, i * k + (j + 1) % k
            c, d_ = a + k, b + k
            faces += [[a, c, b], [b, c, d_]]
    m = trimesh.Trimesh(verts, faces, process=False)
    uv = np.array(uvs)
    if close_ends:
        v2, f2 = trimesh.creation.triangulate_polygon(SP(prof))
        idx = [np.argmin(np.linalg.norm(prof - q, axis=1)) for q in v2]
        last = (len(P) - 1) * k
        caps = [[idx[a], idx[c], idx[b]] for a, b, c in f2] + [[last + idx[a], last + idx[b], last + idx[c]] for a, b, c in f2]
        m = trimesh.Trimesh(verts, np.vstack([faces, caps]), process=False)
    m.fix_normals()
    return m, uv

if A.public:
    # Publishable stand-in for the Printables headband: rebuilt from the measurements taken above,
    # so the original model file is not redistributed.
    C = np.array([0.0, -95.0])
    rad = np.hypot(Q[:, 0] - C[0], Q[:, 1] - C[1]); angq = np.arctan2(Q[:, 0] - C[0], Q[:, 1] - C[1])
    outer = []
    for a0 in np.linspace(-1.72, 1.72, 520):
        sel = np.abs(angq - a0) < 0.004
        if sel.any():
            kk = np.argmax(np.where(sel, rad, -1)); outer.append(Q[kk])
    outer = np.array(outer)
    outer = np.column_stack([np.convolve(outer[:, 0], np.ones(5) / 5, "same"), np.convolve(outer[:, 1], np.ones(5) / 5, "same")])[3:-3]
    C_CH = [(-17.8, 3.0), (-14.8, 0.0), (14.8, 0.0), (17.8, 3.0), (17.8, 7.5), (16.2, 7.5), (16.2, 3.0), (-16.2, 3.0), (-16.2, 7.5), (-17.8, 7.5)]
    SOLID = [(-17.8, 3.0), (-14.8, 0.0), (14.8, 0.0), (17.8, 3.0), (17.8, 7.5), (-17.8, 7.5)]
    arch = outer[outer[:, 1] > -76]
    parts_b, uvs_b = [], []
    m, uv = sweep(arch, C_CH); parts_b.append(m); uvs_b.append(uv)
    for sgn in (1, -1):
        pad_ = outer[(outer[:, 1] <= -74) & (np.sign(outer[:, 0]) == sgn)]
        pad_ = pad_[np.argsort(-pad_[:, 1])]
        m, uv = sweep(pad_, SOLID); parts_b.append(m); uvs_b.append(uv)
        a = pad_[-1]; b = np.array([sgn * 104.0, -124.0])
        tab = np.linspace(a, b, 12)
        m, uv = sweep(tab, [(-9, 0.5), (9, 0.5), (9, 6.5), (-9, 6.5)]); parts_b.append(m); uvs_b.append(uv)
        hub = trimesh.creation.cylinder(radius=7.5, height=7.0, sections=48)
        hub.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
        hub.apply_translation([sgn * 104.0, 0, -124.0])
        parts_b.append(hub); uvs_b.append(np.zeros((len(hub.vertices), 2)))
    band = trimesh.util.concatenate(parts_b); band_uv = np.vstack(uvs_b)
    an = {}
    for side, sgn in (("L", 1), ("R", -1)):
        tip = np.array(meta[f"anchor_tip_{side}"])[[0, 2]]
        st = np.array([sgn * 85.0, -104.0]); ctrl = np.array([sgn * 82.0, -78.0])
        tt = np.linspace(0, 1, 40)[:, None]
        path = (1 - tt) ** 2 * st + 2 * (1 - tt) * tt * ctrl + tt ** 2 * tip
        an[side] = sweep(path, [(-16, 0), (16, 0), (16, 2), (-16, 2)])
    add(band, "band", uv=band_uv)
    add(an["L"][0], "anchor_L", uv=an["L"][1]); add(an["R"][0], "anchor_R", uv=an["R"][1])
else:
    add(band, "band", uv=arch_uv(band))
    add(vel_l, "anchor_L", uv=arch_uv(vel_l)); add(vel_r, "anchor_R", uv=arch_uv(vel_r))

preview = trimesh.load(os.path.join(A.ears, "preview_as_worn.glb"))
pg = {n: preview.geometry[preview.graph.get(n)[1]] for n in preview.graph.nodes_geometry}
for side, key, fname in (("L", "1", f"cat_ear_LEFT_{tag}.stl"), ("R", "-1", f"cat_ear_RIGHT_{tag}.stl")):
    p = pl["placement"][key]
    m = trimesh.load(os.path.join(A.ears, fname))
    if len(m.faces) > A.ear_faces:
        m = m.simplify_quadric_decimation(face_count=A.ear_faces)
    M = tr(p["x"], 0, p["z"]) @ ry(-p["phi"]) @ tr(0, 0, p["seat"] + pl["zmin"][fname])
    # verify against the as-worn preview mesh
    world = m.copy(); world.apply_transform(M)
    ref = pg["right" if side == "L" else "left"]
    err = np.abs(world.bounds - ref.bounds).max()
    print(f"ear {side}: {len(m.faces)} faces, placement check max bbox error {err:.2f} mm")
    assert err < 1.0
    add(m, f"ear_{side}", matrix=M)
    ins = pg["right_insert" if side == "L" else "left_insert"].copy()
    add(ins, f"insert_{side}")

# ---- earcups and pads, sculpted as distance fields to match Corsair's product photos
from skimage.measure import marching_cubes
from scipy.ndimage import gaussian_filter

CUP = dict(x=111.0, z=-186.0, a=41.0, b=52.0, n=2.35)   # centre (world), semi-axes front/back (a) and up/down (b)
DISC = dict(y=6.0, z=-3.0, r=27.6)                      # textured disc, offset toward the back
meta["cup"] = CUP; meta["disc"] = DISC

def sq_sdf(Y, Z, a, b, n):
    """approx. signed distance to a superellipse outline (negative inside)"""
    f = (np.abs(Y / a) ** n + np.abs(Z / b) ** n) ** (1 / n)
    return (f - 1) * min(a, b) * 0.95

def round_inter(ds, rr):
    ds = [d + rr for d in ds]; pos = sum(np.maximum(d, 0) ** 2 for d in ds); mx = ds[0]
    for d in ds[1:]: mx = np.maximum(mx, d)
    return np.sqrt(pos) + np.minimum(mx, 0) - rr

def mc(field, origin, r, sigma=0.6):
    vol = np.pad(gaussian_filter(field, sigma), 1, constant_values=10.0)
    v, f, _, _ = marching_cubes(vol, 0.0, spacing=(r, r, r))
    m = trimesh.Trimesh(v + np.asarray(origin) - r, f, process=True)
    if m.volume < 0: m.invert()
    return m

r = 0.38
xs = np.arange(-2, 30, r, dtype=np.float32); ys = np.arange(-46, 46, r, dtype=np.float32); zs = np.arange(-58, 58, r, dtype=np.float32)
X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
outline = sq_sdf(Y, Z, CUP["a"], CUP["b"], CUP["n"])
# Shape from close-ups of the real cup: FLAT outer face, crisp ~2 mm edge, near-straight side wall
# that tapers slightly toward the face, a parting-line groove at the pad seam, the textured disc set
# in a glossy sloped dish, and a long recessed panel along the front edge carrying "// HS35".
D = 18.5                                             # depth of the shell from the pad seam to the face
outline_t = outline + 2.6 * np.clip(X / D, 0, 1)     # side wall tapers ~2.6 mm toward the face
shell = np.maximum(round_inter([outline_t, X - D], 3.2), -X)
groove = np.maximum(np.abs(X - 1.5) - 0.45, -outline_t - 0.55)   # parting line just above the pad seam
shell = np.maximum(shell, -groove)
dd = np.sqrt((Y - DISC["y"]) ** 2 + (Z - DISC["z"]) ** 2)
x_floor = D - 2.6
meta["disc_floor_x"] = float(x_floor)
recess = np.maximum(dd - (DISC["r"] + 0.45) - (X - x_floor) * 1.6, x_floor - X)   # wide sloped dish (glossy bezel)
meta["bezel"] = dict(r0=DISC["r"] + 0.45, x0=float(x_floor), slope=1.6, x1=float(D))
shell = np.maximum(shell, -recess)
th = np.arctan2(Z - DISC["z"], Y - DISC["y"])
arc_r, a0, a1 = 35.2, np.radians(112), np.radians(190)
thw = np.where(th < 0, th + 2 * np.pi, th)
in_range = (thw > a0) & (thw < a1)
end0 = np.hypot(Y - (DISC["y"] + arc_r * np.cos(a0)), Z - (DISC["z"] + arc_r * np.sin(a0)))
end1 = np.hypot(Y - (DISC["y"] + arc_r * np.cos(a1)), Z - (DISC["z"] + arc_r * np.sin(a1)))
dist_arc = np.where(in_range, np.abs(dd - arc_r), np.minimum(end0, end1))
panel = np.maximum(dist_arc - 4.4, (D - 1.1) - X)
shell = np.maximum(shell, -panel)
mid = np.radians(151)
meta["pill"] = dict(x=float(D - 1.1), y=float(DISC["y"] + arc_r * np.cos(mid)), z=float(DISC["z"] + arc_r * np.sin(mid)), ang=float(mid))
cupL = mc(shell, (xs[0], ys[0], zs[0]), r).simplify_quadric_decimation(face_count=90000)
print("cup shell", len(cupL.faces), cupL.is_watertight)

# pad: fat rounded ring that follows the cup outline, pointing toward the head (-x)
xp = np.arange(-30, 2, r, dtype=np.float32)
Xp, Yp, Zp = np.meshgrid(xp, ys, zs, indexing="ij")
o_out = sq_sdf(Yp, Zp, CUP["a"] + 0.6, CUP["b"] + 0.6, CUP["n"])   # fabric bulges just past the shell rim
o_in = sq_sdf(Yp, Zp, 20.0, 30.0, 2.2)
bulge = 1.8 * np.clip(1 - ((Xp + 12) / 14) ** 2, 0, 1)
pad = round_inter([o_out - bulge, -o_in - bulge, -Xp - 25.5, Xp - 0.6], 9.0)
padL = mc(pad, (xp[0], ys[0], zs[0]), r, sigma=0.8).simplify_quadric_decimation(face_count=70000)
print("pad", len(padL.faces), padL.is_watertight)
def pad_uv(m):
    v = m.vertices; thp = np.arctan2(v[:, 2] / (CUP["b"] / CUP["a"]), v[:, 1])
    rad = np.hypot(v[:, 1], v[:, 2] / (CUP["b"] / CUP["a"]))
    phi = np.arctan2(v[:, 0] + 12.5, rad - 31.0)
    return np.column_stack([thp * 34.0, phi * 13.0])
for side, s in (("L", 1), ("R", -1)):
    M = np.eye(4); M[0, 0] = s; M[:3, 3] = [s * CUP["x"], 0, CUP["z"]]
    c = cupL.copy(); c.apply_transform(M); p = padL.copy(); uvp = pad_uv(p); p.apply_transform(M)
    assert c.volume > 0 and p.volume > 0
    add(c, f"cup_{side}"); add(p, f"pad_{side}", uv=uvp)

scene.export(A.out)
meta["ear_tag"] = tag
json.dump(meta, open(os.path.splitext(A.out)[0] + ".json", "w"))
print("wrote", A.out, os.path.getsize(A.out) / 1e6, "MB")
