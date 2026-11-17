"""Fill an HTML template with the scene GLB, metadata and the Corsair wordmark -> a standalone page.

python build_viewer_html.py scene.glb scene.json template.html out.html [assets/corsair_wordmark.png]
"""
import base64, os, sys
glb, meta, tpl, out = sys.argv[1:5]
wm = sys.argv[5] if len(sys.argv) > 5 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "corsair_wordmark.png")
html = open(tpl, encoding="utf-8").read()
html = html.replace("__META__", open(meta, encoding="utf-8").read())
html = html.replace("__WORDMARK__", "data:image/png;base64," + base64.b64encode(open(wm, "rb").read()).decode())
html = html.replace("__GLB__", base64.b64encode(open(glb, "rb").read()).decode())
open(out, "w", encoding="utf-8").write(html)
print(f"{out}: {len(html)/1e6:.1f} MB")
