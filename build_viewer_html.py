"""Fill an HTML template with the scene GLB, metadata and the Corsair wordmark -> a standalone page.

python build_viewer_html.py scene.glb scene.json template.html out.html [assets/corsair_wordmark.png] [--mode=assembly]
"""
import base64, os, sys
args = [a for a in sys.argv[1:] if not a.startswith("--")]
mode = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mode=")), "viewer")
glb, meta, tpl, out = args[:4]
wm = args[4] if len(args) > 4 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "corsair_wordmark.png")
html = open(tpl, encoding="utf-8").read()
here = os.path.dirname(os.path.abspath(__file__))
html = html.replace("'__MODE__'", repr(mode))
html = html.replace("/*__FILM__*/", open(os.path.join(here, "assembly_film.js"), encoding="utf-8").read() if mode == "assembly" else "const FILM = null;")
html = html.replace("__META__", open(meta, encoding="utf-8").read())
html = html.replace("__WORDMARK__", "data:image/png;base64," + base64.b64encode(open(wm, "rb").read()).decode())
html = html.replace("__GLB__", base64.b64encode(open(glb, "rb").read()).decode())
open(out, "w", encoding="utf-8").write(html)
print(f"{out}: {len(html)/1e6:.1f} MB")
