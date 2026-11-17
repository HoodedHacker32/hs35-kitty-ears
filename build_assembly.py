"""
Data for the animated assembly guide (assembly.html).

Packs the printed parts in their PRINT orientation, the real headband (and strap anchors), and for
every part: its pose on a build plate and its final pose on the headset. Final poses are checked
against the as-worn preview from cat_ears_v3.py.

python build_assembly.py --band band.stl --velcro-l l.stl --velcro-r r.stl --ears out_v3 --out assembly_scene.glb
"""
import argparse, json, os
import numpy as np
import trimesh

ap = argparse.ArgumentParser()
ap.add_argument("--band", required=True)
ap.add_argument("--velcro-l", required=True)
ap.add_argument("--velcro-r", required=True)
ap.add_argument("--ears", default="out_v3")
ap.add_argument("--out", default="assembly_scene.glb")
ap.add_argument("--ear-faces", type=int, default=70000)
A = ap.parse_args()

# same STL -> viewer frame mapping as build_viewer_scene.py
raw = trimesh.load(A.band)
sec = raw.section(plane_origin=[0, 0, raw.bounds[1][2] / 2], plane_normal=[0, 0, 1])
P = np.vstack(sec.discrete)[:, :2]
CY = P[np.argmax(P[:, 0]), 1]; APEX = raw.bounds[1][0]; HALFW = raw.bounds[1][2] / 2
def conv(path):
    m = trimesh.load(path)
    v = m.vertices
    return trimesh.Trimesh(np.column_stack([v[:, 1] - CY, v[:, 2] - HALFW, v[:, 0] - APEX]), m.faces, process=True)

pl = json.load(open(os.path.join(A.ears, "placement.json")))
P2P = {k: np.array(v) for k, v in pl["print_to_part"].items()}
ML, MR = np.array(pl["placement"]["L"]), np.array(pl["placement"]["R"])
FLIPX = np.diag([-1.0, 1, 1, 1])

# constants of cat_ears_v3.py needed to place the flat-printed insert in its pocket
TILT, PLATE, FLOOR = -8.0, 2.8, -3.0
def ry(deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    M = np.eye(4); M[0, 0] = c; M[0, 2] = s; M[2, 0] = -s; M[2, 2] = c; return M
def tr(x, y, z):
    M = np.eye(4); M[:3, 3] = [x, y, z]; return M
T_PLACE = tr(0, 0, PLATE - 0.4) @ ry(TILT)
W_INS = np.array([[1, 0, 0, 0], [0, 0, -1, FLOOR], [0, 1, 0, 0], [0, 0, 0, 1.0]])   # (u,v,w) -> (u, FLOOR-w, v)

parts = {
    "ear_L":    ("ear_LEFT.stl",               ML @ P2P["ear_LEFT.stl"]),
    "ear_R":    ("ear_RIGHT.stl",              MR @ P2P["ear_RIGHT.stl"]),
    "clip_L":   (pl["clip"],                   ML @ P2P[pl["clip"]]),
    "clip_R":   (pl["clip"],                   MR @ FLIPX @ P2P[pl["clip"]]),
    "insert_L": ("inner_ear_insert_LEFT.stl",  ML @ T_PLACE @ W_INS @ P2P["inner_ear_insert_LEFT.stl"]),
    "insert_R": ("inner_ear_insert_RIGHT.stl", MR @ FLIPX @ T_PLACE @ W_INS @ FLIPX @ P2P["inner_ear_insert_RIGHT.stl"]),
}
preview = trimesh.load(os.path.join(A.ears, "preview_as_worn.glb"))
pg = {n: preview.geometry[preview.graph.get(n)[1]] for n in preview.graph.nodes_geometry}

# build plate (Bambu 256 x 256 mm) lying on the floor in front of the headset; print frame z = up
PLATE_C = np.array([0.0, -300.0, -349.0])
LAYOUT = {"ear_L": (-62, 45), "ear_R": (62, 45), "clip_L": (-22, -62), "clip_R": (22, -62),
          "insert_L": (-82, -62), "insert_R": (82, -62)}

scene = trimesh.Scene(); meta = {"parts": {}, "plate": PLATE_C.tolist(),
                                 "axes": {s: np.array(M)[:3, :3].T.tolist() for s, M in (("L", ML), ("R", MR))},
                                 "origin": {"L": ML[:3, 3].tolist(), "R": MR[:3, 3].tolist()}}
for name, (fname, Mfinal) in parts.items():
    m = trimesh.load(os.path.join(A.ears, fname))
    if len(m.faces) > A.ear_faces:
        m = m.simplify_quadric_decimation(face_count=A.ear_faces)
    w = m.copy(); w.apply_transform(Mfinal)
    err = np.abs(w.bounds - pg[name].bounds).max()
    print(f"{name:9s} {len(m.faces):6d} faces, final-pose check {err:.2f} mm")
    assert err < 1.0, name
    x, y = LAYOUT[name]
    Mplate = tr(PLATE_C[0] + x, PLATE_C[1] + y, PLATE_C[2])
    scene.add_geometry(m, node_name=name, geom_name=name)
    meta["parts"][name] = {"final": Mfinal.T.flatten().tolist(), "plate": Mplate.T.flatten().tolist()}   # column-major for three.js

band = conv(A.band); scene.add_geometry(band, node_name="band", geom_name="band")
for side, path in (("L", A.velcro_l), ("R", A.velcro_r)):
    a = conv(path); scene.add_geometry(a, node_name=f"anchor_{side}", geom_name=f"anchor_{side}")
scene.export(A.out)
json.dump(meta, open(os.path.splitext(A.out)[0] + ".json", "w"))
print("wrote", A.out, round(os.path.getsize(A.out) / 1e6, 2), "MB")
