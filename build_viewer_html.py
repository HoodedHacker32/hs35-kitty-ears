"""Fill viewer_realistic_template.html with the scene GLB + metadata -> viewer_realistic.html"""
import base64, sys
glb, meta, tpl, out = sys.argv[1:5]
html = open(tpl, encoding="utf-8").read()
html = html.replace("__META__", open(meta, encoding="utf-8").read())
html = html.replace("__GLB__", base64.b64encode(open(glb, "rb").read()).decode())
open(out, "w", encoding="utf-8").write(html)
print(f"{out}: {len(html)/1e6:.1f} MB")
